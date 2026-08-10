"""Lightweight config sweep for ranking hyperparameters.

This is model selection, not neural training: try discrete configs, score each with
the week-by-week backtest (Brier primary), keep the best on a validation split.
"""
from __future__ import annotations

import itertools
from typing import Any, Dict, List, Optional, Sequence

from algo_lab.backtest import BacktestResult, aggregate_results, backtest_season


def expand_grid(param_grid: Dict[str, Sequence[Any]]) -> List[Dict[str, Any]]:
    """Cartesian product of parameter lists → list of config override dicts."""
    if not param_grid:
        return [{}]
    keys = list(param_grid.keys())
    values = [list(param_grid[k]) for k in keys]
    return [dict(zip(keys, combo)) for combo in itertools.product(*values)]


def sweep_configs(
    games_by_year: Dict[int, List[Dict[str, Any]]],
    param_grid: Dict[str, Sequence[Any]],
    *,
    priors_by_year: Optional[Dict[int, Dict[str, float]]] = None,
    base_config: Optional[Dict[str, Any]] = None,
    metric: str = 'brier',
    lower_is_better: bool = True,
) -> List[Dict[str, Any]]:
    """Evaluate every config on all provided seasons; rank by pooled metric.

    Returns a list of {config, pooled_metric, pooled, per_season} sorted best-first.
    """
    priors_by_year = priors_by_year or {}
    base = dict(base_config or {})
    results_rows: List[Dict[str, Any]] = []

    for overrides in expand_grid(param_grid):
        cfg = {**base, **overrides}
        season_results: List[BacktestResult] = []
        for year, games in sorted(games_by_year.items()):
            season_results.append(
                backtest_season(
                    games,
                    year,
                    config=cfg,
                    priors=priors_by_year.get(year),
                )
            )
        pooled = aggregate_results(season_results)
        score = pooled['pooled'][metric]
        results_rows.append({
            'config': overrides,
            'full_config': cfg,
            'metric': metric,
            'score': score,
            'pooled': pooled['pooled'],
            'per_season': pooled['per_season'],
        })

    results_rows.sort(key=lambda r: r['score'], reverse=not lower_is_better)
    return results_rows


def suggest_default_grid() -> Dict[str, List[Any]]:
    """Small Elo-focused grid around V5.1 defaults (prediction uses team_quality Elo).

    FRS blend weights matter for published rankings but not for Elo win probs;
    tune those in a separate ranking-order experiment after Elo is calibrated.
    """
    return {
        'base_factor': [30.0, 40.0, 50.0],
        'hfa_elo': [50.0, 65.0, 80.0],
        'upset_bonus_mult': [1.0, 1.18],
    }
