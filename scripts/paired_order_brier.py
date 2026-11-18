"""Paired Brier for formula arms A and C. Offline. 2025 is refused.

Game rows: TR_GAMES_DIR/games-YYYY-both.json for 2017-2024 only.
Home field is 50. Weeks 1-15. Week-bootstrap 95% CI, 2,000 resamples, seed 20261111.
Does not read 2025 games, boards, or prior files.
"""
from __future__ import annotations

import json
import os
import random
import sys
from collections import defaultdict

os.environ.setdefault('CFBD_OFFLINE', '1')
os.environ.setdefault('AI_MODE', 'stub')
os.environ.setdefault('FLASK_ENV', 'development')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

GAMES = os.environ.get('TR_GAMES_DIR', '')
if not GAMES:
    raise SystemExit('Set TR_GAMES_DIR to the 2017-2024 game rows. 2025 is not read.')

from api_integration import CFBDApiClient
from data_processor import CFBDataProcessor
from ranking_algorithm import TeamQualityRanker, apply_start_offset, earned_start_offsets
from ranking_service import DEFAULT_CONFIG
from algo_lab.predict import predict_game
from algo_lab.runner import preseason_ratings, rank_through_week, ratings_from_rankings
from conference_membership import load_membership
from static_rankings import read_prior_teams

FBS = {'Power 4', 'Group of 5'}
HFA = 50.0
GRID = (0.3, 0.4, 0.5, 0.6, 0.7)
WINDOWS = {
    'tune_2019_2022': [2019, 2020, 2021, 2022],
    'validate_2023': [2023],
    'confirm_2024': [2024],
}
HOLDOUT_2025 = 'PENDING'


def load_year(year):
    year = int(year)
    if year == 2025 or year < 2017 or year > 2024:
        raise SystemExit(f'Refusing games for {year}. 2025 is not read.')
    raw = json.load(open(f'{GAMES}/games-{year}-both.json'))
    client = CFBDApiClient(api_key='offline-placeholder')
    proc = CFBDataProcessor(api_client=client)
    rows = proc._process_raw_games([client._transform_game(g) for g in raw], season=year)
    out = []
    for game in rows:
        if (game.get('season_type') or 'regular') == 'postseason':
            continue
        week = game.get('week')
        if week is None or not 1 <= int(week) <= 15:
            continue
        out.append(game)
    return out


def cold_frs(games):
    """One-pass results-only replay. Offset 0. G5-G5 weight stays 0.65."""
    config = DEFAULT_CONFIG.copy()
    config['mw_g5_g5'] = 0.65
    config['prior_offset_strength'] = 0.0
    ranker = TeamQualityRanker(config)
    by_week = defaultdict(list)
    for game in games:
        by_week[int(game['week'])].append(game)
    for week in sorted(by_week):
        for game in by_week[week]:
            ranker.update_quality_scores(game)
    results = ranker.calculate_final_rankings()
    scores = {}
    for name, data in results.get('rankings', {}).items():
        score = data.get('final_ranking_score')
        if isinstance(score, (int, float)) and not isinstance(score, bool):
            scores[name] = float(score)
    return scores


def legacy_blend(newer, older):
    """Main's un-normalized 0.70/0.30 FRS blend."""
    priors = {}
    for name in set(newer) | set(older):
        total = 0.0
        present = False
        if name in newer:
            total += 0.70 * newer[name]
            present = True
        if name in older:
            total += 0.30 * older[name]
            present = True
        if present:
            priors[name] = total
    return priors


def legacy_ranker(raw_priors, fade):
    class _Legacy(TeamQualityRanker):
        def _starting_elo(self, team_name, tier_initial):
            if team_name in raw_priors:
                return (1.0 - fade) * tier_initial + fade * float(raw_priors[team_name])
            return float(tier_initial)
    return _Legacy


def main_fade(week):
    return max(0.0, 0.7 * (12.0 - week) / 11.0)


def faded_strength(week, strength):
    """Same shape as main's fade. Week 1 keeps `strength`. Week 12 keeps 0."""
    return float(strength) * max(0.0, (12.0 - week) / 11.0)


def meta_of(games):
    meta = {}
    for game in games:
        meta[game['home_team_name']] = {
            'conference': game.get('home_conference'),
            'conference_type': game.get('home_conference_type'),
        }
        meta[game['away_team_name']] = {
            'conference': game.get('away_conference'),
            'conference_type': game.get('away_conference_type'),
        }
    return meta


