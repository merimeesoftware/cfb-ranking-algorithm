#!/usr/bin/env python3
"""
Precompute week story + Why blurbs from static rankings JSON (offline-safe).

Usage:
  CFBD_OFFLINE=1 ./venv/bin/python scripts/precompute_narratives.py --year 2024 --week 10
  CFBD_OFFLINE=1 ./venv/bin/python scripts/precompute_narratives.py --year 2024 --through-week 10
  CFBD_OFFLINE=1 ./venv/bin/python scripts/precompute_narratives.py --year 2024 --week 10 --mode stub

Writes week-{n}.story.json and week-{n}.why.json under:
  - frontend/static/rankings/{year}/
  - static_rankings/{year}/

--mode live only calls MiniMax when AI_MODE=live and MINIMAX_API_KEY is set;
otherwise falls back to stub templates.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / '.env')

from narrative_facts import extract_week_facts, stub_week_story, stub_why_blurbs  # noqa: E402
from spend_guards import resolve_ai_mode  # noqa: E402
from static_rankings import (  # noqa: E402
    DEFAULT_ROOT,
    read_static_rankings,
    write_week_story,
    write_why_blurbs,
)

FRONTEND_ROOT = ROOT / 'frontend' / 'static' / 'rankings'


def _load_week(year: int, week: int) -> Optional[Dict[str, Any]]:
    """Prefer frontend static copy, then static_rankings/."""
    data = read_static_rankings(year, week, root=FRONTEND_ROOT)
    if data is not None:
        return data
    return read_static_rankings(year, week, root=DEFAULT_ROOT)


def _write_both(
    story: Dict[str, Any],
    why: Dict[str, Any],
    year: int,
    week: int,
) -> List[Path]:
    paths: List[Path] = []
    for root in (FRONTEND_ROOT, Path(DEFAULT_ROOT)):
        paths.append(write_week_story(story, year, week, root=root))
        paths.append(write_why_blurbs(why, year, week, root=root))
    return paths


def _live_story_or_stub(facts: Dict[str, Any]) -> Dict[str, Any]:
    """Attempt MiniMax only when explicitly live + keyed; else stub."""
    mode = resolve_ai_mode()
    key = os.environ.get('MINIMAX_API_KEY', '').strip()
    if mode != 'live' or not key:
        if mode == 'live' and not key:
            print(
                'AI_MODE=live but MINIMAX_API_KEY unset — using stub story.',
                file=sys.stderr,
            )
        return stub_week_story(facts)

    try:
        from agent_service import _call_minimax  # type: ignore

        prompt = (
            'Write a short college football week-story JSON with keys '
            '"headline" (string) and "paragraphs" (array of 2-4 short strings). '
            'Use ONLY these facts; do not invent games:\n'
            + json.dumps(facts, separators=(',', ':'))
        )
        raw = _call_minimax(prompt)
        data = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(data, dict) and data.get('headline'):
            return {
                'headline': data['headline'],
                'paragraphs': data.get('paragraphs') or [],
                'facts': facts,
            }
    except Exception as exc:  # noqa: BLE001 — batch script falls back
        print(f'Live narrative failed ({exc}); falling back to stub.', file=sys.stderr)

    return stub_week_story(facts)


def precompute_week(year: int, week: int, mode: str) -> None:
    current = _load_week(year, week)
    if current is None:
        raise FileNotFoundError(
            f'No static rankings for {year} week {week} under '
            f'{FRONTEND_ROOT} or {DEFAULT_ROOT}'
        )
    # Ensure meta fields present for facts snapshot
    current.setdefault('year', year)
    current.setdefault('week', week)

    previous = None
    if week > 1:
        previous = _load_week(year, week - 1)
        if previous is not None:
            previous.setdefault('year', year)
            previous.setdefault('week', week - 1)

    facts = extract_week_facts(current, previous)
    if mode == 'live':
        story = _live_story_or_stub(facts)
    else:
        story = stub_week_story(facts)
    why = stub_why_blurbs(current, top_n=25)

    paths = _write_both(story, why, year, week)
    wow = 'with WoW' if facts['snapshot']['has_wow'] else 'snapshot-only'
    print(f'{year} week {week} ({wow}, mode={mode}):')
    for p in paths:
        print(f'  wrote {p}')


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Precompute static week story + Why blurbs from rankings JSON'
    )
    parser.add_argument('--year', type=int, required=True)
    parser.add_argument('--week', type=int)
    parser.add_argument(
        '--through-week',
        type=int,
        help='Precompute narratives for weeks 1..N',
    )
    parser.add_argument(
        '--mode',
        choices=('stub', 'live'),
        default='stub',
        help='stub (default, free) or live (MiniMax only if AI_MODE=live + key)',
    )
    args = parser.parse_args()

    if os.environ.get('CFBD_OFFLINE', '').strip() in ('1', 'true', 'yes', 'on'):
        print('CFBD_OFFLINE=1 — reading static files only (no CFBD).')

    jobs: List[int] = []
    if args.through_week is not None:
        jobs = list(range(1, args.through_week + 1))
    elif args.week is not None:
        jobs = [args.week]
    else:
        parser.error('Provide --week or --through-week')

    for week in jobs:
        precompute_week(args.year, week, args.mode)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
