"""TR+ 12-team field. Our projection, not the committee's list.

Rules are cited from NCAA.com, "How the College Football Playoff works"
(canonical URL dated 2026-08-11, retrieved 27 Aug 2026):

https://www.ncaa.com/news/football/article/2026-08-11/how-college-football-playoff-works-schedule-selections-rankings-byes-and-more

2024: the five highest-ranked conference champions, any conference, are in.
Byes go to the four highest-ranked of those champions.

2026: the ACC, Big Ten, Big 12, and SEC champions are in. The highest-ranked
team from the American, Conference USA, MAC, Mountain West, Pac-12, or Sun
Belt is in, whether or not that team won its conference. Notre Dame is in
when it is inside the top 12 of this board. Byes go to the four
highest-ranked teams in the field. The first round is 5 vs 12, 6 vs 11,
7 vs 10, and 8 vs 9, with no re-seeding.

A champion is the winner of that conference's title game. The game has to
be a regular-season row, both teams have to be in that conference, and the
notes have to name that conference's championship. Conference wins do not
name a champion. This module does not use the ranker's postseason flag, and
it does not call CFBD. 2025 is refused. The committee column stays out
until that file exists on its own.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from conference_membership import load_membership
from static_rankings import _write_contained

SCHEMA = 1
KIND = 'tr-plus-field'
SUFFIX = 'field.json'
SEALED_YEAR = 2025
FIELD_SIZE = 12
TOP_12 = 12
NOTRE_DAME = 'Notre Dame'
RULES_SOURCE = (
    'https://www.ncaa.com/news/football/article/2026-08-11/'
    'how-college-football-playoff-works-schedule-selections-rankings-byes-and-more'
)
RULES_RETRIEVED = '2026-08-27'
POWER_CONFERENCES = ('ACC', 'Big Ten', 'Big 12', 'SEC')
# NCAA short names in the citation, stored here under our membership names.
GROUP_OF_SIX = (
    'American Athletic',
    'Conference USA',
    'Mid-American',
    'Mountain West',
    'Pac-12',
    'Sun Belt',
)
NCAA_SHORT = {
    'American Athletic': 'American',
    'Mid-American': 'MAC',
    'Conference USA': 'Conference USA',
    'Mountain West': 'Mountain West',
    'Sun Belt': 'Sun Belt',
    'Pac-12': 'Pac-12',
    'SEC': 'SEC',
    'Big Ten': 'Big Ten',
    'Big 12': 'Big 12',
    'ACC': 'ACC',
}
FIRST_ROUND = ((5, 12), (6, 11), (7, 10), (8, 9))


class FieldError(ValueError):
    """The field cannot be built for this year or ruleset."""


def _notes_name_title(notes: Any, conference: str) -> bool:
    """True when notes name this conference's championship game.

    A bare "championship" substring is not enough. That check is what the
    ranker already uses to change home field and K, and this is not that check.
    """
    if not isinstance(notes, str):
        return False
    text = ' '.join(notes.lower().split())
    if not text or 'national championship' in text or 'playoff' in text:
        return False
    labels = [conference.lower()]
    short = NCAA_SHORT.get(conference)
    if short and short.lower() not in labels:
        labels.append(short.lower())
    for label in labels:
        if f'{label} championship' in text:
            return True
    return text in {'conference championship', 'conference championship game'}


def _score(value: Any) -> Optional[int]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def _sides(game: Dict[str, Any]) -> Optional[tuple]:
    home = game.get('home') or game.get('home_team_name')
    away = game.get('away') or game.get('away_team_name')
    if not isinstance(home, str) or not isinstance(away, str):
        return None
    home_score = _score(game.get('home_score', game.get('homePoints')))
    away_score = _score(game.get('away_score', game.get('awayPoints')))
    if home_score is None or away_score is None:
        return None
    return home, away, home_score, away_score


def champions_from_games(games: List[Dict[str, Any]], year: int) -> Dict[str, Optional[str]]:
    """Champions named by a title game. Missing games are omitted, not guessed.

    A tie, or more than one title game in the same conference, is ``None``.
    """
    if type(year) is not int:
        raise FieldError('year must be an integer')
    if year == SEALED_YEAR:
        raise FieldError('2025 is the sealed holdout. Not reading a field from it.')
    season = load_membership().season_map(year)
    found: Dict[str, List[Optional[str]]] = {}
    for game in games or []:
        if not isinstance(game, dict):
            continue
        season_type = str(game.get('season_type') or 'regular').lower()
        if season_type == 'postseason':
            continue
        sides = _sides(game)
        if sides is None:
            continue
        home, away, home_score, away_score = sides
        home_conf = season.get(home)
        away_conf = season.get(away)
        if not home_conf or home_conf != away_conf or home_conf == 'FBS Independents':
            continue
        if not _notes_name_title(game.get('notes'), home_conf):
            continue
        if home_score == away_score:
            winner: Optional[str] = None
        elif home_score > away_score:
            winner = home
        else:
            winner = away
        found.setdefault(home_conf, []).append(winner)
    champions: Dict[str, Optional[str]] = {}
    for conference, winners in found.items():
        if len(winners) == 1 and isinstance(winners[0], str):
            champions[conference] = winners[0]
        else:
            champions[conference] = None
    return champions


def _ranked(board: List[Dict[str, Any]], year: Optional[int]) -> List[Dict[str, Any]]:
    """Board order is the rank. Membership supplies the conference when a year is set."""
    membership = load_membership() if year is not None else None
    if membership is not None:
        membership.season_map(year)
    rows = []
    seen = set()
    for team in board or []:
        if not isinstance(team, dict):
            continue
        name = team.get('team_name')
        if not isinstance(name, str) or not name or name in seen:
            continue
        seen.add(name)
        board_conf = team.get('conference')
        conference = board_conf if isinstance(board_conf, str) else None
        if membership is not None:
            mapped = membership.conference_for(name, year)
            if mapped is not None:
                conference = mapped
        rows.append({
            'team': name,
            'rank': len(rows) + 1,
            'conference': conference,
        })
    return rows


def _empty_slot(bid: str, conference: Optional[str] = None) -> Dict[str, Any]:
    return {
        'seed': None,
        'team': None,
        'rank': None,
        'conference': conference,
        'bid': bid,
        'bye': None,
    }


def _slot(row: Dict[str, Any], bid: str, seed: Optional[int], bye: Optional[bool]) -> Dict[str, Any]:
    return {
        'seed': seed,
        'team': row['team'],
        'rank': row['rank'],
        'conference': row['conference'],
        'bid': bid,
        'bye': bye,
    }


def _pad(slots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    padded = list(slots)
    while len(padded) < FIELD_SIZE:
        padded.append(_empty_slot('unfilled'))
    return padded[:FIELD_SIZE]


def _first_round(slots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_seed = {slot['seed']: slot for slot in slots if slot.get('seed') is not None}
    pairs = []
    for higher, lower in FIRST_ROUND:
        pairs.append({
            'higher_seed': higher,
            'lower_seed': lower,
            'higher_team': by_seed[higher]['team'],
            'lower_team': by_seed[lower]['team'],
        })
    return pairs


def _document(
    ruleset_id: str,
    ranked_year: Optional[int],
    week: Optional[int],
    board_algo: Optional[str],
    incomplete: bool,
    champion_map: Dict[str, Optional[str]],
    slots: List[Dict[str, Any]],
    first_round: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        'schema': SCHEMA,
        'kind': KIND,
        'projection': 'TR+',
        'ruleset_id': ruleset_id,
        'rules_source': RULES_SOURCE,
        'rules_retrieved': RULES_RETRIEVED,
        'board_algo': board_algo,
        'year': ranked_year,
        'week': week,
        'as_of': {'year': ranked_year, 'week': week},
        'incomplete': incomplete,
        'champion_map': champion_map,
        'slots': slots,
        'first_round': first_round,
    }


def _project_2026(
    ranked: List[Dict[str, Any]],
    champions: Dict[str, Optional[str]],
    year: Optional[int],
    week: Optional[int],
    board_algo: Optional[str],
    champions_final: Optional[bool],
) -> Dict[str, Any]:
    by_name = {row['team']: row for row in ranked}
    champion_map: Dict[str, Optional[str]] = {conf: champions.get(conf) for conf in POWER_CONFERENCES}
    for conference, name in champions.items():
        if conference not in champion_map:
            champion_map[conference] = name

    known = []
    missing = []
    used = set()
    for conference in POWER_CONFERENCES:
        name = champion_map.get(conference)
        row = by_name.get(name) if isinstance(name, str) else None
        if row is None:
            missing.append(conference)
            continue
        known.append(_slot(row, 'power-conference-champion', None, None))
        used.add(row['team'])

    g6_rows = [row for row in ranked if row['conference'] in GROUP_OF_SIX and row['team'] not in used]
    if g6_rows:
        known.append(_slot(g6_rows[0], 'group-of-six-highest-ranked', None, None))
        used.add(g6_rows[0]['team'])
        missing_g6 = False
    else:
        missing_g6 = True

    notre_dame = by_name.get(NOTRE_DAME)
    if notre_dame is not None and notre_dame['rank'] <= TOP_12 and notre_dame['team'] not in used:
        known.append(_slot(notre_dame, 'notre-dame-top-12', None, None))
        used.add(notre_dame['team'])

    required_open = bool(missing) or missing_g6 or champions_final is False
    if required_open or len(ranked) < FIELD_SIZE:
        slots = []
        for conference in POWER_CONFERENCES:
            match = [
                slot for slot in known
                if slot['bid'] == 'power-conference-champion' and slot['conference'] == conference
            ]
            slots.append(match[0] if match else _empty_slot('power-conference-champion', conference))
        g6_slot = [slot for slot in known if slot['bid'] == 'group-of-six-highest-ranked']
        slots.append(g6_slot[0] if g6_slot else _empty_slot('group-of-six-highest-ranked'))
        nd_slot = [slot for slot in known if slot['bid'] == 'notre-dame-top-12']
        if nd_slot:
            slots.append(nd_slot[0])
        return _document(
            '2026', year, week, board_algo, True, champion_map, _pad(slots), [],
        )

    pool = [row for row in ranked if row['team'] not in used]
    at_large = pool[:FIELD_SIZE - len(known)]
    if len(known) + len(at_large) < FIELD_SIZE:
        return _document(
            '2026', year, week, board_algo, True, champion_map,
            _pad(known), [],
        )
    field = known + [_slot(row, 'at-large', None, None) for row in at_large]
    field.sort(key=lambda slot: slot['rank'])
    for index, slot in enumerate(field, start=1):
        slot['seed'] = index
        slot['bye'] = index <= 4
    return _document(
        '2026', year, week, board_algo, False, champion_map, field, _first_round(field),
    )


def _project_2024(
    ranked: List[Dict[str, Any]],
    champions: Dict[str, Optional[str]],
    year: Optional[int],
    week: Optional[int],
    board_algo: Optional[str],
    champions_final: Optional[bool],
) -> Dict[str, Any]:
    by_name = {row['team']: row for row in ranked}
    champion_map = dict(champions)
    named = []
    for conference, name in champion_map.items():
        if not isinstance(name, str):
            continue
        row = by_name.get(name)
        if row is None:
            continue
        named.append((row, conference))
    named.sort(key=lambda item: item[0]['rank'])
    unresolved = any(name is None for name in champion_map.values()) or not named
    if champions_final is False or unresolved or len(named) < 5:
        slots = [
            _slot(row, 'conference-champion', None, None)
            for row, _conference in named
        ]
        return _document(
            '2024', year, week, board_algo, True, champion_map, _pad(slots), [],
        )

    five = named[:5]
    auto_names = {row['team'] for row, _conference in five}
    at_large_rows = [row for row in ranked if row['team'] not in auto_names][:7]
    if len(at_large_rows) < 7:
        slots = [_slot(row, 'conference-champion', None, None) for row, _conference in five]
        return _document(
            '2024', year, week, board_algo, True, champion_map, _pad(slots), [],
        )
    bye_rows = five[:4]
    fifth = five[4]
    others = at_large_rows + [fifth[0]]
    others.sort(key=lambda row: row['rank'])
    slots = []
    for index, (row, _conference) in enumerate(bye_rows, start=1):
        slots.append(_slot(row, 'conference-champion', index, True))
    fifth_name = fifth[0]['team']
    seed = 5
    for row in others:
        bid = 'conference-champion' if row['team'] == fifth_name else 'at-large'
        slots.append(_slot(row, bid, seed, False))
        seed += 1
    slots.sort(key=lambda slot: slot['seed'])
    return _document(
        '2024', year, week, board_algo, False, champion_map, slots, _first_round(slots),
    )


def project_field(
    board: List[Dict[str, Any]],
    champions: Dict[str, Optional[str]],
    ruleset_id: str,
    *,
    year: Optional[int] = None,
    week: Optional[int] = None,
    board_algo: Optional[str] = None,
    champions_final: Optional[bool] = None,
) -> Dict[str, Any]:
    """Twelve slots from an ordered board and an explicit champion map.

    ``champions_final`` False keeps at-large spots empty. A missing champion
    is ``None`` and is never filled from conference wins.
    """
    if year == SEALED_YEAR:
        raise FieldError('2025 is the sealed holdout. Not building a field.')
    if ruleset_id not in ('2024', '2026'):
        raise FieldError(f'unknown ruleset {ruleset_id!r}')
    ranked = _ranked(board, year)
    if ruleset_id == '2026':
        return _project_2026(ranked, champions or {}, year, week, board_algo, champions_final)
    return _project_2024(ranked, champions or {}, year, week, board_algo, champions_final)


def field_from_board(
    board: Dict[str, Any],
    games: List[Dict[str, Any]],
    year: int,
    week: int,
) -> Dict[str, Any]:
    """Project one published week. 2026 can close; 2024 stays open from games alone.

    2024's bid is the five highest champions from any conference. An unplayed
    title game is not in ``games``, so this path does not treat a partial list
    as the final five. A caller with a finished map uses ``project_field``.
    """
    if year == SEALED_YEAR:
        raise FieldError('2025 is the sealed holdout. Not building a field.')
    if year == 2026:
        ruleset_id = '2026'
        found = champions_from_games(games, year)
        champions = {conference: found.get(conference) for conference in POWER_CONFERENCES}
        for conference, name in found.items():
            champions.setdefault(conference, name)
        final = all(isinstance(champions[conference], str) for conference in POWER_CONFERENCES)
    elif year == 2024:
        ruleset_id = '2024'
        champions = champions_from_games(games, year)
        final = False
    else:
        raise FieldError(f'no playoff ruleset for {year}')
    teams = board.get('team_rankings') if isinstance(board, dict) else None
    algo = board.get('algo') if isinstance(board, dict) else None
    return project_field(
        teams or [],
        champions,
        ruleset_id,
        year=year,
        week=week,
        board_algo=algo if isinstance(algo, str) else None,
        champions_final=final,
    )


def write_field_file(year: int, week: int, document: Dict[str, Any], root: Optional[Any] = None):
    """Sibling JSON. Not a week board, and not a committee file."""
    if type(year) is not int or type(week) is not int:
        raise FieldError('year and week must be integers')
    if year == SEALED_YEAR:
        raise FieldError('2025 is the sealed holdout. Not writing a field file.')
    if not isinstance(document, dict) or document.get('kind') != KIND:
        raise FieldError('field file must be a TR+ projection')
    if 'algo' in document or 'committee_rank' in document or 'committee' in document:
        raise FieldError('field file must not carry a board stamp or a committee column')
    return _write_contained(document, year, week, SUFFIX, root, pretty=True)
