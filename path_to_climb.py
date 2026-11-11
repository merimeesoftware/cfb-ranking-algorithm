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


def _gap_words(gap: float) -> str:
    """Fan phrase for a TR+ gap. Under 1 is not rounded up to 1."""
    size = abs(gap)
    if size < 1:
        return 'less than a point'
    whole = int(round(size))
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
    if score_gap > 0.5:
        primary = 'Elo'
        summary = (
            f'{team_name} trails {above_name} by {_gap_words(score_gap)} on TR+. '
            f'Beating better teams closes the gap.'
        )
    elif score_gap < -0.5:
        primary = 'Elo'
        summary = f'{team_name} is ahead of {above_name} on TR+.'
    else:
        primary = None
        summary = f'{team_name} matches {above_name} on TR+.'

    return {
        'at_top': False,
        'team_above': above_name,
        'score_gap': round(score_gap, 2),
        'gaps': {k: round(v, 2) for k, v in gaps.items()},
        'primary_lever': primary,
        'summary': summary,
    }
