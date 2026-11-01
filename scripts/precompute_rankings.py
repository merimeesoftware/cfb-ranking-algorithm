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

A regular week is ready when every kickoff older than 36 hours has a score.
One older unscored game is left out of that week's ranking inputs instead
of freezing the board.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / '.env')

# Per Sunday run, not the public daily budget. Actions does not keep CFBD
# responses, so each Sunday starts cold: /teams + two prior seasons (skipped
# when frontend/static/rankings/priors has them) + one bulk /games call.
# 8 is headroom over that 4. See config/cfbd-month.json.
# Cross-run week storage stays on #117.
os.environ.setdefault('CFBD_MAX_CALLS', '8')

from cache import get_cache
from data_processor import CFBDataProcessor
from spend_guards import CFBDOfflineError, is_cfbd_killed, is_cfbd_offline
from ranking_algorithm import TeamQualityRanker
from ranking_service import (
    ALGO_VERSION,
    DEFAULT_CONFIG,
    get_or_calculate_rankings,
    slim_rankings_for_list,
)
from static_rankings import (
    DEFAULT_ROOT,
    read_prior_teams,
    read_static_rankings,
    rebuild_rankings_manifest,
    write_prior_scores,
    write_static_rankings,
)

# Within this process only. The next Sunday starts with an empty .cache.
BATCH_TTL = 30 * 24 * 60 * 60


def install_batch_cache_ttl(current_year: int | None = None) -> None:
    """Keep finished seasons warm. The current season is not pinned for 30 days."""
    import api_integration
    import ranking_service

    api_integration.TTL_TEAMS = BATCH_TTL
    ranking_service.TTL_PRIORS = BATCH_TTL

    def games_ttl(year: int) -> int:
        if current_year is not None and int(year) == int(current_year):
            return 60 * 60
        return BATCH_TTL

    api_integration.get_games_ttl = games_ttl


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


# A kickoff older than this is no longer "in progress".
STALE_KICKOFF = timedelta(hours=36)


def row_complete(game: dict) -> bool:
    if game.get('completed') is False:
        return False
    return game.get('home_score') is not None and game.get('away_score') is not None


def has_final_score(game: dict) -> bool:
    return game.get('home_score') is not None and game.get('away_score') is not None


def _kickoff_text(game: dict) -> str:
    kick = _kickoff(game)
    if kick is None:
        return 'none'
    return kick.strftime('%Y-%m-%dT%H:%M:%SZ')


def _id_key(game: dict) -> tuple:
    game_id = game.get('id')
    if isinstance(game_id, int) and not isinstance(game_id, bool):
        return (0, game_id, '')
    return (1, 0, '' if game_id is None else str(game_id))


def regular_weeks(games: list) -> dict[int, list]:
    by_week: dict[int, list] = {}
    for game in games:
        if (game.get('season_type') or 'regular') != 'regular':
            continue
        week = game.get('week')
        if week is None:
            continue
        try:
            week_num = int(week)
        except (TypeError, ValueError):
            continue
        by_week.setdefault(week_num, []).append(game)
    return by_week


def row_blocks_week(game: dict, now: datetime) -> bool:
    """True when this row should keep its week unpublished.

    Stale rows (kickoff more than 36 hours ago) do not block. A future
    kickoff does. A kickoff inside the 36-hour window blocks only while
    it still has no score.     Undated rows keep the old score check. Notes never settle a row.
    """
    kick = _kickoff(game)
    if kick is None:
        return not row_complete(game)
    if kick > now:
        return True
    if kick >= now - STALE_KICKOFF:
        return not has_final_score(game)
    return False


def week_is_done(rows: list, now: datetime | None = None) -> bool:
    """A week with a scored game, and nothing still live or in the future."""
    if not rows:
        return False
    now = now or now_utc()
    if any(row_blocks_week(row, now) for row in rows):
        return False
    return any(has_final_score(row) for row in rows)


def _omit_reason(game: dict, now: datetime) -> str | None:
    """Why a row stays out of ranking inputs. None means keep it.

    Only a kickoff older than 36 hours with no score is dropped. Notes do
    not change that, and they never settle a future or in-window game.
    """
    if has_final_score(game):
        return None
    kick = _kickoff(game)
    if kick is not None and kick < now - STALE_KICKOFF:
        return 'stale'
    return None


def ranking_inputs(games: list, now: datetime | None = None) -> list:
    """Drop unscored stale rows and log each drop."""
    now = now or now_utc()
    kept = []
    for game in games:
        reason = _omit_reason(game, now)
        if reason is None:
            kept.append(game)
            continue
        print(
            f'excluding {reason} game {game.get("id")} week {game.get("week")} '
            f'kickoff {_kickoff_text(game)} from ranking inputs'
        )
    return sorted(kept, key=_id_key)