def slices_of(game):
    home = game.get('home_conference_type')
    away = game.get('away_conference_type')
    tags = []
    if home in FBS or away in FBS:
        tags.append('fbs_involved')
    if home in FBS and away in FBS:
        tags.append('fbs_fbs')
    if {home, away} == {'Power 4', 'Group of 5'}:
        tags.append('cross')
    return tags


def score_arm(by_year, years, settings):
    """settings(through_week) -> (config, offsets, ranker_cls)."""
    rows = []
    for year in years:
        games = by_year[year]
        meta = meta_of(games)
        pre_cfg, pre_offsets, pre_cls = settings(year, 1)
        pre = preseason_ratings(
            config=pre_cfg,
            start_offsets=pre_offsets,
            team_meta=meta,
            ranker_cls=pre_cls,
        )
        weeks = sorted({int(game['week']) for game in games})
        for week in weeks:
            if week == 1:
                ratings = pre
            else:
                cfg, offsets, cls = settings(year, week - 1)
                rankings, _ranker = rank_through_week(
                    games, week - 1, config=cfg, start_offsets=offsets, ranker_cls=cls,
                )
                ratings = dict(pre)
                ratings.update(ratings_from_rankings(rankings, field='team_quality_score'))
            for game in games:
                if int(game['week']) != week:
                    continue
                tags = slices_of(game)
                if 'fbs_involved' not in tags:
                    continue
                pred = predict_game(game, ratings, hfa_regular=HFA)
                if pred is None:
                    continue
                outcome = 1.0 if pred['home_won'] else 0.0
                rows.append({
                    'year': year,
                    'week': week,
                    'brier': (pred['p_home'] - outcome) ** 2,
                    'p': pred['p_home'],
                    'y': outcome,
                    'tags': tags,
                })
    return rows


def summarize(rows, tag):
    chosen = [row for row in rows if tag in row['tags']]
    if not chosen:
        return {'n': 0, 'brier': None}
    return {
        'n': len(chosen),
        'brier': sum(row['brier'] for row in chosen) / len(chosen),
    }


def calibration(rows):
    chosen = [row for row in rows if 'cross' in row['tags']]
    if not chosen:
        return {'n': 0, 'abs_gap': None}
    pred = sum(row['p'] for row in chosen) / len(chosen)
    actual = sum(row['y'] for row in chosen) / len(chosen)
    return {'n': len(chosen), 'pred': pred, 'actual': actual, 'abs_gap': abs(pred - actual)}


def paired(base_rows, alt_rows, tag):
    assert len(base_rows) == len(alt_rows)
    by_week = defaultdict(list)
    diffs = []
    for left, right in zip(base_rows, alt_rows):
        assert left['year'] == right['year'] and left['week'] == right['week']
        if tag not in left['tags']:
            continue
        assert tag in right['tags']
        delta = right['brier'] - left['brier']
        diffs.append(delta)
        by_week[(left['year'], left['week'])].append(delta)
    if not diffs:
        return {'n': 0, 'point': None, 'ci_low': None, 'ci_high': None}
    point = sum(diffs) / len(diffs)
    weeks = list(by_week.values())
    rng = random.Random(20261111)
    means = []
    draws = 2000
    for _ in range(draws):
        drawn = [weeks[rng.randrange(len(weeks))] for _ in range(len(weeks))]
        pooled = [value for week in drawn for value in week]
        means.append(sum(pooled) / len(pooled))
    means.sort()
    return {
        'n': len(diffs),
        'n_weeks': len(weeks),
        'point': point,
        'ci_low': means[int(0.025 * draws)],
        'ci_high': means[int(0.975 * draws) - 1],
    }


def arm_settings(kind, strength, raw_by_year, offsets_by_year):
    def settings(year, through_week):
        config = DEFAULT_CONFIG.copy()
        offsets = {}
        cls = None
        if kind == 'main':
            config['mw_g5_g5'] = 0.65
            cls = legacy_ranker(raw_by_year[year], main_fade(through_week))
        elif kind == 'a':
            config['mw_g5_g5'] = 1.0
            cls = legacy_ranker(raw_by_year[year], main_fade(through_week))
        elif kind == 'c_level':
            config['mw_g5_g5'] = 0.65
            config['prior_offset_strength'] = 0.0
            offsets = offsets_by_year[year]
        elif kind == 'c_faded':
            config['mw_g5_g5'] = 0.65
            config['prior_offset_strength'] = faded_strength(through_week, strength)
            offsets = offsets_by_year[year]
        elif kind == 'c_held':
            config['mw_g5_g5'] = 0.65
            config['prior_offset_strength'] = strength
            offsets = offsets_by_year[year]
        elif kind == 'a_c':
            config['mw_g5_g5'] = 1.0
            config['prior_offset_strength'] = strength
            offsets = offsets_by_year[year]
        else:
            raise SystemExit(f'unknown arm {kind}')
        return config, offsets, cls
    return settings


