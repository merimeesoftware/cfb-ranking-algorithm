#!/usr/bin/env python3
"""
Precompute rankings for archived weeks and write static JSON.

Usage:
  ./venv/bin/python scripts/precompute_rankings.py --year 2024 --week 10
  ./venv/bin/python scripts/precompute_rankings.py --year 2024 --through-week 15
  ./venv/bin/python scripts/precompute_rankings.py --current   # current season, weeks 1..current-1

Also copies slim JSON into frontend/static/rankings/ for Cloudflare Pages static serving.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / '.env')

from data_processor import CFBDataProcessor
from ranking_service import (
    get_or_calculate_rankings,
    slim_rankings_for_list,
    is_archived_week,
)
from static_rankings import write_static_rankings, DEFAULT_ROOT


def current_season_week(now: datetime | None = None) -> tuple[int, int]:
    now = now or datetime.now()
    if now.month < 8:
        return now.year - 1, 15
    season_start = datetime(now.year, 8, 24)
    if now < season_start:
        return now.year, 1
    week = int((now - season_start).days / 7) + 1
    return now.year, min(week, 16)


def copy_to_frontend(year: int, week: int, source: Path) -> Path | None:
    dest_root = ROOT / 'frontend' / 'static' / 'rankings'
    dest = dest_root / str(year) / f'week-{week}.json'
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    return dest


def precompute(year: int, week: int, processor: CFBDataProcessor) -> Path:
    class Args(dict):
        def get(self, key, default=None):
            return dict.get(self, key, default)

    data = get_or_calculate_rankings(
        processor, year, week, Args(), prefer_static=False
    )
    if not data:
        raise RuntimeError(f'No rankings data for {year} week {week}')
    slim = slim_rankings_for_list(data)
    path = write_static_rankings(slim, year, week)
    fe = copy_to_frontend(year, week, path)
    print(f'Wrote {path}' + (f' and {fe}' if fe else ''))
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description='Precompute static rankings JSON')
    parser.add_argument('--year', type=int)
    parser.add_argument('--week', type=int)
    parser.add_argument('--through-week', type=int, help='Precompute weeks 1..N')
    parser.add_argument('--current', action='store_true', help='Archive weeks for current season')
    args = parser.parse_args()

    if not os.getenv('CFBD_API_KEY'):
        print('CFBD_API_KEY required', file=sys.stderr)
        return 1

    processor = CFBDataProcessor(api_key=os.getenv('CFBD_API_KEY'))
    jobs: list[tuple[int, int]] = []

    if args.current:
        year, cur = current_season_week()
        for w in range(1, cur):
            jobs.append((year, w))
    elif args.year and args.through_week:
        for w in range(1, args.through_week + 1):
            jobs.append((args.year, w))
    elif args.year and args.week:
        jobs.append((args.year, args.week))
    else:
        parser.error('Provide --year/--week, --year/--through-week, or --current')

    for year, week in jobs:
        print(f'Precomputing {year} week {week}...')
        precompute(year, week, processor)

    print(f'Done. Static root: {DEFAULT_ROOT}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