def log_regular_week_coverage(games: list) -> None:
    """One derived line per regular week. Ids and kickoffs only, no game payloads."""
    by_week = regular_weeks(games)
    for week in sorted(by_week):
        rows = by_week[week]
        completed = sum(1 for row in rows if row_complete(row))
        incomplete = sorted(
            (row for row in rows if not row_complete(row)),
            key=_id_key,
        )
        shown = [
            f'{row.get("id")}@{_kickoff_text(row)}'
            for row in incomplete[:5]
        ]
        detail = ','.join(shown) if shown else 'none'
        print(
            f'regular week {week}: rows={len(rows)} '
            f'completed={completed} incomplete={detail}'
        )


def games_for_week(games: list, week: int) -> list:
    """Regular games for ``week``. Week 15 also keeps postseason rows.

    Bowl and CFP results change the week-15 fingerprint, so a later Sunday
    recomputes that board instead of leaving it frozen after conference title games.
    """
    rows = []
    for game in games:
        season_type = game.get('season_type') or 'regular'
        if season_type == 'postseason':
            if int(week) >= 15:
                rows.append(game)
            continue
        if game.get('week') == week:
            rows.append(game)
    return rows


def latest_completed_regular_week(games: list, now: datetime | None = None) -> int | None:
    """Highest regular week that is ready to publish.

    Ready means no game is still in the future or inside the 36-hour window
    without a score, and at least one row has a score. A stale unscored row
    does not count against the week.
    """
    if now is None:
        now = now_utc()
    done = [
        week for week, rows in regular_weeks(games).items()
        if week_is_done(rows, now)
    ]
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


def copy_to_frontend(
    year: int,
    week: int,
    source: Path,
    static_root: Path | None = None,
) -> Path | None:
    dest_root = Path(static_root) if static_root is not None else ROOT / 'frontend' / 'static' / 'rankings'
    dest = dest_root / str(year) / f'week-{week}.json'
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.resolve() != Path(source).resolve():
        shutil.copy2(source, dest)
    return dest


def precompute(
    year: int,
    week: int,
    processor: CFBDataProcessor,
    *,
    output_root: Path | None = None,
    static_root: Path | None = None,
) -> Path:
    class Args(dict):
        def get(self, key, default=None):
            return dict.get(self, key, default)

    data = get_or_calculate_rankings(
        processor, year, week, Args(), prefer_static=False
    )
    if not data:
        raise RuntimeError(f'No rankings data for {year} week {week}')
    slim = slim_rankings_for_list(data)
    path = write_static_rankings(slim, year, week, root=output_root)
    fe = copy_to_frontend(year, week, path, static_root)
    print(f'Wrote {path}' + (f' and {fe}' if fe else ''))
    return path


def publish_year(
    year: int,
    weeks: list[int],
    processor: CFBDataProcessor,
    *,
    static_root: Path | None = None,
    output_root: Path | None = None,
    season_games: list | None = None,
    now: datetime | None = None,
) -> dict:
    """One bulk season payload. Recompute unpublished weeks and a changed latest week."""
    if now is None:
        now = now_utc()
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
        rows = ranking_inputs(rows, now)
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
        precompute(
            year,
            week,
            processor,
            output_root=output_root,
            static_root=static_root,
        )
        games = by_week.get(week)
        if games:
            write_source(year, week, games, static_root)
    return {
        'bulk_calls': bulk_calls,
        'computed': compute,
        'fetched_seasons': [year] if bulk_calls else [],
    }


def end_of_season_scores(processor: CFBDataProcessor, games: list) -> dict[str, float]:
    """Ranker output for one finished season. Scores only, no game rows."""
    ranker = TeamQualityRanker(DEFAULT_CONFIG)
    by_week = processor.organize_games_by_week(games)
    for week in sorted(by_week):
        for game in by_week[week]:
            ranker.update_quality_scores(game)
    results = ranker.calculate_final_rankings()
    scores = {}
    for name, data in results.get('rankings', {}).items():
        score = data.get('final_ranking_score')
        if isinstance(score, (int, float)):
            scores[name] = float(score)
    return scores


# Used only when a season's games carry no kickoff. source_sha still identifies the rows.
PRIOR_GENERATED_AT_FALLBACK = '1970-01-01T00:00:00Z'


def _kickoff(game: dict) -> datetime | None:
    """CFBD start time. Processed rows store it as date; raw rows use start_date."""
    raw = game.get('start_date')
    if raw is None:
        raw = game.get('date')
    if raw is None:
        raw = game.get('startDate')
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip()
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def prior_generated_at(games: list) -> str:
    """Latest kickoff in the input. Wall clock would make the same season differ by bytes."""
    kickoffs = [stamp for stamp in (_kickoff(game) for game in games) if stamp is not None]
    if not kickoffs:
        return PRIOR_GENERATED_AT_FALLBACK
    return max(kickoffs).strftime('%Y-%m-%dT%H:%M:%SZ')


