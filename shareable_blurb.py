"""Shareable team ranking blurbs (≤280 chars) with season-aware cache periods."""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional

BLURB_MAX_CHARS = 280


def is_in_season(when: Optional[date] = None) -> bool:
    """
    Rough CFB calendar: tip-off ~ Aug 24 through end of January (bowls/CFP).
    Outside that window we refresh blurbs monthly instead of daily.
    """
    d = when or date.today()
    if d.month == 8 and d.day >= 24:
        return True
    if d.month in (9, 10, 11, 12):
        return True
    if d.month == 1:
        return True
    return False


def blurb_cache_period(when: Optional[date] = None) -> str:
    """Cache bucket: YYYY-MM-DD in season, YYYY-MM offseason."""
    d = when or date.today()
    if is_in_season(d):
        return d.isoformat()
    return f'{d.year:04d}-{d.month:02d}'


def lookback_cache_period(when: Optional[date] = None) -> str:
    """
    Stable quarterly key for archived lookbacks (rare regenerate).

    Example: lookback-2026-Q3. Precompute skips teams already present unless --force.
    """
    d = when or date.today()
    quarter = (d.month - 1) // 3 + 1
    return f'lookback-{d.year:04d}-Q{quarter}'


def minimax_web_search_enabled() -> bool:
    """True when MINIMAX_WEB_SEARCH is unset/truthy (env flag only; ignores AI_MODE)."""
    import os
    raw = os.environ.get('MINIMAX_WEB_SEARCH', '1').strip().lower()
    return raw not in ('0', 'false', 'no', 'off')


def search_prompt_rules(*, web_search: Optional[bool] = None) -> str:
    """Prompt addendum: allow web_search only when the tool will actually be attached."""
    enabled = minimax_web_search_enabled() if web_search is None else web_search
    if enabled:
        return (
            'You may use web_search for brief street/media consensus about this team.\n'
            'Rankings JSON is ground truth for scores, records, and games — never invent those.\n'
            'If search results conflict with the ranking facts, the ranking facts win.\n'
            'At most one short clause of social/media color; do not invent buzz without search hits.\n'
        )
    return (
        'Do not invent street/media buzz. Use ONLY the ranking JSON for facts '
        '(scores, records, games).\n'
    )


def truncate_blurb(text: str, limit: int = BLURB_MAX_CHARS) -> str:
    """
    Legacy helper for tests / defensive stub authoring only.

    Live AI blurbs must NEVER use this — over-length model output is rejected
    and retried (see accept_blurb / _resolve_blurb).
    """
    text = ' '.join((text or '').split()).strip()
    if len(text) <= limit:
        return text

    window = text[:limit]
    best_end = -1
    for i, ch in enumerate(window):
        if ch not in '.!?':
            continue
        if i == len(window) - 1 or window[i + 1].isspace():
            best_end = i

    if best_end >= 40:
        return window[: best_end + 1].strip()

    cut = window.rstrip()
    if ' ' in cut:
        cut = cut.rsplit(' ', 1)[0]
    return cut.rstrip('.,;:')


def accept_blurb(text: str, limit: int = BLURB_MAX_CHARS) -> str:
    """Return text only if it already fits the hard cap; never chop."""
    text = ' '.join((text or '').split()).strip()
    if not text or len(text) > limit:
        return ''
    return text


def clean_blurb_candidate(raw: str) -> str:
    """Strip quotes/preamble from model output without length enforcement."""
    text = (raw or '').strip()
    if not text:
        return ''
    if text.startswith('LLM explanation unavailable') or text.startswith('MiniMax API'):
        return ''
    if text.startswith('{') and ("'content'" in text or '"content"' in text):
        return ''
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1].strip()
    if '\n' in text:
        text = text.split('\n')[0].strip()
    return ' '.join(text.split()).strip()


