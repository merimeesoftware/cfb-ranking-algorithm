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


def test_week_scoped_fetch_calls_api_per_week(mock_client):
    mock_client.get_games.side_effect = lambda year, week=None, season_type='regular': (
        [_make_game(week)] if week else [_make_game(1), _make_game(2)]
    )
    processor = CFBDataProcessor(api_client=mock_client)
    games = processor.get_games_for_season(2024, through_week=3, use_week_scoped_fetch=True)
    assert len(games) >= 3
    assert mock_client.get_games.call_count >= 3


def test_get_available_weeks(mock_client):
    mock_client.get_games.return_value = [_make_game(1), _make_game(2), _make_game(2)]
    processor = CFBDataProcessor(api_client=mock_client)
    weeks = processor.get_available_weeks(2024)
    assert weeks == [1, 2]
