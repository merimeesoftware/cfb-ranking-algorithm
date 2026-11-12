"""Public games sidecar. One writer, shared by later readers.

The file is ``week-{n}.games.json`` beside a slim board. It is not a stamped
week board: no ``algo`` key, and the manifest ignores the suffix. Rows are
results already in memory. This module does not call CFBD.

A missing file stays empty. Unplayed games stay out. Two meetings stay two
rows. Names join exactly, so Miami and Miami (OH) stay different teams.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from static_rankings import _read_contained, _write_contained

SCHEMA = 1
KIND = 'games'
SUFFIX = 'games.json'
SEALED_YEAR = 2025

ROW_FIELDS = (
    'week',
    'home',
    'away',
    'home_score',
    'away_score',
    'neutral_site',
    'season_type',
    'home_conference',
    'away_conference',
    'notes',
)


class GamesSidecarError(ValueError):
    """The sidecar cannot be written for this year."""


def _text(game: Dict[str, Any], *keys: str) -> Optional[str]:
    for key in keys:
        value = game.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _score(value: Any) -> Optional[int]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def _week_number(game: Dict[str, Any]) -> Optional[int]:
    try:
        week = int(game.get('week'))
    except (TypeError, ValueError):
        return None
    return week


def _season_type(game: Dict[str, Any]) -> str:
    """The row's own season type. Notes do not rewrite it."""
    raw = _text(game, 'season_type', 'seasonType')
    if raw is None:
        return 'regular'
    return raw.lower()


def _through_week(game: Dict[str, Any], through_week: int) -> bool:
    """Scored rows that belong on the board published for ``through_week``.

    Postseason rows stay off weeks 1–14. From week 15 they stay, whatever
    week number the postseason payload used.
    """
    if _season_type(game) == 'postseason':
        return through_week >= 15
    week = _week_number(game)
    return week is not None and week <= through_week


def public_game_row(game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """One allowlisted result. None when the game has no final score.

    ``neutral_site`` is the boolean on the row. Notes are the event label
    already stored with the game, kept so a later reader can see a
    conference title without a second copy of the payload. Lines, spreads,
    odds, and picks are not copied.
    """
    if not isinstance(game, dict):
        return None
    if game.get('completed') is False:
        return None
    home = _text(game, 'home_team_name', 'home', 'homeTeam')
    away = _text(game, 'away_team_name', 'away', 'awayTeam')
    home_score = _score(game.get('home_score', game.get('homePoints')))
    away_score = _score(game.get('away_score', game.get('awayPoints')))
    week = _week_number(game)
    if not home or not away or home_score is None or away_score is None or week is None:
        return None
    notes = game.get('notes')
    return {
        'week': week,
        'home': home,
        'away': away,
        'home_score': home_score,
        'away_score': away_score,
        'neutral_site': bool(game.get('neutral_site') or game.get('neutralSite')),
        'season_type': _season_type(game),
        'home_conference': _text(game, 'home_conference', 'homeConference'),
        'away_conference': _text(game, 'away_conference', 'awayConference'),
        'notes': notes.strip() if isinstance(notes, str) else '',
    }


def games_through_week(games: List[Dict[str, Any]], through_week: int) -> List[Dict[str, Any]]:
    """Scored public rows through ``through_week``, stable and de-duplicated."""
    rows = []
    seen = set()
    for game in games or []:
        if not isinstance(game, dict) or not _through_week(game, through_week):
            continue
        row = public_game_row(game)
        if row is None:
            continue
        key = (
            row['week'],
            row['home'],
            row['away'],
            row['home_score'],
            row['away_score'],
            row['season_type'],
        )
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
    rows.sort(key=lambda row: (row['week'], row['home'], row['away'], row['season_type']))
    return rows


def sidecar_document(year: int, week: int, games: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Schema is year, week, and games. Not a week board."""
    return {
        'schema': SCHEMA,
        'kind': KIND,
        'year': year,
        'week': week,
        'games': games_through_week(games, week),
    }


def write_games_sidecar(
    year: int,
    week: int,
    games: List[Dict[str, Any]],
    root: Optional[Union[str, Any]] = None,
):
    """Write the one public games sidecar. Refuses the sealed 2025 holdout."""
    if type(year) is not int or type(week) is not int:
        raise GamesSidecarError('year and week must be integers')
    if year == SEALED_YEAR:
        raise GamesSidecarError('2025 is the sealed holdout. Not writing a games sidecar.')
    document = sidecar_document(year, week, games)
    if 'algo' in document:
        raise GamesSidecarError('games sidecar must not carry an algo stamp')
    return _write_contained(document, year, week, SUFFIX, root, pretty=True)


def empty_games(year: int, week: int) -> Dict[str, Any]:
    """What a missing sidecar means: no rows, and no fetch."""
    return {
        'present': False,
        'year': year,
        'week': week,
        'games': [],
    }


def read_games_sidecar(
    year: int,
    week: int,
    root: Optional[Union[str, Any]] = None,
) -> Dict[str, Any]:
    """Read a sidecar. Missing, sealed, or unreadable stays empty. No CFBD."""
    if type(year) is not int or type(week) is not int or year == SEALED_YEAR:
        return empty_games(year if type(year) is int else 0, week if type(week) is int else 0)
    if root is None:
        from pathlib import Path

        from static_rankings import DEFAULT_ROOT

        frontend = Path(__file__).resolve().parent / 'frontend' / 'static' / 'rankings'
        for candidate in (frontend, Path(DEFAULT_ROOT)):
            loaded = read_games_sidecar(year, week, root=candidate)
            if loaded['present']:
                return loaded
        return empty_games(year, week)

    payload = _read_contained(year, week, SUFFIX, root)
    if not isinstance(payload, dict):
        return empty_games(year, week)
    if payload.get('schema') != SCHEMA or payload.get('kind') != KIND:
        return empty_games(year, week)
    if 'algo' in payload:
        return empty_games(year, week)
    games = payload.get('games')
    if not isinstance(games, list):
        return empty_games(year, week)
    rows = []
    for game in games:
        if not isinstance(game, dict):
            continue
        row = {field: game.get(field) for field in ROW_FIELDS}
        if not row['home'] or not row['away']:
            continue
        rows.append(row)
    return {
        'present': True,
        'year': year,
        'week': week,
        'games': rows,
    }
