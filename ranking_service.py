"""Shared ranking calculation logic used by API routes and agent endpoints."""
import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Optional

from data_processor import CFBDataProcessor
from ranking_algorithm import TeamQualityRanker
from cache import get_cache, TTL_RANKINGS, TTL_PRIORS

ALGO_VERSION = 'v5.2'

DEFAULT_CONFIG = {
    'power_conf_initial': 1500.0,
    'group5_initial': 1200.0,
    'fcs_initial': 900.0,
    'base_factor': 40.0,
    'team_quality_weight': 0.75,
    'conference_weight': 0.05,
    'record_weight': 0.20,
    'prior_strength': 0.15,
    'use_ats': False,
    'ats_bonus': 10.0,
    # A/B on 2023–2024: reference ranks hurt pooled Brier; keep off by default.
    'use_reference_ranks': False,
}

# Canonical FRS blend (must match DEFAULT_CONFIG weights)
FRS_WEIGHTS = (
    DEFAULT_CONFIG['team_quality_weight'],
    DEFAULT_CONFIG['record_weight'],
    DEFAULT_CONFIG['conference_weight'],
)

# Fields that affect historical Elo used for priors (not prior_strength blend)
_PRIORS_CONFIG_KEYS = (
    'power_conf_initial',
    'group5_initial',
    'fcs_initial',
    'base_factor',
    'team_quality_weight',
    'conference_weight',
    'record_weight',
    'use_ats',
    'ats_bonus',
    'use_reference_ranks',
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
        'prior_strength': request_args.get('prior_strength'),
        'algo': ALGO_VERSION,
    }
    return cache._generate_key('rankings_computed', **cache_params)


def priors_cache_key(year: int, config: Dict[str, Any]) -> str:
    """Key priors by season + algo fingerprint (excludes prior_strength)."""
    cache = get_cache()
    fingerprint = {k: config.get(k, DEFAULT_CONFIG.get(k)) for k in _PRIORS_CONFIG_KEYS}
    fingerprint['algo'] = ALGO_VERSION
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
    history_data = []
    # calculate_priors only weights Y-1 and Y-2 — skip Y-3
    for h_year in range(year - 1, year - 3, -1):
        try:
            h_games = data_processor.get_games_for_season(h_year, use_week_scoped_fetch=False)
            if h_games:
                h_ranker = TeamQualityRanker(config)
                h_games_by_week = data_processor.organize_games_by_week(h_games)
                for w in sorted(h_games_by_week.keys()):
                    for g in h_games_by_week[w]:
                        h_ranker.update_quality_scores(g)
                h_results = h_ranker.calculate_final_rankings()
                h_results = h_ranker.normalize_scores(h_results)
                history_data.append(h_results)
        except Exception as e:
            print(f"Could not process history for {h_year}: {e}")

    priors = TeamQualityRanker.calculate_priors(history_data)
    cache.set(key, priors, TTL_PRIORS, prefix='priors')
    return priors


_LIST_STRIP_TEAM_KEYS = ('wins_details', 'losses_details')


def slim_rankings_for_list(rankings_data: Dict[str, Any]) -> Dict[str, Any]:
    """Drop duplicate map and per-game details for list/table responses."""
    slim = {
        'year': rankings_data.get('year'),
        'week': rankings_data.get('week'),
        'conference_rankings': rankings_data.get('conference_rankings', []),
        'detail': False,
        'algo': ALGO_VERSION,
    }
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

    if request_args.get('prior_strength') is not None:
        config['prior_strength'] = float(request_args.get('prior_strength'))
    else:
        calc_week = week if week is not None else 15
        config['prior_strength'] = max(0.0, 0.7 * (12.0 - calc_week) / 11.0)

    priors = compute_priors(data_processor, year, config)
    print(f"Calculated priors for {len(priors)} teams.")

    print("Calculating rankings (Iterative V5.2)...")
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
    return rankings_data


def get_or_calculate_rankings(
    data_processor: CFBDataProcessor,
    year: int,
    week: Optional[int],
    request_args,
    *,
    prefer_static: bool = True,
) -> Optional[Dict[str, Any]]:
    # Archived weeks: try precomputed static file first (no CFBD / no solver)
    if prefer_static and week is not None and is_archived_week(year, week):
        try:
            from static_rankings import read_static_rankings
            static = read_static_rankings(year, week)
            if static is not None:
                print(f"STATIC HIT: rankings {year} week={week}")
                return static
        except Exception as e:
            print(f"Static rankings read error: {e}")

    cache = get_cache()
    key = rankings_cache_key(year, week, request_args)
    cached = cache.get(key)
    if cached is not None:
        print(f"Cache HIT: computed rankings {year} week={week}")
        return cached

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
