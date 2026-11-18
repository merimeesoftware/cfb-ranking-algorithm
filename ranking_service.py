"""Shared ranking calculation logic used by API routes and agent endpoints."""
import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Optional

from api_integration import CFBDRequestError
from data_processor import CFBDataProcessor
from ranking_algorithm import (
    TeamQualityRanker,
    earned_start_offsets,
    ordering_score,
    soft_slate_flag,
)
from cache import get_cache, TTL_RANKINGS, TTL_PRIORS
from conference_membership import MembershipError, load_membership
from spend_guards import CFBDOfflineError

ALGO_VERSION = 'v5.6'
# Committed prior files stay the v5.3 blend seed. Do not regenerate them:
# a 2026 prior rebuild would read 2025 games. Tier means are computed at run time.
BLEND_PRIOR_ALGO = 'v5.3'

# Request keys that must not change a board. Ignored by build_config.
# Public routes reject them. ``*_override`` is rejected the same way.
LOCKED_FORMULA_KEYS = frozenset({
    'prior_strength',
    'prior_offset_strength',
    'prior_offset_weights',
    'prior_offset_cap',
    'mw_p4_p4',
    'mw_p4_g5',
    'mw_g5_g5',
    'mw_fbs_fcs',
    'mw_fcs_fcs',
})

DEFAULT_CONFIG = {
    'power_conf_initial': 1500.0,
    'group5_initial': 1200.0,
    'fcs_initial': 900.0,
    'base_factor': 50.0,
    'hfa_elo': 50.0,
    'upset_bonus_mult': 1.0,
    'team_quality_weight': 0.80,
    'conference_weight': 0.05,
    'record_weight': 0.15,
    # History offset, held all season (issue #202 C). Strength is the
    # 2019–2022 tune pick from {0.3, 0.4, 0.5, 0.6, 0.7}. Cap is half the
    # 300-point tier gap. Weights renormalize over seasons that exist.
    'prior_offset_strength': 0.4,
    'prior_offset_weights': [0.70, 0.30],
    'prior_offset_cap': 150.0,
    # Matchup weights. One table. G5-G5 is full weight (issue #202 A).
    'mw_p4_p4': 1.0,
    'mw_p4_g5': 0.8,
    'mw_g5_g5': 1.0,
    'mw_fbs_fcs': 0.2,
    'mw_fcs_fcs': 0.1,
    # A/B on 2019–2024: reference ranks hurt pooled Brier; keep off by default.
    'use_reference_ranks': False,
}

# Canonical FRS blend (must match DEFAULT_CONFIG weights)
FRS_WEIGHTS = (
    DEFAULT_CONFIG['team_quality_weight'],
    DEFAULT_CONFIG['record_weight'],
    DEFAULT_CONFIG['conference_weight'],
)

# Fields that affect the stored-score replay used when a prior file is missing.
# prior_offset_strength and prior_offset_cap are applied at kickoff, not here.
_PRIORS_CONFIG_KEYS = (
    'power_conf_initial',
    'group5_initial',
    'fcs_initial',
    'base_factor',
    'hfa_elo',
    'upset_bonus_mult',
    'team_quality_weight',
    'conference_weight',
    'record_weight',
    'use_reference_ranks',
    'mw_p4_p4',
    'mw_p4_g5',
    'mw_g5_g5',
    'mw_fbs_fcs',
    'mw_fcs_fcs',
    'prior_offset_weights',
)


def build_config(request_args) -> Dict[str, Any]:
    config = DEFAULT_CONFIG.copy()

    def get_float_arg(key, default):
        val = request_args.get(key)
        return float(val) if val is not None else default

    config['power_conf_initial'] = get_float_arg('power_conf_initial', config['power_conf_initial'])
    config['group5_initial'] = get_float_arg('group5_initial', config['group5_initial'])
    config['fcs_initial'] = get_float_arg('fcs_initial', config['fcs_initial'])
    config['base_factor'] = get_float_arg('base_factor', config['base_factor'])
    config['team_quality_weight'] = get_float_arg('team_quality_weight', config['team_quality_weight'])
    config['conference_weight'] = get_float_arg('conference_weight', config['conference_weight'])
    config['record_weight'] = get_float_arg('record_weight', config['record_weight'])
    return config


