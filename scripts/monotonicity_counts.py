"""Same-week F4/F6 counts. Offline. 2025 is not read.

Game rows come from TR_GAMES_DIR (games-YYYY-both.json for 2017-2024).
Recorded counts: docs/monotonicity-counts.json.
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

os.environ.setdefault('CFBD_OFFLINE', '1')
os.environ.setdefault('AI_MODE', 'stub')
os.environ.setdefault('FLASK_ENV', 'development')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from api_integration import CFBDApiClient
from data_processor import CFBDataProcessor
from ranking_algorithm import TeamQualityRanker
from ranking_service import DEFAULT_CONFIG
from algo_lab.predict import predict_game
from algo_lab.runner import rank_through_week, ratings_from_rankings
from algo_lab.metrics import score_predictions

GAMES_DIR = os.environ.get('TR_GAMES_DIR', '')
if not GAMES_DIR:
    raise SystemExit('Set TR_GAMES_DIR to the 2017-2024 game rows. 2025 is not read.')
YEARS = list(range(2017, 2025))
FBS = {'Power 4', 'Group of 5'}
HFA = 50.0
EPS = 1e-6


def load_year(year: int):
    raw = json.load(open(f'{GAMES_DIR}/games-{year}-both.json'))
    client = CFBDApiClient(api_key='offline-placeholder')
    proc = CFBDataProcessor(api_client=client)
    transformed = [client._transform_game(game) for game in raw]
    processed = proc._process_raw_games(transformed, season=year)
    regular = []
    for game in processed:
        if (game.get('season_type') or 'regular') == 'postseason':
            continue
        week = game.get('week')
        if week is None or int(week) < 1 or int(week) > 15:
            continue
        regular.append(game)
    return regular


def cold_final_scores(games):
    ranker = TeamQualityRanker(DEFAULT_CONFIG.copy())
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
        if isinstance(score, (int, float)):
            scores[name] = float(score)
    return scores


def blend_priors(newer, older):
    priors = {}
    names = set(newer) | set(older)
    for name in names:
        total = 0.0
        if name in newer:
            total += 0.70 * newer[name]
        if name in older:
            total += 0.30 * older[name]
        if total:
            priors[name] = total
    return priors


def is_fbs_fbs(game):
    return game.get('home_conference_type') in FBS and game.get('away_conference_type') in FBS


def margin_one(game):
    copy = dict(game)
    home = copy['home_score']
    away = copy['away_score']
    if home == away:
        return None
    if home > away:
        copy['home_score'] = away + 1
    else:
        copy['away_score'] = home + 1
    return copy


def winner_name(game):
    if game['home_score'] > game['away_score']:
        return game['home_team_name']
    if game['away_score'] > game['home_score']:
        return game['away_team_name']
    return None


def score_of(rankings, name, field):
    for team in rankings['team_rankings']:
        if team['team_name'] == name:
            return float(team[field])
    return None


def fbs_names(rankings):
    names = []
    for team in rankings['team_rankings']:
        if team.get('conference_type') in FBS:
            decisions = team['records']['total_wins'] + team['records']['total_losses']
            if decisions >= 1:
                names.append(team['team_name'])
    return names


def main():
    print('loading', flush=True)
    by_year = {year: load_year(year) for year in YEARS}
    print({year: len(games) for year, games in by_year.items()}, flush=True)
    cold = {}
    for year in range(2017, 2024):
        cold[year] = cold_final_scores(by_year[year])
        print('cold', year, len(cold[year]), flush=True)

    # Paired Brier, HFA 50, regular season, priors, Elo vs blend.
    windows = {
        'tune_2019_2022': [2019, 2020, 2021, 2022],
        'validate_2023': [2023],
        'holdout_2024': [2024],
    }
    brier_rows = []
    for label, years in windows.items():
        elo_preds = []
        blend_preds = []
        for year in years:
            games = by_year[year]
            priors = blend_priors(cold[year - 1], cold[year - 2])
            weeks = sorted({int(game['week']) for game in games})
            for week in weeks:
                if week == 1:
                    from algo_lab.runner import preseason_ratings
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
                    rankings = None
                    ratings_elo = preseason_ratings(priors=priors, team_meta=meta)
                    ratings_blend = ratings_elo
                else:
                    rankings, _ = rank_through_week(games, week - 1, priors=priors)
                    ratings_elo = ratings_from_rankings(rankings, field='team_quality_score')
                    ratings_blend = ratings_from_rankings(rankings, field='final_ranking_score')
                for game in games:
                    if int(game['week']) != week:
                        continue
                    if game.get('home_conference_type') not in FBS and game.get('away_conference_type') not in FBS:
                        continue
                    pred_elo = predict_game(game, ratings_elo, hfa_regular=HFA)
                    pred_blend = predict_game(game, ratings_blend, hfa_regular=HFA)
                    if pred_elo is None or pred_blend is None:
                        continue
                    elo_preds.append(pred_elo)
                    blend_preds.append(pred_blend)
        elo_m = score_predictions(elo_preds)
        blend_m = score_predictions(blend_preds)
        paired = 0.0
        for left, right in zip(elo_preds, blend_preds):
            y = 1.0 if left['home_won'] else 0.0
            paired += (right['p_home'] - y) ** 2 - (left['p_home'] - y) ** 2
        paired /= len(elo_preds)
        row = {
            'window': label,
            'n': elo_m.n_games,
            'elo_brier': elo_m.brier,
            'blend_brier': blend_m.brier,
            'blend_minus_elo': paired,
        }
        brier_rows.append(row)
        print('BRIER', row, flush=True)

    f4_games = 0
    f4_blend = 0
    f4_elo = 0
    f4_blend_max = 0.0
    f4_elo_max = 0.0
    f6_rows = 0
    f6_blend = 0
    f6_elo = 0
    f6_blend_max = 0.0
    f6_elo_max = 0.0

    for year in range(2019, 2025):
        games = by_year[year]
        priors = blend_priors(cold[year - 1], cold[year - 2])
        weeks = sorted({int(game['week']) for game in games})
        indexed = list(enumerate(games))
        for week in weeks:
            base_games = [game for game in games if int(game['week']) <= week]
            base, _ = rank_through_week(base_games, week, priors=priors)
            base_by_name = {team['team_name']: team for team in base['team_rankings']}
            week_games = [(index, game) for index, game in indexed if int(game['week']) == week and is_fbs_fbs(game)]
            for index, game in week_games:
                forced = margin_one(game)
                if forced is None:
                    continue
                alt_games = list(base_games)
                # base_games is filtered by week, so find the same object
                replaced = False
                for pos, candidate in enumerate(alt_games):
                    if candidate is game:
                        alt_games[pos] = forced
                        replaced = True
                        break
                if not replaced:
                    continue
                alt, _ = rank_through_week(alt_games, week, priors=priors)
                name = winner_name(game)
                actual_blend = score_of(base, name, 'final_ranking_score')
                forced_blend = score_of(alt, name, 'final_ranking_score')
                actual_elo = score_of(base, name, 'team_quality_score')
                forced_elo = score_of(alt, name, 'team_quality_score')
                f4_games += 1
                if actual_blend is not None and forced_blend is not None:
                    drop = forced_blend - actual_blend
                    if drop > EPS:
                        f4_blend += 1
                        f4_blend_max = max(f4_blend_max, drop)
                if actual_elo is not None and forced_elo is not None:
                    drop = forced_elo - actual_elo
                    if drop > EPS:
                        f4_elo += 1
                        f4_elo_max = max(f4_elo_max, drop)
            for name in fbs_names(base):
                extra = {
                    'year': year,
                    'week': week,
                    'home_team_name': name,
                    'away_team_name': '__extra_fcs__',
                    'home_score': 35,
                    'away_score': 0,
                    'home_conference': base_by_name[name].get('conference'),
                    'away_conference': None,
                    'home_conference_type': base_by_name[name].get('conference_type'),
                    'away_conference_type': 'FCS',
                    'notes': '',
                    'season_type': 'regular',
                    'neutral_site': False,
                }
                alt, _ = rank_through_week(base_games + [extra], week, priors=priors)
                base_blend = float(base_by_name[name]['final_ranking_score'])
                base_elo = float(base_by_name[name]['team_quality_score'])
                alt_blend = score_of(alt, name, 'final_ranking_score')
                alt_elo = score_of(alt, name, 'team_quality_score')
                f6_rows += 1
                if alt_blend is not None and base_blend - alt_blend > EPS:
                    f6_blend += 1
                    f6_blend_max = max(f6_blend_max, base_blend - alt_blend)
                if alt_elo is not None and base_elo - alt_elo > EPS:
                    f6_elo += 1
                    f6_elo_max = max(f6_elo_max, base_elo - alt_elo)
            print(
                f'done {year} week {week} f4 {f4_blend}/{f4_games} f4elo {f4_elo} f6 {f6_blend}/{f6_rows} f6elo {f6_elo}',
                flush=True,
            )

    summary = {
        'brier': brier_rows,
        'f4_games': f4_games,
        'f4_blend_lower': f4_blend,
        'f4_blend_max_drop': f4_blend_max,
        'f4_elo_lower': f4_elo,
        'f4_elo_max_drop': f4_elo_max,
        'f6_team_weeks': f6_rows,
        'f6_blend_lower': f6_blend,
        'f6_blend_max_drop': f6_blend_max,
        'f6_elo_lower': f6_elo,
        'f6_elo_max_drop': f6_elo_max,
        'population': '2019-2024 regular season weeks 1-15, postseason excluded, membership map, HFA 50, cold priors 0.70/0.30, no 2025',
    }
    json.dump(summary, open('/tmp/tr-mono-summary.json', 'w'), indent=2)
    print('SUMMARY', json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
