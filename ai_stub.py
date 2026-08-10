"""Deterministic template explanations (AI_MODE=stub) — no LLM I/O."""
from __future__ import annotations

from typing import Any, Dict, Optional

from ranking_service import FRS_WEIGHTS


def stub_explain_from_context(context: Dict[str, Any], question: Optional[str] = None) -> str:
    """Build a grounded template explanation from ranking context fields."""
    name = context.get('team_name', 'This team')
    rank = context.get('rank')
    conf = context.get('conference', 'their conference')
    final = context.get('final_ranking_score')
    tq = context.get('team_quality_score')
    rec = context.get('record_score')
    cq = context.get('conference_quality_score')
    records = context.get('records') or {}
    wins = records.get('total_wins')
    losses = records.get('total_losses')

    parts = []
    if rank is not None:
        parts.append(f'{name} is ranked #{rank} in {conf}.')
    else:
        parts.append(f'{name} ranking context:')

    score_bits = []
    if final is not None:
        score_bits.append(f'final score {final:.1f}' if isinstance(final, (int, float)) else f'final score {final}')
    if tq is not None:
        score_bits.append(f'Team Quality (Elo) {tq:.0f}' if isinstance(tq, (int, float)) else f'Team Quality {tq}')
    if rec is not None:
        score_bits.append(f'Resume {rec:.0f}' if isinstance(rec, (int, float)) else f'Resume {rec}')
    if cq is not None:
        score_bits.append(f'Conference Quality {cq:.0f}' if isinstance(cq, (int, float)) else f'CQ {cq}')
    if score_bits:
        pct = tuple(int(round(w * 100)) for w in FRS_WEIGHTS)
        parts.append(
            f'Formula mix ({pct[0]}% TQ / {pct[1]}% Resume / {pct[2]}% CQ): '
            + '; '.join(score_bits) + '.'
        )
    if wins is not None and losses is not None:
        parts.append(f'Record: {wins}-{losses}.')

    path = context.get('path_to_climb')
    if isinstance(path, dict):
        if path.get('at_top'):
            parts.append('They are currently #1 — no team above to chase.')
        elif path.get('summary'):
            parts.append(str(path['summary']))

    qw = context.get('quality_wins')
    if qw:
        parts.append(f'Quality wins logged: {qw}.')

    top_wins = context.get('top_quality_wins') or []
    if top_wins:
        parts.append('Notable quality wins vs: ' + ', '.join(top_wins) + '.')

    ahead = context.get('neighbor_ahead')
    behind = context.get('neighbor_behind')
    if ahead:
        parts.append(f'Immediately ahead: {ahead}.')
    if behind:
        parts.append(f'Immediately behind: {behind}.')

    if question:
        parts.append(f'(Responding to: {question})')

    parts.append('This is a stub explanation (AI_MODE=stub); no MiniMax call was made.')
    return ' '.join(parts)