def published_snapshot(data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """A computed-cache entry is current only when it was stored under this label.

    Committed static files are not checked here. A v5.4 key is a different
    cache entry and is not read.
    """
    if not isinstance(data, dict) or data.get('algo') != ALGO_VERSION:
        return None
    return data


def rankings_cache_key(year: int, week: Optional[int], request_args) -> str:
    cache = get_cache()
    cache_params = {
        'year': year,
        'week': week,
        'all_divisions': request_args.get('all_divisions', 'false'),
        'power_conf_initial': request_args.get('power_conf_initial'),
        'group5_initial': request_args.get('group5_initial'),
        'fcs_initial': request_args.get('fcs_initial'),
        'base_factor': request_args.get('base_factor'),
        'team_quality_weight': request_args.get('team_quality_weight'),
        'conference_weight': request_args.get('conference_weight'),
        'record_weight': request_args.get('record_weight'),
        'algo': ALGO_VERSION,
    }
    return cache._generate_key('rankings_computed', **cache_params)


def priors_cache_key(year: int, config: Dict[str, Any]) -> str:
    """Key offsets by season + algo fingerprint.

    Strength and the cap are applied when a team is initialized, so they
    are not part of this key. The 0.7/0.3 weights are.
    """
    cache = get_cache()
    fingerprint = {k: config.get(k, DEFAULT_CONFIG.get(k)) for k in _PRIORS_CONFIG_KEYS}
    fingerprint['algo'] = ALGO_VERSION
    # #101: priors computed under another membership map are a different key.
    fingerprint['membership'] = load_membership().version
    config_hash = hashlib.md5(
        json.dumps(fingerprint, sort_keys=True).encode(),
        usedforsecurity=False,
    ).hexdigest()[:12]
    return cache._generate_key('priors', year, config_hash)


def compute_priors(data_processor: CFBDataProcessor, year: int, config: Dict[str, Any]) -> Dict[str, float]:
    cache = get_cache()
    key = priors_cache_key(year, config)
    cached = cache.get(key)
    if cached is not None:
        print(f"Cache HIT: priors for {year}")
        return cached

    print(f"Cache MISS: priors for {year}")
    seasons = []
    # Y-1 and Y-2 only. Published files stay v5.3. A missing file is replayed
    # from tier starts (offset 0) so history enters once. Do not write that
    # replay back over the committed prior files.
    from static_rankings import read_prior_teams
    membership = load_membership()
    for h_year in range(year - 1, year - 3, -1):
        if h_year < membership.first_season:
            print(f"Priors: skipping {h_year}, before conference membership "
                  f"coverage {membership.first_season}-{membership.last_season} "
                  f"(map {membership.version})")
            continue
        try:
            stored = read_prior_teams(h_year, algo=BLEND_PRIOR_ALGO, membership=membership.version)
            if stored is not None:
                seasons.append({'year': h_year, 'scores': stored})
                continue
            h_games = data_processor.get_games_for_season(h_year, use_week_scoped_fetch=False)
            if h_games:
                replay_config = dict(config)
                replay_config['prior_offset_strength'] = 0.0
                h_ranker = TeamQualityRanker(replay_config)
                h_games_by_week = data_processor.organize_games_by_week(h_games)
                for w in sorted(h_games_by_week.keys()):
                    for g in h_games_by_week[w]:
                        h_ranker.update_quality_scores(g)
                h_results = h_ranker.calculate_final_rankings()
                h_results = h_ranker.normalize_scores(h_results)
                scores = {}
                for name, data in h_results.get('rankings', {}).items():
                    score = data.get('final_ranking_score')
                    if isinstance(score, (int, float)) and not isinstance(score, bool):
                        scores[name] = float(score)
                seasons.append({'year': h_year, 'scores': scores})
        except (CFBDRequestError, CFBDOfflineError, MembershipError):
            # MembershipError fails closed (#101): a map gap is not "no history".
            raise
        except Exception as e:
            print(f"Could not process history for {h_year}: {e}")

    weights = config.get('prior_offset_weights', DEFAULT_CONFIG['prior_offset_weights'])
    priors = earned_start_offsets(seasons, weights)
    cache.set(key, priors, TTL_PRIORS, prefix='priors')
    return priors


_LIST_STRIP_TEAM_KEYS = ('wins_details', 'losses_details')


def formula_breakdown(team: Dict[str, Any]) -> Dict[str, Any]:
    """The place is Elo. Record, conference, and the slate label stay display-only."""
    score = ordering_score(team)
    display: Dict[str, Any] = {
        'record_score': float(team.get('record_score') or 0),
        'conference_quality': float(team.get('conference_quality_score') or 0),
        'soft_slate_flag': soft_slate_flag(team),
        # Cupcake marks use the rating after the week, not the pregame rating.
        'soft_win_share_basis': (
            'End-of-week Elo. A later rating can move a win under the line after the fact.'
        ),
    }
    ahead = team.get('record_ahead')
    if isinstance(ahead, (int, float)) and not isinstance(ahead, bool):
        display['record_ahead'] = float(ahead)
    share = team.get('soft_win_share')
    if isinstance(share, (int, float)) and not isinstance(share, bool):
        display['soft_win_share'] = float(share)
    return {
        'ordering': 'elo',
        'tq_contribution': score,
        'total': score,
        'display_only': display,
    }


def publish_order(rankings_data: Dict[str, Any]) -> Dict[str, Any]:
    """Order the board by Elo. Heat weight is 0. Stamp ordering_score on each row."""
    teams = rankings_data.get('team_rankings')
    if isinstance(teams, list):
        for team in teams:
            if isinstance(team, dict):
                team['ordering_score'] = ordering_score(team)
        rankings_data['team_rankings'] = sorted(
            teams,
            key=lambda team: (-ordering_score(team), str(team.get('team_name') or '')),
        )
    return rankings_data


def slim_rankings_for_list(rankings_data: Dict[str, Any]) -> Dict[str, Any]:
    """Drop duplicate map and per-game details for list/table responses.

    The stamp stays the board's own. A stored week that is missing
    ``detail: False`` must not be relabeled with the current ALGO_VERSION.
    A fresh calculate already set that stamp before this runs.
    """
    slim = {
        'year': rankings_data.get('year'),
        'week': rankings_data.get('week'),
        'conference_rankings': rankings_data.get('conference_rankings', []),
        'detail': False,
    }
    if 'algo' in rankings_data:
        slim['algo'] = rankings_data.get('algo')
    teams = []
    for team in rankings_data.get('team_rankings', []):
        entry = {k: v for k, v in team.items() if k not in _LIST_STRIP_TEAM_KEYS}
        teams.append(entry)
    slim['team_rankings'] = teams
    return slim


def is_archived_week(
    year: int,
    week: Optional[int],
    now: Optional[datetime] = None,
    current_week: Optional[int] = None,
) -> bool:
    """True when rankings for this year/week should prefer static/precomputed data."""
    now = now or datetime.now()
    if week is None:
        if now.month < 8:
            return year < (now.year - 1) or (year == now.year - 1 and now.month >= 2)
        return year < now.year

    if now.month < 8:
        season_year = now.year - 1
        return year <= season_year
    season_year = now.year
    if year < season_year:
        return True
    if year > season_year:
        return False
    if current_week is None:
        season_start = datetime(season_year, 8, 24)
        if now < season_start:
            current_week = 1
        else:
            current_week = int((now - season_start).days / 7) + 1
    return week < current_week


def calculate_rankings_logic(
    data_processor: CFBDataProcessor,
    year: int,
    week: Optional[int],
    request_args,
) -> Optional[Dict[str, Any]]:
    print(f"Fetching games for {year}, week: {week if week else 'all'}...")
    games = data_processor.get_games_for_season(year, through_week=week)
    print(f"Fetched {len(games)} games.")
    if not games:
        return None

    games_by_week = data_processor.organize_games_by_week(games)
    config = build_config(request_args)
    # prior_offset_* and mw_* stay on DEFAULT_CONFIG. A request cannot set them.

    priors = compute_priors(data_processor, year, config)
    print(f"Calculated priors for {len(priors)} teams.")

    print("Calculating rankings (Iterative V5.3)...")
    reference_ranks = None
    conf_stddevs = {}
    num_iterations = TeamQualityRanker(config, priors).num_iterations

    for i in range(num_iterations):
        print(f"  Iteration {i+1}/{num_iterations}...")
        ranker = TeamQualityRanker(config, priors)
        if conf_stddevs:
            ranker.set_conference_stddevs(conf_stddevs)
        for week_num in sorted(games_by_week.keys()):
            for game in games_by_week[week_num]:
                ranker.update_quality_scores(game, reference_ranks)
        if i < num_iterations - 1:
            temp_results = ranker.calculate_final_rankings()
            reference_ranks = {
                t['team_name']: t['team_quality_score']
                for t in temp_results['team_rankings']
            }
            conf_stddevs = ranker.compute_conference_stddevs()

    rankings_data = ranker.calculate_final_rankings()
    rankings_data = ranker.normalize_scores(rankings_data)

    for team in rankings_data['team_rankings']:
        team_name = team['team_name']
        team_info = data_processor.team_info_map.get(team_name, {})
        logos = team_info.get('logos') or []
        team['logo'] = logos[0] if len(logos) > 0 else None
        team['logo_dark'] = logos[1] if len(logos) > 1 else team['logo']
        team['color'] = team_info.get('color')
        team['alt_color'] = team_info.get('alt_color')

    for conf in rankings_data['conference_rankings']:
        conf_name = conf['conference_name']
        fcs_wins = 0
        fcs_losses = 0
        for team_name, stats in ranker.team_stats.items():
            if stats['conference'] == conf_name:
                fcs_wins += stats['record_vs_fcs']['wins']
                fcs_losses += stats['record_vs_fcs']['losses']
        conf['fcs_wins'] = fcs_wins
        conf['fcs_losses'] = fcs_losses
        conf['record_vs_fcs'] = f"{fcs_wins}-{fcs_losses}"

    show_all = request_args.get('all_divisions') == 'true'
    if not show_all:
        fbs_types = ['Power 4', 'Group of 5', 'FBS Independents']
        rankings_data['team_rankings'] = [
            t for t in rankings_data['team_rankings']
            if t.get('conference_type') in fbs_types
        ]

    rankings_data['year'] = year
    rankings_data['week'] = week
    rankings_data['algo'] = ALGO_VERSION
    # team_rankings is canonical; drop name-keyed duplicate before cache/API
    rankings_data.pop('rankings', None)
    return publish_order(rankings_data)


def get_or_calculate_rankings(
    data_processor: Optional[CFBDataProcessor],
    year: int,
    week: Optional[int],
    request_args,
    *,
    prefer_static: bool = True,
    allow_compute: bool = True,
) -> Optional[Dict[str, Any]]:
    # Public routes pass allow_compute=False so a cache miss cannot call CFBD.
    static = None
    if week is not None and (prefer_static or not allow_compute):
        try:
            from static_rankings import read_static_rankings_any
            static = read_static_rankings_any(year, week)
            if static is not None and (prefer_static or not allow_compute):
                if prefer_static and is_archived_week(year, week):
                    print(f"STATIC HIT: rankings {year} week={week}")
                    return publish_order(static)
                if not allow_compute:
                    print(f"STATIC HIT: rankings {year} week={week}")
                    return publish_order(static)
        except Exception as e:
            print(f"Static rankings read error: {e}")

    if not allow_compute:
        if static is not None:
            return publish_order(static)
        print(f"STATIC MISS: rankings {year} week={week} (compute disabled)")
        return None

    if data_processor is None:
        raise RuntimeError('computing rankings requires a data processor')

    cache = get_cache()
    key = rankings_cache_key(year, week, request_args)
    cached = published_snapshot(cache.get(key))
    if cached is not None:
        print(f"Cache HIT: computed rankings {year} week={week}")
        return publish_order(cached)

    print(f"Cache MISS: computed rankings {year} week={week}")
    data = calculate_rankings_logic(data_processor, year, week, request_args)
    if data:
        cache.set(key, data, TTL_RANKINGS, prefix='rankings_computed')
        if week is not None and is_archived_week(year, week):
            try:
                from static_rankings import write_static_rankings
                write_static_rankings(slim_rankings_for_list(data), year, week)
            except Exception as e:
                print(f"Static rankings write error: {e}")
    return data
