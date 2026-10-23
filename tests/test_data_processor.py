"""Tests for data processor week-scoped fetching."""
from unittest.mock import MagicMock, patch

import pytest

from data_processor import CFBDataProcessor


def _make_game(week, home='TeamA', away='TeamB'):
    return {
        'week': week,
        'year': 2024,
        'home_team_name': home,
        'away_team_name': away,
        'home_score': 21,
        'away_score': 14,
        'home_conference': 'SEC',
        'away_conference': 'ACC',
        'home_conference_type': 'Power 4',
        'away_conference_type': 'Power 4',
    }


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.get_teams_with_logos.return_value = {
        'TeamA': {'conference': 'SEC', 'logos': []},
        'TeamB': {'conference': 'ACC', 'logos': []},
    }
    return client


def test_bulk_season_fetch_is_one_call(mock_client):
    def _games(year, week=None, season_type='regular'):
        assert week is None
        assert season_type == 'both'
        return [
            _make_game(1),
            _make_game(2),
            _make_game(3),
            {**_make_game(1, home='BowlA', away='BowlB'), 'season_type': 'postseason', 'week': 1},
        ]

    mock_client.get_games.side_effect = _games
    processor = CFBDataProcessor(api_client=mock_client)
    games = processor.get_games_for_season(2024, through_week=3, use_week_scoped_fetch=True)
    assert mock_client.get_games.call_count == 1
    assert {g['week'] for g in games} == {1, 2, 3}
    assert all(g.get('season_type') != 'postseason' for g in games)


def test_bulk_includes_postseason_from_week_15(mock_client):
    mock_client.get_games.return_value = [
        _make_game(15),
        {**_make_game(1, home='BowlA', away='BowlB'), 'season_type': 'postseason'},
    ]
    processor = CFBDataProcessor(api_client=mock_client)
    games = processor.get_games_for_season(2024, through_week=15)
    assert mock_client.get_games.call_count == 1
    assert any(g.get('season_type') == 'postseason' for g in games)


def test_get_available_weeks(mock_client):
    mock_client.get_games.return_value = [_make_game(1), _make_game(2), _make_game(2)]
    processor = CFBDataProcessor(api_client=mock_client)
    weeks = processor.get_available_weeks(2024)
    assert weeks == [1, 2]


def test_scored_but_incomplete_rows_are_excluded(mock_client):
    processor = CFBDataProcessor(api_client=mock_client)
    games = [
        {
            **_make_game(1, home='BowlA', away='BowlB'),
            'season_type': 'postseason',
            'completed': False,
            'home_score': 31,
            'away_score': 28,
        },
        {**_make_game(1), 'completed': True},
    ]
    kept = processor._process_raw_games(games)
    assert [game['home_team_name'] for game in kept] == ['TeamA']


def test_cfbd_error_is_not_an_empty_season(mock_client):
    from api_integration import CFBDRequestError

    mock_client.get_games.side_effect = CFBDRequestError('CFBD request failed')
    processor = CFBDataProcessor(api_client=mock_client)
    with pytest.raises(CFBDRequestError):
        processor.get_games_for_season(2024, through_week=2)
