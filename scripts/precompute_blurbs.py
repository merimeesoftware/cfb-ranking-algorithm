#!/usr/bin/env python3
"""
Precompute shareable + climb blurbs (stub/static by default).

GitHub Actions always runs AI_MODE=stub — no MiniMax key in CI.
Live MiniMax-M3 + web_search is Cloudflare-only (AI_MODE=live on cache miss).

Cadence (by design):
  - In-season current week: run daily; period = YYYY-MM-DD; skip teams already
    present for that period.
  - Lookbacks / archived weeks: quarterly or workflow_dispatch; period =
    lookback-YYYY-Qn; skip any team already in the file unless --force.

Usage:
  CFBD_OFFLINE=1 AI_MODE=stub ./venv/bin/python scripts/precompute_blurbs.py \\
    --year 2024 --week 10 --top-n 25
  CFBD_OFFLINE=1 AI_MODE=stub ./venv/bin/python scripts/precompute_blurbs.py \\
    --year 2024 --week 10 --lookback --top-n 25

Writes week-{n}.share.json and week-{n}.climb.json under:
  - frontend/static/rankings/{year}/
  - static_rankings/{year}/
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / '.env')

from agent_service import (  # noqa: E402
    MINIMAX_BLURB_MODEL,
    _build_team_context,
    _resolve_blurb,
)
from shareable_blurb import (  # noqa: E402
    blurb_cache_period,
    is_in_season,
    lookback_cache_period,
    minimax_web_search_enabled,
)
from spend_guards import resolve_ai_mode  # noqa: E402
from static_rankings import (  # noqa: E402
    DEFAULT_ROOT,
    read_climb_blurbs,
    read_share_blurbs,
    read_static_rankings,
    write_climb_blurbs,
    write_share_blurbs,
)

FRONTEND_ROOT = ROOT / 'frontend' / 'static' / 'rankings'


def _load_week(year: int, week: int) -> Optional[Dict[str, Any]]:
    data = read_static_rankings(year, week, root=FRONTEND_ROOT)
    if data is not None:
        return data
    return read_static_rankings(year, week, root=DEFAULT_ROOT)


def _read_kind(kind: str, year: int, week: int) -> Dict[str, Any]:
    reader = read_share_blurbs if kind == 'share' else read_climb_blurbs
    for root in (FRONTEND_ROOT, Path(DEFAULT_ROOT)):
        payload = reader(year, week, root=root)
        if payload:
            return dict(payload)
    return {}


def _write_kind(kind: str, payload: Dict[str, Any], year: int, week: int) -> List[Path]:
    writer = write_share_blurbs if kind == 'share' else write_climb_blurbs
    paths: List[Path] = []
    for root in (FRONTEND_ROOT, Path(DEFAULT_ROOT)):
        paths.append(writer(payload, year, week, root=root))
    return paths


def _team_names(rankings: Dict[str, Any], top_n: int) -> List[str]:
    teams = rankings.get('team_rankings') or []
    names: List[str] = []
    for team in teams[:top_n]:
        name = team.get('team_name')
        if name:
            names.append(str(name))
    return names


def precompute_kind(
    *,
    kind: str,
    year: int,
    week: int,
    top_n: int,
    period: str,
    force: bool,
    lookback: bool,
) -> Tuple[int, int]:
    """Return (generated, skipped) counts."""
    rankings = _load_week(year, week)
    if rankings is None:
        raise FileNotFoundError(
            f'No static rankings for {year} week {week} under '
            f'{FRONTEND_ROOT} or {DEFAULT_ROOT}'
        )
    rankings.setdefault('year', year)
    rankings.setdefault('week', week)

    existing = _read_kind(kind, year, week)
    blurbs: Dict[str, str] = dict(existing.get('blurbs') or {})
    existing_period = existing.get('period')

    # Daily: different period → start fresh map (keep only if same period)
    if not lookback and existing_period and existing_period != period and not force:
        blurbs = {}

    generated = 0
    skipped = 0
    for name in _team_names(rankings, top_n):
        already = bool(blurbs.get(name))
        if already and not force:
            skipped += 1
            continue

        context = _build_team_context(rankings, name)
        if not context:
            print(f'  skip {name}: not in rankings', file=sys.stderr)
            skipped += 1
            continue

        text, mode = _resolve_blurb(context, kind=kind)
        blurbs[name] = text
        generated += 1
        print(f'  {kind} {name}: mode={mode} chars={len(text)}')

    payload = {
        'year': year,
        'week': week,
        'kind': kind,
        'period': period,
        'top_n': top_n,
        'model': MINIMAX_BLURB_MODEL if resolve_ai_mode() == 'live' else 'stub',
        'web_search': minimax_web_search_enabled() if resolve_ai_mode() == 'live' else False,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'blurbs': blurbs,
    }
    for path in _write_kind(kind, payload, year, week):
        print(f'  wrote {path}')
    return generated, skipped


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description='Precompute share/climb blurbs')
    parser.add_argument('--year', type=int, required=True)
    parser.add_argument('--week', type=int, required=True)
    parser.add_argument('--top-n', type=int, default=25)
    parser.add_argument(
        '--kind',
        choices=('share', 'climb', 'both'),
        default='both',
    )
    parser.add_argument(
        '--lookback',
        action='store_true',
        help='Use quarterly lookback period; skip existing teams unless --force',
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Regenerate even when period artifact already has the team',
    )
    parser.add_argument(
        '--require-in-season',
        action='store_true',
        help='Exit 0 without work when outside CFB season (for daily cron)',
    )
    args = parser.parse_args(argv)

    if args.require_in_season and not is_in_season():
        print('Outside CFB season — skipping daily blurb precompute.')
        return 0

    if os.environ.get('CFBD_OFFLINE', '').strip() in ('1', 'true', 'yes', 'on'):
        print('CFBD_OFFLINE=1 — reading static rankings only.')

    period = lookback_cache_period() if args.lookback else blurb_cache_period()
    kinds = ['share', 'climb'] if args.kind == 'both' else [args.kind]
    mode = resolve_ai_mode()
    print(
        f'Precompute blurbs year={args.year} week={args.week} period={period} '
        f'mode={mode} web_search={minimax_web_search_enabled()} '
        f'lookback={args.lookback} force={args.force}'
    )

    total_gen = 0
    total_skip = 0
    for kind in kinds:
        gen, skip = precompute_kind(
            kind=kind,
            year=args.year,
            week=args.week,
            top_n=args.top_n,
            period=period,
            force=args.force,
            lookback=args.lookback,
        )
        total_gen += gen
        total_skip += skip

    print(f'Done: generated={total_gen} skipped={total_skip}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