def stub_shareable_blurb(context: Dict[str, Any]) -> str:
    """
    Deterministic ≤280-char blurb: ranking why + a light debate hook.
    Used for AI_MODE=stub/off fallback and when MiniMax is unavailable.
    """
    name = str(context.get('team_name') or 'This team')
    rank = context.get('rank')
    conf = context.get('conference') or 'FBS'
    records = context.get('records') or {}
    wins = records.get('total_wins')
    losses = records.get('total_losses')
    qw = context.get('quality_wins')
    path = context.get('path_to_climb') or {}
    behind = context.get('neighbor_behind')
    ahead = context.get('neighbor_ahead')

    record_bit = ''
    if wins is not None and losses is not None:
        record_bit = f' ({wins}-{losses})'

    if rank == 1:
        why = f'{name} sits No. 1{record_bit} on the board — {conf} resume still clear the field.'
        hook = f' Prove {behind} can knock them off?' if behind else ' Who actually belongs above them?'
    elif path.get('at_top'):
        why = f'{name} is No. {rank}{record_bit} with nothing left to chase in the table.'
        hook = ' Is the board too locked in?'
    else:
        why = (
            f'{name} is No. {rank}{record_bit} ({conf}). '
            f'The board ranks them on who they beat and how they look — not the hype.'
        )
        if ahead:
            hook = f' Fair ranking — or is {ahead} getting too much respect?'
        elif behind:
            hook = f' Should {behind} already be ahead?'
        else:
            hook = ' Hot take: this spot is still up for debate.'

    if qw and isinstance(qw, int) and qw > 0 and 'quality' not in why.lower():
        why = why.rstrip('.') + f' ({qw} quality wins).'

    blurb = accept_blurb(f'{why.rstrip()} {hook.strip()}')
    if blurb:
        return blurb
    # Authoring guard: stubs must always fit — shorten deliberately, do not chop mid-thought
    return accept_blurb(
        f'{name} is No. {rank}{record_bit}. The board ranks the full resume, not the noise. '
        f'{"Prove " + behind + " belongs ahead?" if behind else "Fair ranking — or still up for debate?"}'
    ) or f'{name} is No. {rank}. Debate?'


def _plain_lever(path: Dict[str, Any]) -> str:
    """Map structured climb data to fan-language problem (StoryBrand)."""
    lever = str(path.get('primary_lever') or '').lower()
    gaps = path.get('gaps') or {}
    # Prefer structured gaps when present
    if gaps:
        key = max(gaps, key=lambda k: float(gaps.get(k) or 0))
        if float(gaps.get(key) or 0) > 0.5:
            return {
                'tq': 'how strong they look week to week',
                'resume': 'who they beat on the schedule',
                'cq': 'the company they keep in conference',
            }.get(key, 'the full body of work')
    if 'quality' in lever or 'elo' in lever or lever == 'tq':
        return 'how strong they look week to week'
    if 'resume' in lever or 'record' in lever or 'beat' in lever:
        return 'who they beat on the schedule'
    if 'conference' in lever or lever == 'cq':
        return 'the company they keep in conference'
    return 'the full body of work'


def stub_climb_blurb(context: Dict[str, Any]) -> str:
    """
    StoryBrand path-to-climb blurb: hero team, plain problem, one plan, debate CTA.
    No point dumps, deltas, or internal metric names.
    """
    name = str(context.get('team_name') or 'This team')
    path = context.get('path_to_climb') or {}
    ahead = path.get('team_above') or context.get('neighbor_ahead')
    behind = context.get('neighbor_behind')

    if path.get('at_top') or not ahead:
        hook = f' Can {behind} take the throne?' if behind else ' Who belongs up here next?'
        blurb = accept_blurb(
            f'{name} is already on top. The board is impartial — wins, strength, '
            f'and the whole resume decide it, not the noise.{hook}'
        )
        return blurb or accept_blurb(f'{name} is on top. Who takes the throne next?') or f'{name} is #1.'

    problem = _plain_lever(path)
    plan = {
        'who they beat on the schedule': 'Beat a real contender. Padding wins will not close this.',
        'how strong they look week to week': 'Stack wins against good teams and look dominant doing it.',
        'the company they keep in conference': 'Prove it against the best in their league.',
    }.get(problem, 'Keep winning the games that matter.')

    body = (
        f'{name} is chasing {ahead}. The gap is mostly {problem} — '
        f'the board weighs the whole resume, not the narrative. {plan}'
    )
    hook = f' Think {name} already deserves that spot?'
    blurb = accept_blurb(f'{body} {hook}')
    if blurb:
        return blurb
    return (
        accept_blurb(
            f'{name} is chasing {ahead}. Close it by beating better teams. '
            f'Think they already deserve that spot?'
        )
        or f'{name} vs {ahead}: who belongs higher?'
    )


