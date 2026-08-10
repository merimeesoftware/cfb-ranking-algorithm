#!/usr/bin/env python3
"""CLI: week-by-week predictive backtest for the ranking algorithm.

Examples
--------
  # Offline synthetic smoke is in pytest; real seasons need games in cache or live CFBD:
  CFBD_OFFLINE=0 ./venv/bin/python scripts/backtest_rankings.py --years 2024 --max-week 10

  # Compare Elo vs FRS as predictors:
  ./venv/bin/python scripts/backtest_rankings.py --years 2023,2024 --rating-field team_quality_score
  ./venv/bin/python scripts/backtest_rankings.py --years 2023,2024 --rating-field final_ranking_score

  # Small hyperparameter sweep (expensive — many full-season recomputes):
  ./venv/bin/python scripts/backtest_rankings.py --years 2023 --sweep --max-week 8
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

# Repo root on path when run as scripts/backtest_rankings.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _parse_years(raw: str) -> List[int]:
    years: List[int] = []
    for part in raw.split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            a, b = part.split('-', 1)
            years.extend(range(int(a), int(b) + 1))
        else:
            years.append(int(part))
    return years


def _load_season_games(year: int, max_week: Optional[int]) -> List[Dict[str, Any]]:
    from data_processor import CFBDataProcessor

    processor = CFBDataProcessor()
    # Full-season fetch hits cache after warm_cfbd_cache.py; avoids week-scoped CFBD spam.
    games = processor.get_games_for_season(
        year,
        through_week=None,
        use_week_scoped_fetch=False,
    )
    if max_week is not None:
        games = [g for g in games if int(g.get('week', 0)) <= max_week]
    # FBS-involved only (exclude FCS-vs-FCS noise); matches production ranking focus.
    games = [
        g for g in games
        if g.get('home_conference_type') != 'FCS' or g.get('away_conference_type') != 'FCS'
    ]
    if not games:
        raise SystemExit(
            f'No games for {year} (through_week={max_week}). '
            'Warm .cache/ or set CFBD_OFFLINE=0 with a valid CFBD_API_KEY.'
        )
    return games


def _compute_priors(year: int, config: Dict[str, Any]) -> Dict[str, float]:
    from data_processor import CFBDataProcessor
    from ranking_service import compute_priors

    processor = CFBDataProcessor()
    return compute_priors(processor, year, config)


def main() -> int:
    parser = argparse.ArgumentParser(description='CFB ranking predictive backtest')
    parser.add_argument(
        '--years',
        required=True,
        help='Comma list or range, e.g. 2024 or 2022-2024',
    )
    parser.add_argument('--max-week', type=int, default=None, help='Last outcome week to score')
    parser.add_argument('--min-week', type=int, default=1, help='First outcome week to score')
    parser.add_argument(
        '--rating-field',
        default='team_quality_score',
        choices=['team_quality_score', 'final_ranking_score'],
        help='Rating used for P(home). Prefer team_quality_score (Elo).',
    )
    parser.add_argument('--no-priors', action='store_true', help='Skip historical priors')
    parser.add_argument('--sweep', action='store_true', help='Run small hyperparameter grid')
    parser.add_argument('--json-out', default=None, help='Write full results JSON to path')
    parser.add_argument('--predictions', action='store_true', help='Include per-game predictions in JSON')
    args = parser.parse_args()

    from ranking_service import DEFAULT_CONFIG
    from algo_lab.backtest import aggregate_results, backtest_season
    from algo_lab.sweep import suggest_default_grid, sweep_configs

    years = _parse_years(args.years)
    config = DEFAULT_CONFIG.copy()
    games_by_year: Dict[int, List[Dict[str, Any]]] = {}
    priors_by_year: Dict[int, Dict[str, float]] = {}

    for year in years:
        print(f'Loading games for {year}...')
        games_by_year[year] = _load_season_games(year, args.max_week)
        print(f'  {len(games_by_year[year])} games')
        if not args.no_priors:
            try:
                priors_by_year[year] = _compute_priors(year, config)
                print(f'  priors for {len(priors_by_year[year])} teams')
            except Exception as exc:
                print(f'  priors unavailable ({exc}); continuing without')

    if args.sweep:
        print('Running config sweep (this recomputes rankings many times)...')
        rows = sweep_configs(
            games_by_year,
            suggest_default_grid(),
            priors_by_year=priors_by_year,
            base_config=config,
        )
        print('\nTop configs by Brier (lower is better):')
        for i, row in enumerate(rows[:10], 1):
            p = row['pooled']
            print(
                f"  {i:2d}. brier={p['brier']:.4f} acc={p['accuracy']:.3f} "
                f"ll={p['log_loss']:.4f}  {row['config']}"
            )
        payload: Dict[str, Any] = {'sweep': rows}
    else:
        results = []
        for year in years:
            print(f'Backtesting {year} ({args.rating_field})...')
            result = backtest_season(
                games_by_year[year],
                year,
                config=config,
                priors=priors_by_year.get(year),
                rating_field=args.rating_field,
                min_week=args.min_week,
                max_week=args.max_week,
            )
            results.append(result)
            m = result.model
            home = result.baselines.get('always_home')
            print(
                f"  games={m.n_games}  accuracy={m.accuracy:.3f}  "
                f"brier={m.brier:.4f}  log_loss={m.log_loss:.4f}"
            )
            if home:
                lift = result.lifts['always_home']
                print(
                    f"  vs always-home: accuracy {lift['accuracy_lift']:+.3f}  "
                    f"brier {lift['brier_improvement']:+.4f}"
                )
            if m.by_week:
                print('  by week (acc / brier):')
                for week in sorted(m.by_week):
                    w = m.by_week[week]
                    print(f"    W{week:02d}: n={int(w['n']):3d}  "
                          f"acc={w['accuracy']:.3f}  brier={w['brier']:.4f}")

        pooled = aggregate_results(results)
        print('\nPooled across seasons:')
        p = pooled['pooled']
        print(
            f"  games={p['n_games']}  accuracy={p['accuracy']:.3f}  "
            f"brier={p['brier']:.4f}  log_loss={p['log_loss']:.4f}"
        )
        payload = {
            'pooled': pooled,
            'seasons': [
                r.to_dict(include_predictions=args.predictions) for r in results
            ],
        }

    if args.json_out:
        with open(args.json_out, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)
        print(f'Wrote {args.json_out}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