def pick_strength(grid_rows):
    """Lowest FBS-vs-FBS Brier. Tie: closer to 0.5, then lower."""
    def key(row):
        return (row['brier'], abs(row['strength'] - 0.5), row['strength'])
    return min(grid_rows, key=key)['strength']


def _pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    if dx == 0.0 or dy == 0.0:
        return None
    return num / (dx * dy)


def spearman(pairs):
    def ranks(index):
        order = sorted(range(len(pairs)), key=lambda i: (-pairs[i][index], pairs[i][0]))
        out = [0] * len(pairs)
        for place, i in enumerate(order):
            out[i] = place
        return out
    if len(pairs) < 3:
        return None
    return _pearson(ranks(1), ranks(2))


def order_map(rankings):
    teams = [
        team for team in rankings['team_rankings']
        if team.get('conference_type') in FBS
    ]
    teams.sort(key=lambda team: (-team['team_quality_score'], team['team_name']))
    return {team['team_name']: (place, team['team_quality_score']) for place, team in enumerate(teams, start=1)}


def dominate(by_year, offsets_by_year, strength):
    """C-held versus C-level-only at the shipped G5 weight, so only the offset differs."""
    report = []
    for year in (2023, 2024):
        games = by_year[year]
        for week in (12, 15):
            level_cfg = DEFAULT_CONFIG.copy()
            level_cfg['prior_offset_strength'] = 0.0
            held_cfg = DEFAULT_CONFIG.copy()
            held_cfg['prior_offset_strength'] = strength
            level, _ = rank_through_week(
                games, week, config=level_cfg, start_offsets=offsets_by_year[year],
            )
            held, _ = rank_through_week(
                games, week, config=held_cfg, start_offsets=offsets_by_year[year],
            )
            pre = preseason_ratings(
                config=held_cfg,
                start_offsets=offsets_by_year[year],
                team_meta=meta_of(games),
            )
            left = order_map(level)
            right = order_map(held)
            names = sorted(set(left) & set(right))
            pairs = [(name, left[name][1], right[name][1]) for name in names]
            shifts = [abs(left[name][0] - right[name][0]) for name in names]
            worst = max(names, key=lambda name: abs(left[name][0] - right[name][0]))
            finals = [right[name][1] for name in names]
            starts = [pre.get(name, 1200.0) for name in names]
            r = _pearson(starts, finals)
            report.append({
                'year': year,
                'week': week,
                'n': len(names),
                'spearman_held_vs_level': spearman(pairs),
                'largest_place_shift': max(shifts) if shifts else None,
                'largest_shift_team': worst,
                'largest_shift_level_place': left[worst][0],
                'largest_shift_held_place': right[worst][0],
                'start_r2': None if r is None else r * r,
            })
            print('DOMINATE', report[-1], flush=True)
    return report


def echo(strength):
    """Effect of the 2022 prior on 2024 starts. Does not read 2025."""
    membership = load_membership()
    scores_2023 = read_prior_teams(2023, algo='v5.3', membership=membership.version)
    scores_2022 = read_prior_teams(2022, algo='v5.3', membership=membership.version)
    if not scores_2023 or not scores_2022:
        raise SystemExit('2022 and 2023 prior files are required. They are not regenerated.')
    weights = DEFAULT_CONFIG['prior_offset_weights']
    cap = DEFAULT_CONFIG['prior_offset_cap']
    both = earned_start_offsets(
        [{'year': 2023, 'scores': scores_2023}, {'year': 2022, 'scores': scores_2022}],
        weights,
    )
    only = earned_start_offsets([{'year': 2023, 'scores': scores_2023}], weights)
    deltas = []
    for team in membership.season_map(2024):
        conference = membership.conference_for(team, 2024)
        tier = membership.tier_for(conference, 2024, team=team)
        if tier == 'Power 4':
            base = 1500.0
        elif tier == 'Group of 5':
            base = 1200.0
        else:
            continue
        full = apply_start_offset(base, both.get(team, 0.0), strength, cap)
        dropped = apply_start_offset(base, only.get(team, 0.0), strength, cap)
        deltas.append(abs(full - dropped))
    return {
        'n_fbs_2024': len(deltas),
        'mean_abs_start_change': sum(deltas) / len(deltas),
        'max_abs_start_change': max(deltas),
        'cap': cap,
        'bar_mean_abs_at_most': 25.0,
        'bar_max_at_most': cap,
        'passes_mean': (sum(deltas) / len(deltas)) <= 25.0,
        'passes_max': max(deltas) <= cap,
    }


