"""12-team TR+ projection. Synthetic boards and sidecar rows. No CFBD and no 2025."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

import precompute_rankings as pre
from playoff_field import (
    RULES_SOURCE,
    FieldError,
    champions_from_games,
    field_from_board,
    project_field,
    write_field_file,
)
from ranking_service import ALGO_VERSION
from static_rankings import rebuild_rankings_manifest, write_static_rankings

BANNED = {
    'algo',
    'committee',
    'committee_rank',
    'poll',
    'site',
    'stadium',
    'favorite',
    'odds',
    'pick',
    'spread',
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


def _teams(*rows):
    teams = []
    for name, conference, conf_wins in rows:
        teams.append({
            'team_name': name,
            'conference': conference,
            'records': {'conf_wins': conf_wins, 'conf_losses': 0, 'total_wins': conf_wins, 'total_losses': 0},
        })
    return teams


def _title(conference, home, away, notes, season_type='regular', home_score=24, away_score=10):
    return {
        'week': 14,
        'home': home,
        'away': away,
        'home_score': home_score,
        'away_score': away_score,
        'season_type': season_type,
        'notes': notes,
        'neutral_site': True,
        'home_conference': conference,
        'away_conference': conference,
    }


FULL_2026 = _teams(
    ('Oregon', 'Big Ten', 9),
    ('Georgia', 'SEC', 6),
    ('Ohio State', 'Big Ten', 7),
    ('Texas', 'SEC', 8),
    ('Clemson', 'ACC', 7),
    ('Indiana', 'Big Ten', 8),
    ('Penn State', 'Big Ten', 7),
    ('Alabama', 'SEC', 5),
    ('Ole Miss', 'SEC', 5),
    ('Miami', 'ACC', 6),
    ('SMU', 'ACC', 8),
    ('Notre Dame', 'FBS Independents', 0),
    ('Arizona State', 'Big 12', 7),
    ('Boise State', 'Pac-12', 7),
    ('Toledo', 'Mid-American', 8),
    ('UConn', 'American Athletic', 0),
)

CHAMPS_2026 = {
    'Big Ten': 'Oregon',
    'SEC': 'Georgia',
    'ACC': 'Clemson',
    'Big 12': 'Arizona State',
    'Mid-American': 'Toledo',
}


def test_rules_are_cited_and_2025_is_refused():
    assert 'ncaa.com' in RULES_SOURCE
    assert '2026-08-11' in RULES_SOURCE
    try:
        project_field([], {}, '2026', year=2025)
    except FieldError as exc:
        assert '2025' in str(exc)
    else:
        raise AssertionError('2025 field should be refused')
    try:
        champions_from_games([], 2025)
    except FieldError as exc:
        assert '2025' in str(exc)
    else:
        raise AssertionError('2025 games should be refused')


def test_2026_inserts_a_power_champion_outside_the_top_12_and_not_uconn():
    field = project_field(FULL_2026, CHAMPS_2026, '2026', year=2026, week=14, board_algo=ALGO_VERSION)
    assert field['kind'] == 'tr-plus-field'
    assert field['projection'] == 'TR+'
    assert field['ruleset_id'] == '2026'
    assert field['board_algo'] == ALGO_VERSION
    assert 'algo' not in field
    assert field['incomplete'] is False
    assert field['as_of'] == {'year': 2026, 'week': 14}
    by_team = {slot['team']: slot for slot in field['slots']}
    assert set(by_team) == {
        'Oregon', 'Georgia', 'Ohio State', 'Texas', 'Clemson', 'Indiana',
        'Penn State', 'Alabama', 'Ole Miss', 'Notre Dame', 'Arizona State', 'Boise State',
    }
    assert by_team['Arizona State']['bid'] == 'power-conference-champion'
    assert by_team['Arizona State']['bye'] is False
    assert by_team['Arizona State']['rank'] == 13
    assert by_team['Boise State']['bid'] == 'group-of-six-highest-ranked'
    assert by_team['Boise State']['conference'] == 'Pac-12'
    assert by_team['Notre Dame']['bid'] == 'notre-dame-top-12'
    assert by_team['Oregon']['bye'] is True
    assert by_team['Texas']['seed'] == 4
    assert by_team['Texas']['bye'] is True
    assert 'UConn' not in by_team
    assert 'Miami' not in by_team
    assert [slot['seed'] for slot in field['slots']] == list(range(1, 13))
    pairs = [(row['higher_seed'], row['lower_seed']) for row in field['first_round']]
    assert pairs == [(5, 12), (6, 11), (7, 10), (8, 9)]
    assert field['first_round'][0]['higher_team'] == 'Clemson'
    assert field['first_round'][0]['lower_team'] == 'Boise State'
    assert BANNED.isdisjoint(_keys(field))


def test_notre_dame_at_12_is_in_and_at_13_is_out():
    inside = project_field(FULL_2026, CHAMPS_2026, '2026', year=2026)
    assert any(slot['team'] == 'Notre Dame' and slot['rank'] == 12 for slot in inside['slots'])

    outside_rows = _teams(
        ('Oregon', 'Big Ten', 9),
        ('Georgia', 'SEC', 6),
        ('Ohio State', 'Big Ten', 7),
        ('Texas', 'SEC', 8),
        ('Clemson', 'ACC', 7),
        ('Arizona State', 'Big 12', 7),
        ('Indiana', 'Big Ten', 8),
        ('Boise State', 'Pac-12', 7),
        ('Penn State', 'Big Ten', 7),
        ('Alabama', 'SEC', 5),
        ('Ole Miss', 'SEC', 5),
        ('Miami', 'ACC', 6),
        ('Notre Dame', 'FBS Independents', 0),
        ('SMU', 'ACC', 8),
        ('Toledo', 'Mid-American', 8),
        ('UConn', 'FBS Independents', 0),
    )
    outside = project_field(outside_rows, CHAMPS_2026, '2026', year=2026)
    assert outside['incomplete'] is False
    assert all(slot['team'] != 'Notre Dame' for slot in outside['slots'])


def test_group_of_six_bid_is_the_highest_ranked_team_not_the_champion():
    field = project_field(FULL_2026, CHAMPS_2026, '2026', year=2026)
    bids = {slot['team']: slot['bid'] for slot in field['slots']}
    assert bids['Boise State'] == 'group-of-six-highest-ranked'
    assert 'Toledo' not in bids


def test_uconn_board_label_does_not_take_the_group_of_six_bid():
    rows = _teams(
        ('UConn', 'American Athletic', 12),
        ('Oregon', 'Big Ten', 0),
        ('Georgia', 'SEC', 0),
        ('Clemson', 'ACC', 0),
        ('Arizona State', 'Big 12', 0),
        ('Boise State', 'Mountain West', 0),
        ('Ohio State', 'Big Ten', 0),
        ('Texas', 'SEC', 0),
        ('Indiana', 'Big Ten', 0),
        ('Penn State', 'Big Ten', 0),
        ('Alabama', 'SEC', 0),
        ('Ole Miss', 'SEC', 0),
        ('Miami', 'ACC', 0),
        ('SMU', 'ACC', 0),
        ('Notre Dame', 'FBS Independents', 0),
        ('Toledo', 'MAC', 0),
    )
    field = project_field(rows, CHAMPS_2026, '2026', year=2026)
    bids = {slot['team']: slot['bid'] for slot in field['slots']}
    assert bids.get('UConn') != 'group-of-six-highest-ranked'
    assert 'UConn' not in bids or bids['UConn'] == 'at-large'
    assert bids['Boise State'] == 'group-of-six-highest-ranked'


def test_missing_champion_leaves_the_field_incomplete_and_ignores_conf_wins():
    champs = dict(CHAMPS_2026)
    champs['SEC'] = None
    field = project_field(FULL_2026, champs, '2026', year=2026, week=10)
    assert field['incomplete'] is True
    assert field['first_round'] == []
    assert field['champion_map']['SEC'] is None
    sec = [
        slot for slot in field['slots']
        if slot['conference'] == 'SEC' and slot['bid'] == 'power-conference-champion'
    ]
    assert sec == [{
        'seed': None,
        'team': None,
        'rank': None,
        'conference': 'SEC',
        'bid': 'power-conference-champion',
        'bye': None,
    }]
    filled = [slot['team'] for slot in field['slots'] if slot['team']]
    assert 'Texas' not in filled
    assert 'Georgia' not in filled


def test_2024_byes_go_to_the_four_highest_champions_not_the_highest_teams():
    rows = _teams(
        ('Ohio State', 'Big Ten', 7),
        ('Oregon', 'Big Ten', 9),
        ('Georgia', 'SEC', 6),
        ('Clemson', 'ACC', 7),
        ('Arizona State', 'Big 12', 7),
        ('Texas', 'SEC', 8),
        ('Indiana', 'Big Ten', 8),
        ('Penn State', 'Big Ten', 7),
        ('Alabama', 'SEC', 5),
        ('Ole Miss', 'SEC', 5),
        ('Miami', 'ACC', 6),
        ('SMU', 'ACC', 8),
        ('Notre Dame', 'FBS Independents', 0),
        ('Oregon State', 'Pac-12', 1),
        ('Boise State', 'Mountain West', 7),
        ('Army', 'American Athletic', 8),
    )
    champs = {
        'Big Ten': 'Oregon',
        'SEC': 'Georgia',
        'ACC': 'Clemson',
        'Big 12': 'Arizona State',
        'Pac-12': 'Oregon State',
        'Mountain West': 'Boise State',
    }
    field = project_field(
        rows, champs, '2024', year=2024, week=14, champions_final=True, board_algo=ALGO_VERSION,
    )
    assert field['incomplete'] is False
    by_team = {slot['team']: slot for slot in field['slots']}
    assert by_team['Ohio State']['seed'] == 5
    assert by_team['Ohio State']['bye'] is False
    assert by_team['Ohio State']['bid'] == 'at-large'
    assert [by_team[name]['seed'] for name in ('Oregon', 'Georgia', 'Clemson', 'Arizona State')] == [1, 2, 3, 4]
    assert all(by_team[name]['bye'] is True for name in ('Oregon', 'Georgia', 'Clemson', 'Arizona State'))
    assert by_team['Oregon State']['bid'] == 'conference-champion'
    assert by_team['Oregon State']['bye'] is False
    assert 'Boise State' not in by_team
    assert BANNED.isdisjoint(_keys(field))


def test_2024_partial_games_do_not_guess_the_five():
    games = [
        _title('SEC', 'Georgia', 'Texas', 'SEC Championship'),
        _title('Big Ten', 'Oregon', 'Penn State', 'Big Ten Championship'),
    ]
    found = champions_from_games(games, 2024)
    assert found == {'SEC': 'Georgia', 'Big Ten': 'Oregon'}
    board = {'algo': ALGO_VERSION, 'team_rankings': FULL_2026}
    field = field_from_board(board, games, 2024, 14)
    assert field['incomplete'] is True
    assert field['first_round'] == []
    assert field['champion_map']['SEC'] == 'Georgia'
    assert all(slot['seed'] is None for slot in field['slots'])


def test_title_game_reader_does_not_reuse_the_ranker_championship_check():
    games = [
        _title('SEC', 'Georgia', 'Texas', 'championship'),
        _title('Big Ten', 'Oregon', 'Penn State', 'Big Ten Championship', season_type='postseason'),
        _title('ACC', 'Clemson', 'SMU', 'ACC Championship', home_score=17, away_score=17),
        _title('Big 12', 'Arizona State', 'Iowa State', 'Big 12 Championship'),
        _title('Big 12', 'Arizona State', 'Iowa State', 'Big 12 Championship Game', home_score=10, away_score=7),
        _title('Mid-American', 'Toledo', 'Miami (OH)', 'MAC Championship'),
    ]
    found = champions_from_games(games, 2026)
    assert 'SEC' not in found
    assert 'Big Ten' not in found
    assert found['ACC'] is None
    assert found['Big 12'] is None
    assert found['Mid-American'] == 'Toledo'


def test_field_file_is_not_a_week_board(tmp_path):
    import check_board_stamps as stamps

    week = tmp_path / '2026'
    week.mkdir()
    (week / 'week-10.json').write_text(
        json.dumps({'year': 2026, 'week': 10, 'algo': ALGO_VERSION, 'team_rankings': []}),
        encoding='utf-8',
    )
    document = project_field(FULL_2026, CHAMPS_2026, '2026', year=2026, week=10, board_algo=ALGO_VERSION)
    path = write_field_file(2026, 10, document, tmp_path)
    assert path.name == 'week-10.field.json'
    assert stamps.board_stamp_errors(tmp_path) == []
    assert rebuild_rankings_manifest(tmp_path)['years']['2026'] == [10]
    try:
        write_field_file(2025, 1, document, tmp_path)
    except FieldError as exc:
        assert '2025' in str(exc)
    else:
        raise AssertionError('2025 field write should be refused')


def test_publish_field_reads_the_games_sidecar_and_does_not_fetch(tmp_path, monkeypatch):
    calls = []

    class Processor:
        class api_client:
            @staticmethod
            def get_games(**kwargs):
                calls.append(kwargs)
                raise AssertionError('CFBD fetch')

    def fake_precompute(year, week, _processor, **kwargs):
        return write_static_rankings(
            {'year': year, 'week': week, 'algo': ALGO_VERSION, 'team_rankings': FULL_2026},
            year,
            week,
            root=kwargs.get('output_root') or tmp_path,
        )

    monkeypatch.setattr(pre, 'precompute', fake_precompute)
    games = [
        _title('SEC', 'Georgia', 'Texas', 'SEC Championship'),
        _title('Big Ten', 'Oregon', 'Penn State', 'Big Ten Championship'),
        _title('ACC', 'Clemson', 'SMU', 'ACC Championship'),
        _title('Big 12', 'Arizona State', 'Iowa State', 'Big 12 Championship'),
        {
            'week': 1,
            'home': 'Georgia',
            'away': 'Texas',
            'home_score': None,
            'away_score': None,
            'season_type': 'regular',
            'notes': 'SEC Championship',
        },
    ]
    result = pre.publish_year(
        2026,
        [14],
        Processor(),
        static_root=tmp_path,
        season_games=games,
    )
    assert result['bulk_calls'] == 0
    assert calls == []
    field = json.loads((tmp_path / '2026' / 'week-14.field.json').read_text(encoding='utf-8'))
    assert field['kind'] == 'tr-plus-field'
    assert field['incomplete'] is False
    assert field['champion_map']['SEC'] == 'Georgia'
    assert 'algo' not in field
    assert 'committee_rank' not in _keys(field)
    sidecar = json.loads((tmp_path / '2026' / 'week-14.games.json').read_text(encoding='utf-8'))
    assert sidecar['kind'] == 'games'
    assert all(row['home_score'] is not None for row in sidecar['games'])


def test_week_14_and_week_15_files_are_not_the_selection_board():
    """Published week 14 is before championship weekend. Week 15 includes the postseason.

    Neither file is a selection-day board. This test does not build a field from them
    and does not read the sealed 2025 prior.
    """
    folder = ROOT / 'frontend' / 'static' / 'rankings' / '2024'
    early = json.loads((folder / 'week-14.json').read_text(encoding='utf-8'))
    late = json.loads((folder / 'week-15.json').read_text(encoding='utf-8'))

    def wins(payload, name):
        for team in payload['team_rankings']:
            if team['team_name'] == name:
                return team['records']['total_wins']
        raise AssertionError(name)

    assert wins(late, 'Oregon') > wins(early, 'Oregon')
    assert not (folder / 'week-14.field.json').exists()
    assert not (folder / 'week-15.field.json').exists()
