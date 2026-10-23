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
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / '.env')

# Per Sunday run, not the public daily budget. Cache hits do not count.
# A cold Sunday is /teams (if missing) + two baseline seasons (if missing)
# + one bulk /games call. 8 is headroom over that 4. Steady Sundays are 1.
# See config/cfbd-month.json. Cross-run week storage stays on #117.
os.environ.setdefault('CFBD_MAX_CALLS', '8')

from cache import get_cache
from data_processor import CFBDataProcessor
from spend_guards import is_cfbd_killed, is_cfbd_offline
from ranking_service import (
    get_or_calculate_rankings,
    slim_rankings_for_list,
)
from static_rankings import (
    DEFAULT_ROOT,
    read_baseline_games,
    read_static_rankings,
    rebuild_rankings_manifest,
    write_baseline_games,
    write_static_rankings,
)

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


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def is_offseason(now: datetime | None = None) -> bool:
    """Jan 21 through Aug 23. Bowl weeks through Jan 20 still count as in season."""
    now = now or now_utc()
    if (now.month, now.day) <= (1, 20):
        return False
    if (now.month, now.day) < (8, 24):
        return True
    return False


def season_year(now: datetime | None = None) -> int:
    """January bowls belong to the season that started the previous August."""
    now = now or now_utc()
    if now.month == 1:
        return now.year - 1
    return now.year


def current_season_week(now: datetime | None = None) -> tuple[int, int]:
    now = now or now_utc()
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


def row_complete(game: dict) -> bool:
    if game.get('completed') is False:
        return False
    return game.get('home_score') is not None and game.get('away_score') is not None


def games_for_week(games: list, week: int) -> list:
    rows = []
    for game in games:
        if (game.get('season_type') or 'regular') != 'regular':
            continue
        if game.get('week') == week:
            rows.append(game)
    return rows


def latest_completed_regular_week(games: list) -> int | None:
    """Highest regular week whose games all have scores. Partial weeks wait."""
    by_week: dict[int, list] = {}
    for game in games:
        if (game.get('season_type') or 'regular') != 'regular':
            continue
        week = game.get('week')
        if week is None:
            continue
        by_week.setdefault(int(week), []).append(game)
    done = [week for week, rows in by_week.items() if rows and all(row_complete(row) for row in rows)]
    return max(done) if done else None


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
    season_games: list | None = None,
) -> dict:
    """One bulk season payload. Recompute unpublished weeks and a changed latest week."""
    if not weeks:
        return {'bulk_calls': 0, 'computed': [], 'fetched_seasons': []}
    bulk_calls = 0
    if season_games is None:
        print(f'Fetching {year} games (one bulk call)...')
        season_games = processor.api_client.get_games(year=year, season_type='both')
        bulk_calls = 1
    published = {
        week for week in weeks
        if read_static_rankings(year, week, root=static_root) is not None
    }
    previous_fingerprint: dict[int, str | None] = {}
    by_week: dict[int, list] = {}
    latest = max(weeks)
    for week in weeks:
        previous = read_source(year, week, static_root)
        previous_fingerprint[week] = None if previous is None else previous.get('fingerprint')
        rows = games_for_week(season_games, week)
        if not rows and previous and previous.get('games'):
            rows = previous['games']
        by_week[week] = rows
        if rows:
            seed_week_games(year, week, rows)
            # Keep the previous latest-week fingerprint until compute succeeds.
            if week != latest:
                write_source(year, week, rows, static_root)

    compute = []
    for week in weeks:
        week_changed = latest_games_changed(
            previous_fingerprint.get(week),
            by_week.get(week) or [],
        )
        if week not in published or week_changed:
            compute.append(week)
    for week in sorted(published - set(compute)):
        print(f'Skip unchanged {year} week {week}')
    for week in compute:
        print(f'Precomputing {year} week {week}...')
        precompute(year, week, processor)
        games = by_week.get(week)
        if games:
            write_source(year, week, games, static_root)
    return {
        'bulk_calls': bulk_calls,
        'computed': compute,
        'fetched_seasons': [year] if bulk_calls else [],
    }


def ensure_baseline(processor: CFBDataProcessor, year: int, root: Path | None = None) -> list[int]:
    """Write Y-1 and Y-2 processed games once. Later Sundays read the files."""
    fetched = []
    for prior in (year - 1, year - 2):
        if read_baseline_games(prior, root=root) is not None:
            print(f'Baseline hit: {prior}')
            continue
        print(f'Baseline fetch: {prior}')
        games = processor.get_games_for_season(prior, through_week=None, use_week_scoped_fetch=False)
        write_baseline_games(prior, games, root=root)
        fetched.append(prior)
    return fetched


def publish_stored_manifests() -> None:
    """Refresh manifests from files already on disk. No CFBD call."""
    frontend = ROOT / 'frontend' / 'static' / 'rankings'
    rebuild_rankings_manifest(frontend)
    if Path(DEFAULT_ROOT).exists():
        rebuild_rankings_manifest(DEFAULT_ROOT)


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

    now = now_utc()
    if args.current and is_offseason(now):
        print('Off-season: precompute skipped (0 CFBD calls).')
        publish_stored_manifests()
        return 0

    if is_cfbd_offline():
        # Prod stays CFBD_OFFLINE=1. Publishing still refreshes the manifest
        # from static JSON. The ingest job itself leaves CFBD_OFFLINE unset.
        print('CFBD offline: publishing stored rankings only (0 CFBD calls).')
        publish_stored_manifests()
        return 0

    if not os.getenv('CFBD_API_KEY'):
        print('CFBD_API_KEY required', file=sys.stderr)
        return 1

    install_batch_cache_ttl()
    by_year: dict[int, list[int]] = {}
    if args.current:
        year = season_year(now)
        by_year[year] = []
    elif args.year and args.through_week:
        by_year[args.year] = list(range(1, args.through_week + 1))
    elif args.year and args.week:
        by_year[args.year] = [args.week]
    else:
        parser.error('Provide --year/--week, --year/--through-week, or --current')

    processor = CFBDataProcessor(api_key=os.getenv('CFBD_API_KEY'))
    for year, weeks in by_year.items():
        processor.ensure_teams(year, persist=True)
        ensure_baseline(processor, year)
        print(f'Fetching {year} games (one bulk call)...')
        season_games = processor.api_client.get_games(year=year, season_type='both')
        if not weeks:
            latest = latest_completed_regular_week(season_games)
            if not latest:
                print(f'No completed week for {year}.')
                continue
            weeks = list(range(1, latest + 1))
        publish_year(year, weeks, processor, season_games=season_games)

    publish_stored_manifests()
    print(f'Done. Static root: {DEFAULT_ROOT}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
