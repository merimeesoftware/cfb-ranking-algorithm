"""Hand-entered CFP selection-committee rows (#174).

Legal log D-20261112-15. The source of record is hand entry from the weekly
CFP release. A stored row has rank, team name, an optional record, and a
release date. Nothing else is stored: no release text, no images, no raw
CFBD JSON, and no ``algo`` / ``ALGO_VERSION`` stamp.

These files are not week boards. They are not named ``week-N.json``, they
are not listed in the rankings manifest, and they are not a public table.
This module does not call CFBD, does not scrape, and does not read 2025.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

SOURCE_OF_RECORD = 'hand-entry'
STORED_FIELDS = ('rank', 'team_name', 'record', 'release_date')
ALLOWED_KEYS = frozenset(STORED_FIELDS)
YEAR_MIN = 2014
YEAR_MAX = 2024
SEALED_YEAR = 2025
SEALED_YEAR_PART = str(SEALED_YEAR)
RANK_MIN = 1
RANK_MAX = 25
COMMITTEE_POLL = 'Playoff Committee Rankings'
YEAR_FILE = re.compile(r'^(\d{4})\.json$')
WEEK_FILE = re.compile(r'^week-\d+\.json$')
RELEASE_DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
RECORD = re.compile(r'^\d{1,2}-\d{1,2}(?:-\d{1,2})?$')
ATTRIBUTION = (
    'CFP selection committee ranking, released [DATE]. '
    'Source: collegefootballplayoff.com. '
    'Not affiliated with or endorsed by the College Football Playoff.'
)

# Stored rows stay plain data. The citation string lives here, not in the file.
_BANNED_TEXT = (
    'official',
    'endorsed',
    'playoff committee rankings',
    'ap top 25',
    'coaches poll',
    'firstplacevotes',
    'http://',
    'https://',
    'data:image',
    '.png',
    '.jpg',
    '.jpeg',
    '.gif',
    '.webp',
    '.svg',
)
_ALGO_KEYS = frozenset({'algo', 'algo_version'})


class CommitteeFormatError(ValueError):
    """The payload is not a hand-entered committee file."""

    def __init__(self, errors: Sequence[str]):
        self.errors = list(errors)
        super().__init__('; '.join(self.errors))


def attribution_line(release_date: str) -> str:
    """Citation for one release. ``[DATE]`` is filled from that release date.

    The line is not written into the committee file.
    """
    errors = committee_errors([{
        'release_date': release_date,
        'rank': 1,
        'team_name': 'Citation Check',
    }])
    if errors:
        raise CommitteeFormatError(errors)
    return ATTRIBUTION.replace('[DATE]', release_date)


def committee_errors(
    payload: Any,
    *,
    filename: Optional[str] = None,
    forbidden_stamps: Iterable[str] = ('v5.5',),
) -> list[str]:
    """Problems that keep ``payload`` from being a committee file. Empty means valid."""
    stamps = tuple(dict.fromkeys(str(stamp) for stamp in forbidden_stamps))
    errors: list[str] = []
    _banned_content(payload, stamps, errors)
    file_year = _filename_errors(filename, errors)
    if not isinstance(payload, list):
        errors.append('a committee file is a list of rows, not a board or a CFBD object')
        return _dedupe(errors)
    if not payload:
        errors.append('a committee file needs at least one row')
        return _dedupe(errors)

    seen: dict[str, dict[str, set]] = {}
    years: set[int] = set()
    for index, row in enumerate(payload):
        if not isinstance(row, dict):
            errors.append(f'row {index} must be an object')
            continue
        extra = [key for key in row.keys() if key not in ALLOWED_KEYS]
        if extra:
            errors.append(
                f'row {index} has fields that are not stored: {sorted(map(str, extra))}'
            )
        release = _release_date(row.get('release_date'), index, errors)
        rank = _rank(row.get('rank'), index, errors)
        name = _team_name(row.get('team_name'), index, errors)
        if 'record' in row:
            _record(row.get('record'), index, errors)
        if release is None or rank is None or name is None:
            continue
        years.add(release.year)
        bucket = seen.setdefault(release.isoformat(), {'ranks': set(), 'names': set()})
        if rank in bucket['ranks']:
            errors.append(f'{release.isoformat()} repeats rank {rank}')
        if name in bucket['names']:
            errors.append(f'{release.isoformat()} repeats team {name!r}')
        bucket['ranks'].add(rank)
        bucket['names'].add(name)

    _year_errors(file_year, years, errors)
    return _dedupe(errors)


def hand_entered_rows(
    rows: Any,
    *,
    filename: Optional[str] = None,
    forbidden_stamps: Iterable[str] = ('v5.5',),
) -> list[dict]:
    """Return canonical hand-entered rows, or raise ``CommitteeFormatError``."""
    errors = committee_errors(rows, filename=filename, forbidden_stamps=forbidden_stamps)
    if errors:
        raise CommitteeFormatError(errors)
    return _canonical(rows)


def checked_backfill(
    hand_rows: Any,
    cfbd_body: Any,
    *,
    forbidden_stamps: Iterable[str] = ('v5.5',),
) -> list[dict]:
    """Keep the hand-entered rows when one CFBD fixture matches them.

    CFBD is not the source of record. This does not call the network, does
    not write the CFBD body, and does not store poll text. Rank and team
    name must match one release. A mismatch returns no rows.
    """
    entered = hand_entered_rows(hand_rows, forbidden_stamps=forbidden_stamps)
    releases = {row['release_date'] for row in entered}
    if len(releases) != 1:
        raise CommitteeFormatError(['a backfill checks one release date at a time'])
    extracted = _committee_ranks_from_cfbd(cfbd_body)
    hand_pairs = sorted((row['rank'], row['team_name']) for row in entered)
    cfbd_pairs = sorted(extracted)
    if hand_pairs != cfbd_pairs:
        missing = sorted(set(hand_pairs) - set(cfbd_pairs))
        extra = sorted(set(cfbd_pairs) - set(hand_pairs))
        raise CommitteeFormatError([
            'CFBD backfill does not match the hand-entered list',
            f'missing from CFBD fixture: {missing}',
            f'not on the hand-entered list: {extra}',
        ])
    return entered


def dumps_committee(rows: Sequence[dict]) -> str:
    """Canonical JSON for a validated committee file."""
    return json.dumps(_canonical(rows), indent=2) + '\n'


def path_is_sealed(path: Path) -> bool:
    """True when a path part, or the file name, is the sealed holdout year.

    Path parts are strings. Comparing them to the integer year never matches.
    """
    candidate = Path(path)
    if SEALED_YEAR_PART in candidate.parts:
        return True
    return candidate.name in {SEALED_YEAR_PART, f'{SEALED_YEAR_PART}.json'}


def write_committee_file(
    directory: Path,
    rows: Any,
    *,
    year: int,
    forbidden_stamps: Iterable[str] = ('v5.5',),
) -> Path:
    """Write ``{year}.json`` under ``directory``. Does not touch the manifest."""
    if type(year) is not int:
        raise CommitteeFormatError(['year must be an integer'])
    filename = f'{year}.json'
    path = Path(directory) / filename
    if year == SEALED_YEAR or path_is_sealed(path):
        raise CommitteeFormatError(['2025 is the sealed holdout.'])
    stored = hand_entered_rows(rows, filename=filename, forbidden_stamps=forbidden_stamps)
    if WEEK_FILE.match(path.name):
        raise CommitteeFormatError(['committee files are not named week-N.json'])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps_committee(stored), encoding='utf-8')
    return path


def _canonical(rows: Sequence[dict]) -> list[dict]:
    ordered = sorted(rows, key=lambda row: (row['release_date'], row['rank']))
    stored = []
    for row in ordered:
        item = {
            'release_date': row['release_date'],
            'rank': row['rank'],
            'team_name': row['team_name'],
        }
        if 'record' in row:
            item['record'] = row['record']
        stored.append(item)
    return stored


def _filename_errors(filename: Optional[str], errors: list[str]) -> Optional[int]:
    if not filename:
        return None
    if WEEK_FILE.match(filename):
        errors.append('committee files are not named week-N.json and are not boards')
        return None
    match = YEAR_FILE.match(filename)
    if not match:
        errors.append('committee files are named {year}.json')
        return None
    year = int(match.group(1))
    if year == SEALED_YEAR:
        errors.append('2025 is the sealed holdout.')
        return year
    if year < YEAR_MIN or year > YEAR_MAX:
        errors.append(f'year {year} is outside {YEAR_MIN}-{YEAR_MAX}')
    return year


def _year_errors(file_year: Optional[int], years: set[int], errors: list[str]) -> None:
    if SEALED_YEAR in years:
        errors.append('2025 is the sealed holdout.')
    if file_year is not None:
        if years and years != {file_year}:
            errors.append(f'release dates must fall in {file_year}')
        return
    if not years:
        return
    if len(years) != 1:
        errors.append(f'release dates must fall in one year from {YEAR_MIN} through {YEAR_MAX}')
        return
    year = next(iter(years))
    if year != SEALED_YEAR and (year < YEAR_MIN or year > YEAR_MAX):
        errors.append(f'year {year} is outside {YEAR_MIN}-{YEAR_MAX}')


def _release_date(value: Any, index: int, errors: list[str]) -> Optional[date]:
    if not isinstance(value, str) or not RELEASE_DATE.match(value):
        errors.append(f'row {index} needs a release_date as YYYY-MM-DD')
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        errors.append(f'row {index} has a bad release_date {value!r}')
        return None
    if parsed.isoformat() != value:
        errors.append(f'row {index} needs a release_date as YYYY-MM-DD')
        return None
    return parsed


def _rank(value: Any, index: int, errors: list[str]) -> Optional[int]:
    if type(value) is not int or not (RANK_MIN <= value <= RANK_MAX):
        errors.append(f'row {index} needs an integer rank from {RANK_MIN} to {RANK_MAX}')
        return None
    return value


def _team_name(value: Any, index: int, errors: list[str]) -> Optional[str]:
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > 80:
        errors.append(f'row {index} needs a team_name')
        return None
    if any(ord(char) < 32 for char in value):
        errors.append(f'row {index} needs a team_name')
        return None
    return value


def _record(value: Any, index: int, errors: list[str]) -> None:
    if not isinstance(value, str) or not RECORD.match(value):
        errors.append(f'row {index} record must look like 8-0')


def _banned_content(value: Any, stamps: Sequence[str], errors: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str) or key.casefold() in _ALGO_KEYS:
                errors.append('committee files never carry algo or ALGO_VERSION')
            elif key in {'season', 'year'} and child == SEALED_YEAR:
                errors.append('2025 is the sealed holdout.')
            _banned_content(child, stamps, errors)
        return
    if isinstance(value, list):
        for child in value:
            _banned_content(child, stamps, errors)
        return
    if isinstance(value, str):
        folded = value.casefold()
        for stamp in stamps:
            if stamp and stamp in value:
                errors.append(f'committee files never carry {stamp}')
        for banned in _BANNED_TEXT:
            if banned in folded:
                errors.append(f'committee files do not store {banned!r}')
    if value == SEALED_YEAR and not isinstance(value, bool):
        errors.append('2025 is the sealed holdout.')


def _committee_ranks_from_cfbd(body: Any) -> list[tuple[int, str]]:
    """Read rank and school from one committee poll. Drop every other field."""
    if not isinstance(body, list) or not body:
        raise CommitteeFormatError(['CFBD fixture must be a non-empty list'])
    weeks: list[list[tuple[int, str]]] = []
    for week in body:
        if not isinstance(week, dict):
            raise CommitteeFormatError(['CFBD fixture week must be an object'])
        if str(week.get('season')) == str(SEALED_YEAR) or str(week.get('year')) == str(SEALED_YEAR):
            raise CommitteeFormatError(['2025 is the sealed holdout.'])
        polls = week.get('polls')
        if not isinstance(polls, list):
            continue
        found: list[tuple[int, str]] = []
        for poll in polls:
            if not isinstance(poll, dict) or poll.get('poll') != COMMITTEE_POLL:
                continue
            if found:
                raise CommitteeFormatError(['CFBD fixture repeats the committee poll in one week'])
            ranks = poll.get('ranks')
            if not isinstance(ranks, list) or not ranks:
                raise CommitteeFormatError(['committee poll ranks must be a non-empty list'])
            for item in ranks:
                if not isinstance(item, dict) or type(item.get('rank')) is not int \
                        or not isinstance(item.get('school'), str) or not item.get('school'):
                    raise CommitteeFormatError(['committee poll rank needs an integer rank and a school'])
                found.append((item['rank'], item['school']))
        if found:
            weeks.append(found)
    if len(weeks) != 1:
        raise CommitteeFormatError([
            'a backfill uses one CFBD week that contains the committee poll; week numbers are not stored',
        ])
    return weeks[0]


def _dedupe(errors: list[str]) -> list[str]:
    return list(dict.fromkeys(errors))
