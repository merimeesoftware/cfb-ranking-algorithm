"""Tests for CFBD game transform integrity fields."""
from api_integration import CFBDApiClient


def test_transform_preserves_notes_and_season_type():
    raw = {
        'week': 15,
        'season': 2024,
        'homeTeam': 'Oregon',
        'awayTeam': 'Penn State',
        'homePoints': 45,
        'awayPoints': 37,
        'homeConference': 'Big Ten',
        'awayConference': 'Big Ten',
        'venue': 'Rose Bowl',
        'startDate': '2025-01-01T00:00:00.000Z',
        'notes': 'CFP Semifinal - Rose Bowl',
        'seasonType': 'postseason',
        'neutralSite': True,
    }
    out = CFBDApiClient._transform_game(None, raw)
    assert out['notes'] == 'CFP Semifinal - Rose Bowl'
    assert out['season_type'] == 'postseason'
    assert out['neutral_site'] is True
    assert out['home_team_name'] == 'Oregon'


def test_transform_defaults_missing_notes():
    raw = {
        'week': 1,
        'season': 2024,
        'homeTeam': 'A',
        'awayTeam': 'B',
        'homePoints': 10,
        'awayPoints': 7,
        'homeConference': 'SEC',
        'awayConference': 'SEC',
    }
    out = CFBDApiClient._transform_game(None, raw)
    assert out['notes'] == ''
    assert out['season_type'] == 'regular'
    assert out['neutral_site'] is False
