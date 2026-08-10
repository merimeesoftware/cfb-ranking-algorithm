#!/usr/bin/env python3
"""Run roadmap eval suite: baseline, reference_ranks A/B, Elo sweep, FRS weights.

Writes JSON under docs/ and prints a markdown summary suitable for
ALGORITHM_EVAL_RESULTS.md. Prefers CFBD_OFFLINE=1 after warm_cfbd_cache.py.
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

    # Validate on 2023, report on 2024 (plan season split; skip deep history for CFBD budget)
    max_week = 12  # regular season core; keeps runtime sane
    years = [2023, 2024]
    games_by_year = {}
    for y in years:
        print(f'Loading {y}...')
        games_by_year[y] = _load_games(y, max_week=max_week)
        print(f'  {len(games_by_year[y])} FBS-involved games through week {max_week}')

    base = DEFAULT_CONFIG.copy()
    # No priors for first pass — isolates in-season Elo signal and avoids nested prior seasons
    results_payload: Dict[str, Any] = {
        'algo_version_at_run': ALGO_VERSION,
        'max_week': max_week,
        'priors': False,
        'protocol': 'week_by_week_leak_free',
        'rating_field': 'team_quality_score',
    }

    # --- Baseline (current defaults, reference ranks ON) ---
    print('\n=== Baseline (use_reference_ranks=True) ===')
    t0 = time.time()
    baseline_results = []
    for y in years:
        cfg = {**base, 'use_reference_ranks': True}
        r = backtest_season(games_by_year[y], y, config=cfg, priors=None)
        baseline_results.append(r)
        print(f"  {y}: {_summarize(r)}")
    results_payload['baseline_ref_on'] = {
        'per_season': [_summarize(r) for r in baseline_results],
        'pooled': aggregate_results(baseline_results)['pooled'],
        'elapsed_s': round(time.time() - t0, 1),
    }

    # --- A/B reference ranks OFF ---
    print('\n=== A/B (use_reference_ranks=False) ===')
    t0 = time.time()
    ab_results = []
    for y in years:
        cfg = {**base, 'use_reference_ranks': False}
        r = backtest_season(games_by_year[y], y, config=cfg, priors=None)
        ab_results.append(r)
        print(f"  {y}: {_summarize(r)}")
    results_payload['ab_ref_off'] = {
        'per_season': [_summarize(r) for r in ab_results],
        'pooled': aggregate_results(ab_results)['pooled'],
        'elapsed_s': round(time.time() - t0, 1),
    }

    brier_on = results_payload['baseline_ref_on']['pooled']['brier']
    brier_off = results_payload['ab_ref_off']['pooled']['brier']
    keep_ref = brier_on <= brier_off
    results_payload['reference_ranks_decision'] = {
        'keep_use_reference_ranks': keep_ref,
        'brier_on': brier_on,
        'brier_off': brier_off,
        'delta': round(brier_off - brier_on, 6),
        'rationale': (
            'Keep True — lower/equal pooled Brier on 2023–2024'
            if keep_ref
            else 'Revert to False — reference ranks hurt pooled Brier'
        ),
    }
    print(f"\nReference ranks decision: keep={keep_ref} (on={brier_on:.5f} off={brier_off:.5f})")

    preferred_ref = keep_ref
    base_pref = {**base, 'use_reference_ranks': preferred_ref}

    # --- Elo sweep on 2023 (validate), score 2024 holdout ---
    print('\n=== Elo sweep (validate=2023) ===')
    t0 = time.time()
    elo_grid = {
        'base_factor': [30.0, 40.0, 50.0],
        'hfa_elo': [50.0, 65.0, 80.0],
        'upset_bonus_mult': [1.0, 1.18],
    }
    elo_rows = sweep_configs(
        {2023: games_by_year[2023]},
        elo_grid,
        base_config=base_pref,
    )
    top = elo_rows[0]
    print(f"  Best on 2023: brier={top['score']:.5f} config={top['config']}")

    # Score top config + default on 2024 holdout
    holdout = {}
    for label, cfg in (
        ('default', base_pref),
        ('swept', {**base_pref, **top['config']}),
    ):
        r = backtest_season(games_by_year[2024], 2024, config=cfg, priors=None)
        holdout[label] = _summarize(r)
        print(f"  2024 holdout {label}: {holdout[label]}")

    promote_elo = (
        holdout['swept']['brier'] + 1e-9 < holdout['default']['brier']
        and (holdout['default']['brier'] - holdout['swept']['brier']) >= 0.0005
    )
    # Also require non-worse vs always-home lift
    if holdout['swept']['brier_lift_vs_home'] + 1e-9 < holdout['default']['brier_lift_vs_home'] - 0.002:
        promote_elo = False

    results_payload['elo_sweep'] = {
        'grid': elo_grid,
        'best_on_2023': {'config': top['config'], 'score': top['score']},
        'top5': [{'config': r['config'], 'score': r['score']} for r in elo_rows[:5]],
        'holdout_2024': holdout,
        'promote': promote_elo,
        'elapsed_s': round(time.time() - t0, 1),
    }
    print(f"Promote Elo sweep config? {promote_elo}")

    promoted_config = {**base_pref, **(top['config'] if promote_elo else {})}

    # --- FRS weight triples (ranking-order predictor via final_ranking_score) ---
    print('\n=== FRS weight triples (predict with final_ranking_score) ===')
    t0 = time.time()
    weight_sets = [
        {'team_quality_weight': 0.65, 'record_weight': 0.27, 'conference_weight': 0.08},
        {'team_quality_weight': 0.70, 'record_weight': 0.22, 'conference_weight': 0.08},
        {'team_quality_weight': 0.60, 'record_weight': 0.32, 'conference_weight': 0.08},
        {'team_quality_weight': 0.75, 'record_weight': 0.20, 'conference_weight': 0.05},
        {'team_quality_weight': 0.55, 'record_weight': 0.35, 'conference_weight': 0.10},
    ]
    frs_rows = []
    for weights in weight_sets:
        cfg = {**promoted_config, **weights}
        r23 = backtest_season(
            games_by_year[2023], 2023, config=cfg, priors=None,
            rating_field='final_ranking_score',
        )
        r24 = backtest_season(
            games_by_year[2024], 2024, config=cfg, priors=None,
            rating_field='final_ranking_score',
        )
        pooled = aggregate_results([r23, r24])['pooled']
        frs_rows.append({
            'weights': weights,
            'brier_2023': round(r23.model.brier, 5),
            'brier_2024': round(r24.model.brier, 5),
            'pooled_brier': round(pooled['brier'], 5),
            'pooled_accuracy': round(pooled['accuracy'], 4),
        })
        print(f"  {weights} pooled_brier={pooled['brier']:.5f}")
    frs_rows.sort(key=lambda x: x['pooled_brier'])
    best_frs = frs_rows[0]
    default_frs = next(
        r for r in frs_rows
        if r['weights']['team_quality_weight'] == 0.65
    )
    promote_frs = best_frs['pooled_brier'] + 0.001 < default_frs['pooled_brier']
    results_payload['frs_weights'] = {
        'rows': frs_rows,
        'best': best_frs,
        'default': default_frs,
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