def build_blurb_prompt(context: Dict[str, Any]) -> str:
    """Prompt for MiniMax: why + debate hook, hard 280-char cap."""
    return (
        'Write ONE shareable college football ranking blurb for X/Twitter.\n'
        f'HARD RULE: the entire blurb MUST be {BLURB_MAX_CHARS} characters or fewer. '
        'Count every character before you reply. If it would exceed the limit, rewrite shorter.\n'
        'Target 180–250 characters. Never return text longer than the hard rule.\n'
        'Requirements:\n'
        '- Explain WHY this team is ranked here using the JSON facts.\n'
        f'{search_prompt_rules()}'
        '- End with a short complete debate question (must finish with ?).\n'
        '- No hashtags, no emojis, no quotes around the whole blurb.\n'
        '- Plain prose only.\n'
        '- Reply with ONLY the blurb text — no preamble, no JSON, no character count.\n\n'
        f'Team context JSON: {context}\n'
    )


def build_climb_prompt(context: Dict[str, Any]) -> str:
    """StoryBrand path-to-climb prompt: caveman-simple, debate-first, ≤280."""
    return (
        'Write ONE path-to-climb blurb for college football fans (X/Twitter length).\n'
        f'HARD RULE: the entire blurb MUST be {BLURB_MAX_CHARS} characters or fewer. '
        'Count every character. If too long, rewrite shorter — do not trail off.\n'
        'Target 180–250 characters.\n'
        'Use Donald Miller StoryBrand simplicity: caveman-clear. Fan is the hero.\n'
        'Structure:\n'
        '1) Who they are chasing (team above).\n'
        '2) The gap in plain football language (who they beat / how they look / schedule).\n'
        '3) One clear thing that would move them up.\n'
        '4) End with a complete debate question (?).\n'
        'Voice: confident that an impartial model (wins + strength + full resume) beats hot takes.\n'
        f'{search_prompt_rules()}'
        'Do NOT use: TQ, CQ, Elo, delta, Δ, contrib, lever, point gaps, decimals, formulas.\n'
        'No hashtags, emojis, or quotes around the whole blurb.\n'
        'Reply with ONLY the blurb text.\n\n'
        f'Team context JSON: {context}\n'
    )


def build_blurb_rewrite_prompt(previous: str, context: Dict[str, Any], kind: str = 'share') -> str:
    """Ask the model to rewrite an over-length draft under the hard cap."""
    n = len(previous or '')
    kind_bit = 'path-to-climb' if kind == 'climb' else 'shareable ranking'
    return (
        f'The previous {kind_bit} blurb was {n} characters — TOO LONG.\n'
        f'HARD RULE: rewrite it in {BLURB_MAX_CHARS} characters or fewer (count carefully).\n'
        'Keep the same facts and a debate question at the end. Do not invent games.\n'
        'Reply with ONLY the rewritten blurb text.\n\n'
        f'Previous draft:\n{previous}\n\n'
        f'Team context JSON: {context}\n'
    )


def extract_blurb_text(raw: str) -> str:
    """
    Normalize model output. Returns '' if missing/invalid/over 280.

    Never truncates — callers must retry or stub.
    """
    return accept_blurb(clean_blurb_candidate(raw))


def blurb_cache_key(
    team_name: str,
    year: int,
    week: Optional[int],
    period: Optional[str] = None,
    *,
    kind: str = 'share',
) -> str:
    period = period or blurb_cache_period()
    week_part = str(week) if week is not None else 'final'
    safe = team_name.strip().lower().replace(' ', '_')
    return f'{kind}_blurb:{year}:{week_part}:{safe}:{period}'