def ensure_priors(processor: CFBDataProcessor, year: int, root: Path | None = None) -> list[int]:
    """Write Y-1 and Y-2 derived priors when the published file is missing."""
    fetched = []
    for prior in (year - 1, year - 2):
        if read_prior_teams(prior, algo=ALGO_VERSION, root=root) is not None:
            print(f'Priors hit: {prior}')
            continue
        print(f'Priors fetch: {prior}')
        games = processor.get_games_for_season(prior, through_week=None, use_week_scoped_fetch=False)
        scores = end_of_season_scores(processor, games)
        write_prior_scores(
            prior,
            scores,
            source_sha=games_fingerprint(games),
            generated_at=prior_generated_at(games),
            algo=ALGO_VERSION,
            root=root,
        )
        fetched.append(prior)
    return fetched


def ingest_season(
    processor: CFBDataProcessor,
    year: int,
    weeks: list[int],
    *,
    refresh_games: bool,
    static_root: Path | None = None,
    output_root: Path | None = None,
    now: datetime | None = None,
) -> dict:
    """One bulk /games call. The in-progress season always refetches."""
    if now is None:
        now = now_utc()
    if refresh_games:
        # 30-minute computed boards live under this prefix. A re-dispatch
        # after a bowl must not replay one for the season just refetched.
        get_cache().invalidate_prefix('rankings_computed')
    print(f'Fetching {year} games (one bulk call, refresh={refresh_games})...')
    season_games = processor.api_client.get_games(
        year=year,
        season_type='both',
        refresh=refresh_games,
    )
    log_regular_week_coverage(season_games)
    if not weeks:
        latest = latest_completed_regular_week(season_games, now)
        if not latest:
            print(f'No completed week for {year}.')
            return {'bulk_calls': 0, 'computed': [], 'fetched_seasons': []}
        weeks = list(range(1, latest + 1))
    return publish_year(
        year,
        weeks,
        processor,
        static_root=static_root,
        output_root=output_root,
        season_games=season_games,
        now=now,
    )


def publish_stored_manifests(
    output_root: Path | None = None,
    static_root: Path | None = None,
) -> None:
    """Refresh manifests from files already on disk. No CFBD call."""
    frontend = Path(static_root) if static_root is not None else ROOT / 'frontend' / 'static' / 'rankings'
    rebuild_rankings_manifest(frontend)
    rankings_root = Path(output_root) if output_root is not None else Path(DEFAULT_ROOT)
    if rankings_root.resolve() == frontend.resolve():
        return
    if output_root is not None or rankings_root.exists():
        rebuild_rankings_manifest(rankings_root)


def main(
    argv: list[str] | None = None,
    *,
    output_root: Path | None = None,
    static_root: Path | None = None,
) -> int:
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
        publish_stored_manifests(output_root, static_root)
        return 0

    if is_cfbd_offline():
        # Prod stays CFBD_OFFLINE=1. Publishing still refreshes the manifest
        # from static JSON. The ingest job itself leaves CFBD_OFFLINE unset.
        print('CFBD offline: publishing stored rankings only (0 CFBD calls).')
        publish_stored_manifests(output_root, static_root)
        return 0

    if not os.getenv('CFBD_API_KEY'):
        print('CFBD_API_KEY required', file=sys.stderr)
        return 1

    current_year = season_year(now)
    install_batch_cache_ttl(current_year)
    by_year: dict[int, list[int]] = {}
    if args.current:
        by_year[current_year] = []
    elif args.year and args.through_week:
        by_year[args.year] = list(range(1, args.through_week + 1))
    elif args.year and args.week:
        by_year[args.year] = [args.week]
    else:
        parser.error('Provide --year/--week, --year/--through-week, or --current')

    processor = CFBDataProcessor(api_key=os.getenv('CFBD_API_KEY'))
    prior_root = static_root if static_root is not None else output_root
    try:
        for year, weeks in by_year.items():
            processor.ensure_teams(year, persist=True, root=output_root)
            ensure_priors(processor, year, root=prior_root)
            # The in-progress season always takes one fresh bulk call.
            # There is no cross-run CFBD cache.
            ingest_season(
                processor,
                year,
                weeks,
                refresh_games=(year == current_year),
                static_root=static_root,
                output_root=output_root,
                now=now,
            )
    except CFBDOfflineError as exc:
        print(exc, file=sys.stderr)
        return 1

    publish_stored_manifests(output_root, static_root)
    shown = output_root if output_root is not None else DEFAULT_ROOT
    print(f'Done. Static root: {shown}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
