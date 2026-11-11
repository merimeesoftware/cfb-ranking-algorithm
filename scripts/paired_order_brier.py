"""Paired Brier for the Elo order and the upset step. Offline. 2025 is refused.

Reads game rows from TR_GAMES_DIR (games-YYYY-both.json, 2017-2024 only).
Does not copy those rows into the repo. Home field is 50.
"""
from __future__ import annotations

import json
import os
import random
import sys
from collections import defaultdict

os.environ.setdefault('CFBD_OFFLINE', '1')
os.environ.setdefault('AI_MODE', 'stub')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

GAMES = os.environ.get('TR_GAMES_DIR', '')
if not GAMES:
    raise SystemExit('Set TR_GAMES_DIR to the 2017-2024 game rows. 2025 is not read.')

from api_integration import CFBDApiClient
from data_processor import CFBDataProcessor
from ranking_algorithm import TeamQualityRanker
from ranking_service import DEFAULT_CONFIG
from algo_lab.predict import predict_game
from algo_lab.runner import preseason_ratings, rank_through_week, ratings_from_rankings

FBS = {'Power 4', 'Group of 5'}
HFA = 50.0


def load_year(year):
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


def cold(games, config):
    ranker = TeamQualityRanker(config)
    by_week = defaultdict(list)
    for game in games:
        by_week[int(game['week'])].append(game)
    for week in sorted(by_week):
        for game in by_week[week]:
            ranker.update_quality_scores(game)
    results = ranker.calculate_final_rankings()
    return {
        name: float(data['final_ranking_score'])
        for name, data in results.get('rankings', {}).items()
        if isinstance(data.get('final_ranking_score'), (int, float))
    }


def blend(newer, older):
    priors = {}
    for name in set(newer) | set(older):
        total = 0.0
        if name in newer:
            total += 0.70 * newer[name]
        if name in older:
            total += 0.30 * older[name]
        if total:
            priors[name] = total
    return priors


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


def score_arm(by_year, colds, years, config):
    """Return list of (year, week, brier_sq) per game, using Elo."""
    rows = []
    for year in years:
        games = by_year[year]
        priors = blend(colds[year - 1], colds[year - 2])
        meta = meta_of(games)
        pre = preseason_ratings(config=config, priors=priors, team_meta=meta)
        weeks = sorted({int(g['week']) for g in games})
        for week in weeks:
            if week == 1:
                ratings = pre
            else:
                rankings, _ = rank_through_week(games, week - 1, config=config, priors=priors)
                ratings = dict(pre)
                ratings.update(ratings_from_rankings(rankings, field='team_quality_score'))
            for game in games:
                if int(game['week']) != week:
                    continue
                if game.get('home_conference_type') not in FBS and game.get('away_conference_type') not in FBS:
                    continue
                pred = predict_game(game, ratings, hfa_regular=HFA)
                if pred is None:
                    continue
                y = 1.0 if pred['home_won'] else 0.0
                rows.append((year, week, (pred['p_home'] - y) ** 2))
    return rows


def summarize(rows):
    if not rows:
        return {'n': 0, 'brier': None}
    return {'n': len(rows), 'brier': sum(item[2] for item in rows) / len(rows)}


def paired(base_rows, alt_rows):
    # zip assumes identical game order
    assert len(base_rows) == len(alt_rows)
    by_week = defaultdict(list)
    diffs = []
    for left, right in zip(base_rows, alt_rows):
        assert left[0] == right[0] and left[1] == right[1]
        delta = right[2] - left[2]
        diffs.append(delta)
        by_week[(left[0], left[1])].append(delta)
    point = sum(diffs) / len(diffs)
    weeks = list(by_week.values())
    rng = random.Random(20261111)
    means = []
    for _ in range(2000):
        drawn = [weeks[rng.randrange(len(weeks))] for _ in range(len(weeks))]
        pooled = [x for week in drawn for x in week]
        means.append(sum(pooled) / len(pooled))
    means.sort()
    return {
        'n': len(diffs),
        'n_weeks': len(weeks),
        'point': point,
        'ci_low': means[int(0.025 * 2000)],
        'ci_high': means[int(0.975 * 2000) - 1],
    }


def main():
    print('load', flush=True)
    by_year = {year: load_year(year) for year in range(2017, 2025)}
    base_cfg = {k: v for k, v in DEFAULT_CONFIG.items() if k != 'prior_strength'}
    flat_cfg = dict(base_cfg)
    flat_cfg['upset_bonus_mult'] = 1.0
    cold_base = {}
    cold_flat = {}
    full_base = DEFAULT_CONFIG.copy()
    full_flat = DEFAULT_CONFIG.copy()
    full_flat['upset_bonus_mult'] = 1.0
    for year in range(2017, 2024):
        cold_base[year] = cold(by_year[year], full_base)
        cold_flat[year] = cold(by_year[year], full_flat)
        print('cold', year, flush=True)
    windows = {
        'tune_2019_2022': [2019, 2020, 2021, 2022],
        'validate_2023': [2023],
        'test_2024': [2024],
    }
    out = []
    for label, years in windows.items():
        base_rows = score_arm(by_year, cold_base, years, base_cfg)
        alt_rows = score_arm(by_year, cold_flat, years, flat_cfg)
        row = {
            'window': label,
            'current': summarize(base_rows),
            'bonus_1': summarize(alt_rows),
            'bonus1_minus_current': paired(base_rows, alt_rows),
        }
        out.append(row)
        print('ROW', row, flush=True)
    json.dump(out, open('/tmp/tr-upset-brier.json', 'w'), indent=2)
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