def main():
    if HOLDOUT_2025 != 'PENDING':
        raise SystemExit('2025 stays PENDING in this script.')
    print('load', flush=True)
    by_year = {year: load_year(year) for year in range(2017, 2025)}
    cold = {}
    for year in range(2017, 2024):
        cold[year] = cold_frs(by_year[year])
        print('cold', year, len(cold[year]), flush=True)
    raw_by_year = {}
    offsets_by_year = {}
    weights = DEFAULT_CONFIG['prior_offset_weights']
    for year in range(2019, 2025):
        raw_by_year[year] = legacy_blend(cold[year - 1], cold[year - 2])
        offsets_by_year[year] = earned_start_offsets(
            [
                {'year': year - 1, 'scores': cold[year - 1]},
                {'year': year - 2, 'scores': cold[year - 2]},
            ],
            weights,
        )
        print('offsets', year, len(offsets_by_year[year]), flush=True)

    tune = WINDOWS['tune_2019_2022']
    grid = []
    for strength in GRID:
        rows = score_arm(
            by_year, tune, arm_settings('c_held', strength, raw_by_year, offsets_by_year),
        )
        summary = summarize(rows, 'fbs_fbs')
        grid.append({'strength': strength, 'n': summary['n'], 'brier': summary['brier']})
        print('GRID', grid[-1], flush=True)
    strength = pick_strength(grid)
    print('PICK', strength, flush=True)

    arms = {}
    for kind in ('main', 'a', 'c_level', 'c_faded', 'c_held', 'a_c'):
        arms[kind] = {}
        for label, years in WINDOWS.items():
            rows = score_arm(
                by_year, years, arm_settings(kind, strength, raw_by_year, offsets_by_year),
            )
            arms[kind][label] = rows
            print('ARM', kind, label, summarize(rows, 'fbs_involved')['brier'], flush=True)
        arms[kind]['pooled_2019_2024'] = (
            arms[kind]['tune_2019_2022']
            + arms[kind]['validate_2023']
            + arms[kind]['confirm_2024']
        )

    def pack(kind, label, baseline_kind, tag):
        return {
            'arm': summarize(arms[kind][label], tag),
            'baseline': summarize(arms[baseline_kind][label], tag),
            'arm_minus_baseline': paired(arms[baseline_kind][label], arms[kind][label], tag),
            'cross_calibration_arm': calibration(arms[kind][label]),
            'cross_calibration_baseline': calibration(arms[baseline_kind][label]),
        }

    labels = list(WINDOWS) + ['pooled_2019_2024']
    comparisons = {
        'a_minus_main': {label: pack('a', label, 'main', 'fbs_involved') for label in labels},
        'c_level_minus_main': {label: pack('c_level', label, 'main', 'fbs_involved') for label in labels},
        'c_faded_minus_main': {label: pack('c_faded', label, 'main', 'fbs_involved') for label in labels},
        'c_held_minus_main': {label: pack('c_held', label, 'main', 'fbs_involved') for label in labels},
        'c_held_minus_main_fbs_fbs': {label: pack('c_held', label, 'main', 'fbs_fbs') for label in labels},
        'a_c_minus_c_held': {label: pack('a_c', label, 'c_held', 'fbs_involved') for label in labels},
        'a_c_minus_main': {label: pack('a_c', label, 'main', 'fbs_involved') for label in labels},
    }
    out = {
        'protocol': {
            'hfa': HFA,
            'weeks': '1-15',
            'bootstrap': 2000,
            'seed': 20261111,
            'grid': list(GRID),
            'chosen_strength': strength,
            'holdout_2025': HOLDOUT_2025,
        },
        'grid_tune_fbs_fbs': grid,
        'comparisons': comparisons,
        'results_dominate': dominate(by_year, offsets_by_year, strength),
        'echo_2022_on_2024_starts': echo(strength),
    }
    path = os.path.join(ROOT, 'docs', 'earned-start-brier.json')
    json.dump(out, open(path, 'w'), indent=2)
    open(path, 'a').write('\n')
    print('WROTE', path, flush=True)
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
