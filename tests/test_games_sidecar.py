"""Games sidecar writer. Fixtures only. No CFBD and no 2025 board."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

import precompute_rankings as pre
from games_sidecar import (
    GamesSidecarError,
    read_games_sidecar,
    write_games_sidecar,
)
from static_rankings import rebuild_rankings_manifest

BANNED = {
    'algo',
    'implied_spread',
    'market_spread',
    'favorite',
    'delta',
    'odds',
    'pick',
    'spread',
    'line',
    'win_probability',
    'win_chance',
    'expected_winner',
}


def _keys(value):
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            found.append(key)
            found.extend(_keys(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_keys(item))
    return found


def _game(**overrides):
    row = {
        'week': 3,
        'home_team_name': 'Oregon',
        'away_team_name': 'Ohio State',
        'home_score': 24,
        'away_score': 21,
        'neutral_site': False,
        'season_type': 'regular',
        'home_conference': 'Big Ten',
        'away_conference': 'Big Ten',
        'notes': '',
        'completed': True,
    }
    row.update(overrides)
    return row


def test_writer_schema_has_no_board_stamp_or_pick(tmp_path):
    path = write_games_sidecar(2024, 10, [
        _game(),
        _game(week=1, home_score=None, away_score=None),
        _game(week=7, spread=3.5, odds='-110', pick='Oregon', line=3.5),
        _game(week=2, home_team_name='Oregon', away_team_name='Ohio State', home_score=14, away_score=17),
        _game(week=4, completed=False, home_score=10, away_score=7),
        _game(
            week=5,
            neutral_site=False,
            notes='SEC Championship',
            season_type='regular',
            home_team_name='Georgia',
            away_team_name='Texas',
        ),
    ], root=tmp_path)
    assert path.name == 'week-10.games.json'
    payload = json.loads(path.read_text(encoding='utf-8'))
    assert payload['schema'] == 1
    assert payload['kind'] == 'games'
    assert payload['year'] == 2024
    assert payload['week'] == 10
    assert 'algo' not in payload
    assert BANNED.isdisjoint(_keys(payload))
    weeks = [row['week'] for row in payload['games']]
    assert weeks == [2, 3, 5, 7]
    assert all('spread' not in row and 'odds' not in row and 'pick' not in row for row in payload['games'])
    title = next(row for row in payload['games'] if row['week'] == 5)
    assert title['season_type'] == 'regular'
    assert title['neutral_site'] is False
    assert title['notes'] == 'SEC Championship'
    loaded = read_games_sidecar(2024, 10, root=tmp_path)
    assert loaded['present'] is True
    assert len(loaded['games']) == 4


def test_two_meetings_and_miami_names_stay_distinct(tmp_path):
    write_games_sidecar(2024, 8, [
        _game(week=1, home_team_name='Miami', away_team_name='Florida'),
        _game(week=2, home_team_name='Miami (OH)', away_team_name='Ohio'),
        _game(week=6, home_team_name='Florida', away_team_name='Miami', home_score=10, away_score=20),
    ], root=tmp_path)
    games = read_games_sidecar(2024, 8, root=tmp_path)['games']
    names = {(row['home'], row['away']) for row in games}
    assert ('Miami', 'Florida') in names
    assert ('Florida', 'Miami') in names
    assert ('Miami (OH)', 'Ohio') in names
    assert len(games) == 3


def test_missing_sidecar_is_empty_and_2025_is_refused(tmp_path):
    assert read_games_sidecar(2024, 3, root=tmp_path) == {
        'present': False,
        'year': 2024,
        'week': 3,
        'games': [],
    }
    planted = tmp_path / '2025'
    planted.mkdir()
    (planted / 'week-1.games.json').write_text(
        json.dumps({'schema': 1, 'kind': 'games', 'year': 2025, 'week': 1, 'games': [{'home': 'A'}]}),
        encoding='utf-8',
    )
    assert read_games_sidecar(2025, 1, root=tmp_path)['present'] is False
    assert read_games_sidecar(2025, 1, root=tmp_path)['games'] == []
    try:
        write_games_sidecar(2025, 1, [_game()], root=tmp_path)
    except GamesSidecarError as exc:
        assert '2025' in str(exc)
    else:
        raise AssertionError('2025 sidecar write should be refused')
    assert list(planted.glob('week-1.games.json')) == [planted / 'week-1.games.json']
    assert 'Oregon' not in (planted / 'week-1.games.json').read_text(encoding='utf-8')


def test_postseason_rows_wait_for_week_15(tmp_path):
    games = [
        _game(week=1),
        _game(week=1, season_type='postseason', home_team_name='Alabama', away_team_name='Michigan'),
    ]
    write_games_sidecar(2024, 10, games, root=tmp_path)
    early = read_games_sidecar(2024, 10, root=tmp_path)['games']
    assert [row['home'] for row in early] == ['Oregon']
    write_games_sidecar(2024, 15, games, root=tmp_path)
    late = read_games_sidecar(2024, 15, root=tmp_path)['games']
    assert {row['season_type'] for row in late} == {'regular', 'postseason'}


def test_sidecar_is_not_a_week_board(tmp_path):
    import check_board_stamps as stamps

    week = tmp_path / '2024'
    week.mkdir()
    (week / 'week-1.json').write_text(
        json.dumps({'year': 2024, 'week': 1, 'algo': 'v5.5', 'team_rankings': []}),
        encoding='utf-8',
    )
    write_games_sidecar(2024, 1, [_game(week=1)], root=tmp_path)
    assert stamps.board_stamp_errors(tmp_path) == []
    manifest = rebuild_rankings_manifest(tmp_path)
    assert manifest['years']['2024'] == [1]


def test_publish_writes_sidecar_from_memory_without_a_fetch(tmp_path, monkeypatch):
    calls = []

    class Processor:
        class api_client:
            @staticmethod
            def get_games(**kwargs):
                calls.append(kwargs)
                raise AssertionError('CFBD fetch')

    monkeypatch.setattr(pre, 'precompute', lambda *args, **kwargs: tmp_path / 'unused.json')
    games = [_game(week=1), _game(week=2, home_score=None, away_score=None)]
    result = pre.publish_year(
        2024,
        [1],
        Processor(),
        static_root=tmp_path,
        season_games=games,
    )
    assert result['bulk_calls'] == 0
    assert calls == []
    payload = json.loads((tmp_path / '2024' / 'week-1.games.json').read_text(encoding='utf-8'))
    assert payload['kind'] == 'games'
    assert 'algo' not in payload
    assert len(payload['games']) == 1
    assert payload['games'][0]['away'] == 'Ohio State'
