"""Pure path-to-climb insights from ranking scores (no I/O)."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Optional, Tuple

from ranking_service import FRS_WEIGHTS

WEIGHTS = FRS_WEIGHTS  # TQ, Resume, CQ


def board_rating(score: float) -> float:
    """One decimal, half away from zero, matching the board's toFixed(1)."""
    return float(Decimal(str(float(score))).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))


def _shown_raw(team: Dict[str, Any]) -> float:
    """The rating the board prints: ordering_score, else team quality."""
    raw = team.get('ordering_score')
    if raw is None:
        raw = team.get('team_quality_score')
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.0
    if value != value:
        return 0.0
    return value

def _contrib(team: Dict[str, Any], weights: Tuple[float, float, float] = WEIGHTS) -> Dict[str, float]:
    w_tq, w_rec, w_cq = weights
    return {
        'tq': float(team.get('team_quality_score') or 0) * w_tq,
        'resume': float(team.get('record_score') or 0) * w_rec,
        'cq': float(team.get('conference_quality_score') or 0) * w_cq,
        'final': float(team.get('final_ranking_score') or 0),
    }


def _gap_words(gap: float) -> str:
    """Fan phrase for a TR+ gap. A gap that rounds below 1 is not 1 point."""
    whole = int(Decimal(str(abs(float(gap)))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    if whole < 1:
        return 'less than a point'
    if whole == 1:
        return '1 point'
    return f'{whole} points'


def compute_path_to_climb(
    team: Dict[str, Any],
    team_above: Optional[Dict[str, Any]],
    weights: Tuple[float, float, float] = WEIGHTS,
) -> Dict[str, Any]:
    """
    Compare team to the team ranked immediately above.

    Returns structured gaps and a human-readable summary. No network/LLM.
    """
    if team_above is None:
        return {
            'at_top': True,
            'team_above': None,
            'score_gap': 0.0,
            'gaps': {'tq': 0.0, 'resume': 0.0, 'cq': 0.0},
            'primary_lever': None,
            'summary': f"{team.get('team_name', 'This team')} is currently #1 — no team above to chase.",
        }

    mine = _contrib(team, weights)
    theirs = _contrib(team_above, weights)
    gaps = {
        'tq': theirs['tq'] - mine['tq'],
        'resume': theirs['resume'] - mine['resume'],
        'cq': theirs['cq'] - mine['cq'],
    }
    # The board is ordered by Elo. Resume and conference gaps are display only.
    score_gap = float(team_above.get('team_quality_score') or 0) - float(team.get('team_quality_score') or 0)
    above_name = team_above.get('team_name', 'the team above')
    team_name = team.get('team_name', 'This team')
    mine_shown = board_rating(_shown_raw(team))
    above_shown = board_rating(_shown_raw(team_above))
    if mine_shown == above_shown:
        primary = None
        summary = f'{team_name} matches {above_name} on TR+.'
    elif above_shown > mine_shown:
        primary = 'Elo'
        summary = (
            f'{team_name} trails {above_name} by {_gap_words(above_shown - mine_shown)} on TR+. '
            f'Beating better teams closes the gap.'
        )
    else:
        primary = 'Elo'
        summary = f'{team_name} is ahead of {above_name} on TR+.'

    return {
        'at_top': False,
        'team_above': above_name,
        'score_gap': round(score_gap, 2),
        'shown_rating': _shown_raw(team),
        'shown_rating_above': _shown_raw(team_above),
        'gaps': {k: round(v, 2) for k, v in gaps.items()},
        'primary_lever': primary,
        'summary': summary,
    }
