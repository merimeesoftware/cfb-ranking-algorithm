"""Deterministic template explanations (AI_MODE=stub) — no LLM I/O."""
from __future__ import annotations

from typing import Any, Dict, Optional

def stub_explain_from_context(context: Dict[str, Any], question: Optional[str] = None) -> str:
    """Build a grounded fan-language explanation from ranking context fields."""
    name = context.get('team_name', 'This team')
    rank = context.get('rank')
    conf = context.get('conference', 'their conference')
    place = context.get('ordering_score')
    if place is None:
        place = context.get('team_quality_score')
    records = context.get('records') or {}
    wins = records.get('total_wins')
    losses = records.get('total_losses')

    parts = []
    if rank is not None:
        parts.append(f'{name} sits #{rank} on the board ({conf}).')
    else:
        parts.append(f'{name} on the board:')

    if isinstance(place, (int, float)):
        parts.append(f'The rating is TR+ {place:.1f}.')
    elif place is not None:
        parts.append(f'The rating is TR+ {place}.')
    if wins is not None and losses is not None:
        parts.append(f'Record: {wins}-{losses}.')

    path = context.get('path_to_climb')
    if isinstance(path, dict):
        if path.get('at_top'):
            parts.append('They own #1 — nobody above to chase.')
        elif path.get('summary'):
            parts.append(str(path['summary']))

    qw = context.get('quality_wins')
    if qw:
        parts.append(f'Quality wins on the ledger: {qw}.')

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

    return ' '.join(parts)
