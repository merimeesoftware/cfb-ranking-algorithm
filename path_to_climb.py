"""Pure path-to-climb insights from ranking scores (no I/O)."""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

WEIGHTS = (0.65, 0.27, 0.08)  # TQ, Resume, CQ


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
    score_gap = theirs['final'] - mine['final']

    # Largest positive gap (where we trail most in contribution space)
    lever_key = max(gaps, key=lambda k: gaps[k])
    lever_labels = {
        'tq': 'Team Quality (Elo)',
        'resume': 'Resume (record score)',
        'cq': 'Conference Quality',
    }
    primary = lever_labels[lever_key] if gaps[lever_key] > 0.5 else 'balanced margins'

    above_name = team_above.get('team_name', 'the team above')
    if score_gap <= 0:
        summary = (
            f"{team.get('team_name', 'This team')} already matches or exceeds "
            f"{above_name} on final score in this snapshot."
        )
    else:
        summary = (
            f"To pass {above_name}, close a final-score gap of {score_gap:.1f}. "
            f"Largest drag vs them: {primary} "
            f"(TQ contrib Δ {gaps['tq']:+.1f}, Resume Δ {gaps['resume']:+.1f}, CQ Δ {gaps['cq']:+.1f})."
        )
        if lever_key == 'resume' and gaps['resume'] > 1:
            summary += ' A quality win over a strong opponent is the usual resume lever.'
        elif lever_key == 'tq' and gaps['tq'] > 1:
            summary += ' Sustained Elo gains (winning vs quality) close the Team Quality gap.'

    return {
        'at_top': False,
        'team_above': above_name,
        'score_gap': round(score_gap, 2),
        'gaps': {k: round(v, 2) for k, v in gaps.items()},
        'primary_lever': primary,
        'summary': summary,
    }
