"""Week-by-week predictive backtest protocol (no future leakage).

Protocol
--------
For each season year Y and week W from 0 .. max_week-1:
  1. Build ratings using ONLY games with week <= W (W=0 → preseason / priors).
  2. Predict every completed game in week W+1 via Elo + HFA → P(home).
  3. Score predictions with Brier, log-loss, accuracy.

Priors from Y-1 / Y-2 are allowed (known before kickoff of Y). Never use week W+1
results when forming week-W ratings.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from algo_lab.baselines import (
    baseline_always_home,
    baseline_coin_flip,
    baseline_equal_elo_hfa,
)
from algo_lab.metrics import MetricsSummary, compare_to_baseline, score_predictions
from algo_lab.predict import predict_game
from algo_lab.runner import (
    games_in_week,
    preseason_ratings,
    rank_through_week,
    ratings_from_rankings,
)


@dataclass
class BacktestResult:
    year: int
    rating_field: str
    n_predict_weeks: int
    model: MetricsSummary
    baselines: Dict[str, MetricsSummary] = field(default_factory=dict)
    lifts: Dict[str, Dict[str, float]] = field(default_factory=dict)
    predictions: List[Dict[str, Any]] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self, *, include_predictions: bool = False) -> Dict[str, Any]:
        data = {
            'year': self.year,
            'rating_field': self.rating_field,
            'n_predict_weeks': self.n_predict_weeks,
            'model': self.model.to_dict(),
            'baselines': {k: v.to_dict() for k, v in self.baselines.items()},
            'lifts': self.lifts,
            'config': self.config,
        }
        if include_predictions:
            data['predictions'] = self.predictions
        return data


def _team_meta_from_games(games: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    meta: Dict[str, Dict[str, Any]] = {}
    for g in games:
        for side, conf_key, type_key in (
            ('home_team_name', 'home_conference', 'home_conference_type'),
            ('away_team_name', 'away_conference', 'away_conference_type'),
        ):
            name = g[side]
            if name not in meta:
                meta[name] = {
                    'conference': g.get(conf_key),
                    'conference_type': g.get(type_key, 'FCS'),
                }
    return meta


def backtest_season(
    games: List[Dict[str, Any]],
    year: int,
    *,
    config: Optional[Dict[str, Any]] = None,
    priors: Optional[Dict[str, float]] = None,
    rating_field: str = 'team_quality_score',
    min_week: int = 1,
    max_week: Optional[int] = None,
    include_preseason: bool = True,
) -> BacktestResult:
    """Run the leak-free week-by-week backtest for one season's game list.

    Parameters
    ----------
    games : full-season completed games (all weeks).
    min_week : first *outcome* week to score (default 1).
    max_week : last outcome week to score (default = max week in games).
    include_preseason : if True and min_week==1, week-1 games use preseason ratings.
    rating_field : usually team_quality_score (Elo). final_ranking_score is also
                   supported for ranking-order experiments but is not a calibrated Elo.
    """
    if not games:
        empty = MetricsSummary()
        return BacktestResult(
            year=year,
            rating_field=rating_field,
            n_predict_weeks=0,
            model=empty,
            config=config or {},
        )

    weeks = sorted({int(g['week']) for g in games})
    last_week = max_week if max_week is not None else weeks[-1]
    outcome_weeks = [w for w in weeks if min_week <= w <= last_week]

    predictions: List[Dict[str, Any]] = []
    ratings_cache: Dict[int, Dict[str, float]] = {}
    team_meta = _team_meta_from_games(games)
    cfg = config or {}

    for outcome_week in outcome_weeks:
        rating_week = outcome_week - 1  # ratings as of end of prior week
        if rating_week in ratings_cache:
            ratings = ratings_cache[rating_week]
        elif rating_week < 1:
            if not include_preseason:
                continue
            ratings = preseason_ratings(config=cfg, priors=priors, team_meta=team_meta)
            # If rating_field is FRS, preseason has no resume — fall back to Elo scale
            if rating_field != 'team_quality_score':
                # Still use Elo preseason; FRS only exists after games
                pass
            ratings_cache[0] = ratings
        else:
            rankings, _ = rank_through_week(
                games,
                rating_week,
                config=cfg,
                priors=priors,
            )
            ratings = ratings_from_rankings(rankings, field=rating_field)
            ratings_cache[rating_week] = ratings

        for game in games_in_week(games, outcome_week):
            pred = predict_game(game, ratings)
            if pred is not None:
                pred['rating_week'] = max(rating_week, 0)
                pred['rating_field'] = rating_field
                predictions.append(pred)

    model_metrics = score_predictions(predictions)

    # Baselines scored on the same game set (preserve real scores for margins)
    pred_keys = {(p['week'], p['home_team'], p['away_team']) for p in predictions}
    baseline_games = [
        g for g in games
        if (g.get('week'), g['home_team_name'], g['away_team_name']) in pred_keys
    ]

    baselines = {
        'coin_flip': score_predictions(baseline_coin_flip(baseline_games)),
        'always_home': score_predictions(baseline_always_home(baseline_games)),
        'equal_elo_hfa': score_predictions(baseline_equal_elo_hfa(baseline_games)),
    }
    lifts = {name: compare_to_baseline(model_metrics, base) for name, base in baselines.items()}

    return BacktestResult(
        year=year,
        rating_field=rating_field,
        n_predict_weeks=len(outcome_weeks),
        model=model_metrics,
        baselines=baselines,
        lifts=lifts,
        predictions=predictions,
        config=cfg,
    )


def aggregate_results(results: Sequence[BacktestResult]) -> Dict[str, Any]:
    """Pool predictions across seasons and re-score (micro-average)."""
    all_preds: List[Dict[str, Any]] = []
    for r in results:
        all_preds.extend(r.predictions)
    pooled = score_predictions(all_preds)
    return {
        'seasons': [r.year for r in results],
        'pooled': pooled.to_dict(),
        'per_season': [
            {
                'year': r.year,
                'n_games': r.model.n_games,
                'accuracy': r.model.accuracy,
                'brier': r.model.brier,
                'log_loss': r.model.log_loss,
                'lifts_vs_home': r.lifts.get('always_home', {}),
            }
            for r in results
        ],
    }
