#!/usr/bin/env python3
"""
Precompute rankings for archived weeks and write static JSON.

Usage:
  ./venv/bin/python scripts/precompute_rankings.py --year 2024 --week 10
  ./venv/bin/python scripts/precompute_rankings.py --year 2024 --through-week 15
  ./venv/bin/python scripts/precompute_rankings.py --current   # current season, weeks 1..current-1

Published weeks are not fetched again. The latest week is fetched and
recomputed only when its games changed. Earlier weeks are read from the
saved snapshot. Also copies slim JSON into frontend/static/rankings/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / '.env')

# Per Sunday run, not the public daily budget. Cache hits do not count.
# 24 covers one cold season (teams + weeks 1..15 + priors). A warm Sunday
# refetches only the latest week. See config/cfbd-month.json.
os.environ.setdefault('CFBD_MAX_CALLS', '24')

from cache import get_cache
from data_processor import CFBDataProcessor
from spend_guards import is_cfbd_killed
from ranking_service import (
    get_or_calculate_rankings,
    slim_rankings_for_list,
)
from static_rankings import read_static_rankings, write_static_rankings, DEFAULT_ROOT

# Restored by the weekly Actions cache. Longer than the public 1-hour TTL
# so a Sunday run still sees last Sunday's games, teams, and priors.
BATCH_TTL = 30 * 24 * 60 * 60


def install_batch_cache_ttl() -> None:
    """Keep cron snapshots warm across the week without changing public TTLs."""
    import api_integration
    import ranking_service

    api_integration.TTL_TEAMS = BATCH_TTL
    ranking_service.TTL_PRIORS = BATCH_TTL
    api_integration.get_games_ttl = lambda year: BATCH_TTL


def current_season_week(now: datetime | None = None) -> tuple[int, int]:
    now = now or datetime.now()
    if now.month < 8:
        return now.year - 1, 15
    season_start = datetime(now.year, 8, 24)
    if now < season_start:
        return now.year, 1
    week = int((now - season_start).days / 7) + 1
    return now.year, min(week, 16)


def games_fingerprint(games: list) -> str:
    payload = json.dumps(games, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(payload.encode()).hexdigest()


def source_path(year: int, week: int, root: Path | None = None) -> Path:
    base = Path(root) if root is not None else Path(DEFAULT_ROOT)
    return base / '_sources' / str(year) / f'week-{week}.json'


def read_source(year: int, week: int, root: Path | None = None) -> dict | None:
    path = source_path(year, week, root)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding='utf-8'))


def write_source(year: int, week: int, games: list, root: Path | None = None) -> None:
    path = source_path(year, week, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({'fingerprint': games_fingerprint(games), 'games': games}),
        encoding='utf-8',
    )


def seed_week_games(year: int, week: int, games: list) -> None:
    cache = get_cache()
    key = cache._generate_key('games', year, week, 'regular')
    cache.set(key, games, BATCH_TTL, prefix='games')


def weeks_to_fetch(weeks: list[int], published: set[int], snapshots: set[int]) -> list[int]:
    """Unpublished weeks, the latest week, and any earlier week with no snapshot."""
    if not weeks:
        return []
    latest = max(weeks)
    needed = {week for week in weeks if week not in published}
    needed.add(latest)
    compute_through = max(needed)
    for earlier in range(1, compute_through):
        if earlier not in snapshots:
            needed.add(earlier)
    return sorted(needed)


def weeks_to_compute(weeks: list[int], published: set[int], latest_changed: bool) -> list[int]:
    """Published weeks stay put. The latest week is rebuilt only when games changed."""
    if not weeks:
        return []
    latest = max(weeks)
    chosen = [week for week in weeks if week not in published]
    if latest_changed and latest not in chosen:
        chosen.append(latest)
    return sorted(chosen)


def latest_games_changed(stored_fingerprint: str | None, games: list) -> bool:
    if not games and stored_fingerprint:
        return False
    if stored_fingerprint is None:
        return True
    return stored_fingerprint != games_fingerprint(games)


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


def publish_year(
    year: int,
    weeks: list[int],
    processor: CFBDataProcessor,
    *,
    static_root: Path | None = None,
) -> dict:
    """Fetch only weeks that are new or whose latest games changed."""
    published = {
        week for week in weeks
        if read_static_rankings(year, week, root=static_root) is not None
    }
    snapshots = {
        week for week in range(1, (max(weeks) if weeks else 0) + 1)
        if read_source(year, week, static_root) is not None
    }
    fetch = weeks_to_fetch(weeks, published, snapshots)
    fetched: dict[int, list] = {}
    previous_fingerprint: dict[int, str | None] = {}
    for week in fetch:
        previous = read_source(year, week, static_root)
        previous_fingerprint[week] = None if previous is None else previous.get('fingerprint')
        print(f'Fetching {year} week {week} games...')
        fetched[week] = processor.api_client.get_games(year=year, week=week)
        if fetched[week]:
            seed_week_games(year, week, fetched[week])
            # Keep the previous latest-week fingerprint until compute succeeds.
            # Otherwise a failed rebuild looks unchanged on the next Sunday.
            if week != max(weeks):
                write_source(year, week, fetched[week], static_root)

    for week, source in (
        (week, read_source(year, week, static_root))
        for week in range(1, (max(weeks) if weeks else 0) + 1)
    ):
        if week not in fetched and source and source.get('games'):
            seed_week_games(year, week, source['games'])

    latest = max(weeks) if weeks else None
    changed = False
    if latest is not None and latest in fetched:
        changed = latest_games_changed(previous_fingerprint.get(latest), fetched[latest])
    compute = weeks_to_compute(weeks, published, changed)
    for week in sorted(published - set(compute)):
        print(f'Skip unchanged {year} week {week}')
    for week in compute:
        print(f'Precomputing {year} week {week}...')
        precompute(year, week, processor)
        games = fetched.get(week)
        if games:
            write_source(year, week, games, static_root)
    return {'fetched': fetch, 'computed': compute}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Precompute static rankings JSON')
    parser.add_argument('--year', type=int)
    parser.add_argument('--week', type=int)
    parser.add_argument('--through-week', type=int, help='Precompute weeks 1..N')
    parser.add_argument('--current', action='store_true', help='Archive weeks for current season')
    args = parser.parse_args(argv)

    if is_cfbd_killed():
        print('CFBD kill switch is on. Precompute skipped.')
        return 0

    if not os.getenv('CFBD_API_KEY'):
        print('CFBD_API_KEY required', file=sys.stderr)
        return 1

    install_batch_cache_ttl()
    processor = CFBDataProcessor(api_key=os.getenv('CFBD_API_KEY'))
    jobs: list[tuple[int, int]] = []

    if args.current:
        year, cur = current_season_week()
        for week in range(1, cur):
            jobs.append((year, week))
    elif args.year and args.through_week:
        for week in range(1, args.through_week + 1):
            jobs.append((args.year, week))
    elif args.year and args.week:
        jobs.append((args.year, args.week))
    else:
        parser.error('Provide --year/--week, --year/--through-week, or --current')

    by_year: dict[int, list[int]] = {}
    for year, week in jobs:
        by_year.setdefault(year, []).append(week)
    for year, weeks in by_year.items():
        publish_year(year, weeks, processor)

    print(f'Done. Static root: {DEFAULT_ROOT}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
