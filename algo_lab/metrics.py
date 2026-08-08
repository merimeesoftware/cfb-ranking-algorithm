"""Proper scoring rules and summary stats for game predictions."""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List


EPS = 1e-15


@dataclass
class MetricsSummary:
    n_games: int = 0
    accuracy: float = 0.0
    brier: float = 0.0
    log_loss: float = 0.0
    mean_p_home: float = 0.0
    home_win_rate: float = 0.0
    upset_rate: float = 0.0
    # Calibration: mean predicted P among games where favorite was picked, vs win rate
    favorite_confidence: float = 0.0
    by_week: Dict[int, Dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _clip(p: float) -> float:
    return min(max(p, EPS), 1.0 - EPS)


def score_predictions(predictions: Iterable[Dict[str, Any]]) -> MetricsSummary:
    """Score a list of predict_game() records with proper scoring rules.

    - accuracy: fraction where P(favorite) >= 0.5 matches outcome
    - brier: mean((p_home - y)^2) — lower is better; 0.25 ≈ coin flip
    - log_loss: mean NLL — lower is better; ln(2)≈0.693 ≈ coin flip
    """
    preds = list(predictions)
    if not preds:
        return MetricsSummary()

    n = len(preds)
    correct = 0
    brier_sum = 0.0
    ll_sum = 0.0
    p_sum = 0.0
    home_wins = 0
    upsets = 0
    fav_conf_sum = 0.0

    by_week_acc: Dict[int, List[float]] = {}
    by_week_brier: Dict[int, List[float]] = {}

    for pred in preds:
        p = float(pred['p_home'])
        y = 1.0 if pred['home_won'] else 0.0
        p_c = _clip(p)

        if pred.get('correct'):
            correct += 1
        if pred.get('underdog_won'):
            upsets += 1
        if pred['home_won']:
            home_wins += 1

        brier = (p - y) ** 2
        ll = -(y * math.log(p_c) + (1.0 - y) * math.log(1.0 - p_c))
        brier_sum += brier
        ll_sum += ll
        p_sum += p
        fav_conf_sum += max(p, 1.0 - p)

        week = pred.get('week')
        if week is not None:
            by_week_acc.setdefault(week, []).append(1.0 if pred.get('correct') else 0.0)
            by_week_brier.setdefault(week, []).append(brier)

    by_week: Dict[int, Dict[str, float]] = {}
    for week, accs in by_week_acc.items():
        briars = by_week_brier[week]
        by_week[int(week)] = {
            'n': float(len(accs)),
            'accuracy': sum(accs) / len(accs),
            'brier': sum(briars) / len(briars),
        }

    return MetricsSummary(
        n_games=n,
        accuracy=correct / n,
        brier=brier_sum / n,
        log_loss=ll_sum / n,
        mean_p_home=p_sum / n,
        home_win_rate=home_wins / n,
        upset_rate=upsets / n,
        favorite_confidence=fav_conf_sum / n,
        by_week=by_week,
    )


def compare_to_baseline(model: MetricsSummary, baseline: MetricsSummary) -> Dict[str, float]:
    """Positive deltas mean the model beat the baseline (lower brier/log_loss, higher accuracy)."""
    return {
        'accuracy_lift': model.accuracy - baseline.accuracy,
        'brier_improvement': baseline.brier - model.brier,
        'log_loss_improvement': baseline.log_loss - model.log_loss,
    }
