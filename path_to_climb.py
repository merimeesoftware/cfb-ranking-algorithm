"""Pure path-to-climb insights from ranking scores (no I/O)."""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from ranking_service import FRS_WEIGHTS

WEIGHTS = FRS_WEIGHTS  # TQ, Resume, CQ

def _contrib(team: Dict[str, Any], weights: Tuple[float, float, float] = WEIGHTS) -> Dict[str, float]:
    w_tq, w_rec, w_cq = weights
    return {
        'tq': float(team.get('team_quality_score') or 0) * w_tq,
        'resume': float(team.get('record_score') or 0) * w_rec,
        'cq': float(team.get('conference_quality_score') or 0) * w_cq,
        'final': float(team.get('final_ranking_score') or 0),
    }


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
    if score_gap > 0.5:
        primary = 'Elo'
        summary = (
            f'To catch {above_name}, {team_name} needs {score_gap:.0f} more Elo points. '
            f'The record is shown beside the order and does not move the place.'
        )
    elif score_gap < -0.5:
        primary = 'Elo'
        summary = (
            f'{team_name} is already ahead of {above_name} on Elo. '
            f'The record is shown beside the order and does not move the place.'
        )
    else:
        primary = None
        summary = (
            f'{team_name} matches {above_name} on Elo. '
            f'The record is shown beside the order and does not move the place.'
        )

    return {
        'at_top': False,
        'team_above': above_name,
        'score_gap': round(score_gap, 2),
        'gaps': {k: round(v, 2) for k, v in gaps.items()},
        'primary_lever': primary,
        'summary': summary,
    }
