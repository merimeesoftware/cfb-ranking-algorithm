#!/usr/bin/env python3
"""Run roadmap eval suite with proper season splits.

Default split (plan):
  tune     = 2019–2022  (Elo/FRS sweeps)
  validate = 2023       (gate promotions)
  holdout  = 2024       (final report; never used to pick params)

Writes docs/algo_eval_results.json. Prefers CFBD_OFFLINE=1 after warm_cfbd_cache.py.
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('FLASK_ENV', 'development')
os.environ.setdefault('CFBD_OFFLINE', '1')
os.environ.setdefault('CFBD_MAX_CALLS', '10')

TUNE_YEARS = [2019, 2020, 2021, 2022]
VALIDATE_YEAR = 2023
HOLDOUT_YEAR = 2024


def _load_games(year: int, max_week: Optional[int] = None) -> List[Dict[str, Any]]:
    from data_processor import CFBDataProcessor

    processor = CFBDataProcessor()
    games = processor.get_games_for_season(year, through_week=None, use_week_scoped_fetch=False)
    if max_week is not None:
        games = [g for g in games if int(g.get('week', 0)) <= max_week]
    return [
        g for g in games
        if g.get('home_conference_type') != 'FCS' or g.get('away_conference_type') != 'FCS'
    ]


def _summarize(result) -> Dict[str, Any]:
    m = result.model
    home = result.baselines.get('always_home')
    lift = result.lifts.get('always_home', {})
    return {
        'year': result.year,
        'n_games': m.n_games,
        'accuracy': round(m.accuracy, 4),
        'brier': round(m.brier, 5),
        'log_loss': round(m.log_loss, 5),
        'home_brier': round(home.brier, 5) if home else None,
        'brier_lift_vs_home': round(lift.get('brier_improvement', 0.0), 5),
        'accuracy_lift_vs_home': round(lift.get('accuracy_lift', 0.0), 5),
    }


def main() -> int:
    from ranking_service import DEFAULT_CONFIG, ALGO_VERSION
    from algo_lab.backtest import aggregate_results, backtest_season
    from algo_lab.sweep import sweep_configs

    max_week = 12
    all_years = TUNE_YEARS + [VALIDATE_YEAR, HOLDOUT_YEAR]
    games_by_year: Dict[int, List[Dict[str, Any]]] = {}
    for y in all_years:
        print(f'Loading {y}...')
        games_by_year[y] = _load_games(y, max_week=max_week)
        print(f'  {len(games_by_year[y])} FBS-involved games through week {max_week}')
        if not games_by_year[y]:
            raise SystemExit(
                f'No games for {y}. Run: CFBD_OFFLINE=0 ./venv/bin/python '
                f'scripts/warm_cfbd_cache.py {" ".join(str(x) for x in all_years)}'
            )

    base = DEFAULT_CONFIG.copy()
    results_payload: Dict[str, Any] = {
        'algo_version_at_run': ALGO_VERSION,
        'max_week': max_week,
        'priors': False,
        'protocol': 'week_by_week_leak_free',
        'rating_field': 'team_quality_score',
        'split': {
            'tune': TUNE_YEARS,
            'validate': VALIDATE_YEAR,
            'holdout': HOLDOUT_YEAR,
        },
    }

    # --- Baseline A/B on validate+holdout (reporting seasons) ---
    report_years = [VALIDATE_YEAR, HOLDOUT_YEAR]
    print('\n=== Baseline (use_reference_ranks=True) on validate+holdout ===')
    t0 = time.time()
    baseline_results = []
    for y in report_years:
        cfg = {**base, 'use_reference_ranks': True}
        r = backtest_season(games_by_year[y], y, config=cfg, priors=None)
        baseline_results.append(r)
        print(f"  {y}: {_summarize(r)}")
    results_payload['baseline_ref_on'] = {
        'per_season': [_summarize(r) for r in baseline_results],
        'pooled': aggregate_results(baseline_results)['pooled'],
        'elapsed_s': round(time.time() - t0, 1),
    }

    print('\n=== A/B (use_reference_ranks=False) on validate+holdout ===')
    t0 = time.time()
    ab_results = []
    for y in report_years:
        cfg = {**base, 'use_reference_ranks': False}
        r = backtest_season(games_by_year[y], y, config=cfg, priors=None)
        ab_results.append(r)
        print(f"  {y}: {_summarize(r)}")
    results_payload['ab_ref_off'] = {
        'per_season': [_summarize(r) for r in ab_results],
        'pooled': aggregate_results(ab_results)['pooled'],
        'elapsed_s': round(time.time() - t0, 1),
    }

    # Also score ref A/B on tune years for stability
    print('\n=== Reference-ranks A/B pooled on TUNE years ===')
    tune_on = [
        backtest_season(games_by_year[y], y, config={**base, 'use_reference_ranks': True}, priors=None)
        for y in TUNE_YEARS
    ]
    tune_off = [
        backtest_season(games_by_year[y], y, config={**base, 'use_reference_ranks': False}, priors=None)
        for y in TUNE_YEARS
    ]
    tune_on_brier = aggregate_results(tune_on)['pooled']['brier']
    tune_off_brier = aggregate_results(tune_off)['pooled']['brier']
    print(f'  tune ref_on brier={tune_on_brier:.5f}  ref_off brier={tune_off_brier:.5f}')

    # Decision: prefer lower Brier on tune; confirm on validate
    keep_ref = tune_on_brier <= tune_off_brier
    val_on = next(r for r in baseline_results if r.year == VALIDATE_YEAR).model.brier
    val_off = next(r for r in ab_results if r.year == VALIDATE_YEAR).model.brier
    if keep_ref and val_on > val_off + 0.002:
        keep_ref = False
    if (not keep_ref) and val_off > val_on + 0.002:
        keep_ref = True

    results_payload['reference_ranks_decision'] = {
        'keep_use_reference_ranks': keep_ref,
        'tune_brier_on': tune_on_brier,
        'tune_brier_off': tune_off_brier,
        'validate_brier_on': val_on,
        'validate_brier_off': val_off,
        'rationale': (
            'Keep True — better/equal on tune and not worse on validate'
            if keep_ref
            else 'Keep False — better without reference ranks'
        ),
    }
    print(f"\nReference ranks decision: keep={keep_ref}")

    preferred_ref = keep_ref
    base_pref = {**base, 'use_reference_ranks': preferred_ref}

    # --- Elo sweep on TUNE years; gate on VALIDATE; report HOLDOUT ---
    print(f'\n=== Elo sweep (tune={TUNE_YEARS}) ===')
    t0 = time.time()
    elo_grid = {
        'base_factor': [30.0, 40.0, 50.0],
        'hfa_elo': [50.0, 65.0, 80.0],
        'upset_bonus_mult': [1.0, 1.18],
    }
    tune_games = {y: games_by_year[y] for y in TUNE_YEARS}
    elo_rows = sweep_configs(tune_games, elo_grid, base_config=base_pref)
    top = elo_rows[0]
    print(f"  Best on tune: brier={top['score']:.5f} config={top['config']}")

    gate = {}
    for label, cfg in (
        ('default', base_pref),
        ('swept', {**base_pref, **top['config']}),
    ):
        r_val = backtest_season(games_by_year[VALIDATE_YEAR], VALIDATE_YEAR, config=cfg, priors=None)
        r_hold = backtest_season(games_by_year[HOLDOUT_YEAR], HOLDOUT_YEAR, config=cfg, priors=None)
        gate[label] = {
            'validate': _summarize(r_val),
            'holdout': _summarize(r_hold),
        }
        print(f"  {label} validate={gate[label]['validate']['brier']:.5f} "
              f"holdout={gate[label]['holdout']['brier']:.5f}")

    # Promote only if validate improves enough AND holdout does not regress
    val_improve = gate['default']['validate']['brier'] - gate['swept']['validate']['brier']
    hold_delta = gate['default']['holdout']['brier'] - gate['swept']['holdout']['brier']
    promote_elo = val_improve >= 0.0005 and hold_delta >= -0.001
    if gate['swept']['validate']['brier_lift_vs_home'] + 1e-9 < gate['default']['validate']['brier_lift_vs_home'] - 0.002:
        promote_elo = False

    results_payload['elo_sweep'] = {
        'grid': elo_grid,
        'best_on_tune': {'config': top['config'], 'score': top['score']},
        'top5': [{'config': r['config'], 'score': r['score']} for r in elo_rows[:5]],
        'gate': gate,
        'promote': promote_elo,
        'elapsed_s': round(time.time() - t0, 1),
    }
    print(f"Promote Elo sweep config? {promote_elo}")

    promoted_config = {**base_pref, **(top['config'] if promote_elo else {})}

    # --- FRS weights: tune pooled Brier, gate on validate, report holdout ---
    print('\n=== FRS weight triples (predict with final_ranking_score) ===')
    t0 = time.time()
    current_w = {
        'team_quality_weight': DEFAULT_CONFIG['team_quality_weight'],
        'record_weight': DEFAULT_CONFIG['record_weight'],
        'conference_weight': DEFAULT_CONFIG['conference_weight'],
    }
    weight_sets = [
        current_w,
        {'team_quality_weight': 0.65, 'record_weight': 0.27, 'conference_weight': 0.08},
        {'team_quality_weight': 0.70, 'record_weight': 0.22, 'conference_weight': 0.08},
        {'team_quality_weight': 0.60, 'record_weight': 0.32, 'conference_weight': 0.08},
        {'team_quality_weight': 0.80, 'record_weight': 0.15, 'conference_weight': 0.05},
        {'team_quality_weight': 0.75, 'record_weight': 0.20, 'conference_weight': 0.05},
        {'team_quality_weight': 0.55, 'record_weight': 0.35, 'conference_weight': 0.10},
    ]
    # de-dupe identical dicts
    seen = set()
    unique_weights = []
    for w in weight_sets:
        key = tuple(sorted(w.items()))
        if key not in seen:
            seen.add(key)
            unique_weights.append(w)

    frs_rows = []
    for weights in unique_weights:
        cfg = {**promoted_config, **weights}
        season_results = [
            backtest_season(
                games_by_year[y], y, config=cfg, priors=None,
                rating_field='final_ranking_score',
            )
            for y in all_years
        ]
        by_year = {r.year: round(r.model.brier, 5) for r in season_results}
        tune_pooled = aggregate_results([r for r in season_results if r.year in TUNE_YEARS])['pooled']
        frs_rows.append({
            'weights': weights,
            'brier_by_year': by_year,
            'tune_brier': round(tune_pooled['brier'], 5),
            'validate_brier': by_year[VALIDATE_YEAR],
            'holdout_brier': by_year[HOLDOUT_YEAR],
        })
        print(
            f"  {weights} tune={tune_pooled['brier']:.5f} "
            f"val={by_year[VALIDATE_YEAR]:.5f} hold={by_year[HOLDOUT_YEAR]:.5f}"
        )

    frs_rows.sort(key=lambda x: (x['tune_brier'], x['validate_brier']))
    best_frs = frs_rows[0]
    current_frs = next(
        r for r in frs_rows
        if r['weights']['team_quality_weight'] == current_w['team_quality_weight']
        and r['weights']['record_weight'] == current_w['record_weight']
        and r['weights']['conference_weight'] == current_w['conference_weight']
    )
    promote_frs = (
        best_frs['tune_brier'] + 0.001 < current_frs['tune_brier']
        and best_frs['validate_brier'] <= current_frs['validate_brier'] + 0.001
        and best_frs['holdout_brier'] <= current_frs['holdout_brier'] + 0.002
    )
    results_payload['frs_weights'] = {
        'rows': frs_rows,
        'best': best_frs,
        'current': current_frs,
        'promote': promote_frs,
        'elapsed_s': round(time.time() - t0, 1),
    }
    print(f"Promote FRS weights? {promote_frs} best={best_frs['weights']}")

    if promote_frs:
        promoted_config.update(best_frs['weights'])

    results_payload['promoted_config'] = {
        k: promoted_config[k]
        for k in (
            'base_factor', 'hfa_elo', 'upset_bonus_mult', 'use_reference_ranks',
            'team_quality_weight', 'record_weight', 'conference_weight',
        )
        if k in promoted_config
    }
    results_payload['promotions'] = {
        'use_reference_ranks': preferred_ref,
        'elo_hparams': promote_elo,
        'frs_weights': promote_frs,
    }

    out_json = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'docs',
        'algo_eval_results.json',
    )
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(results_payload, f, indent=2)
    print(f'\nWrote {out_json}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
