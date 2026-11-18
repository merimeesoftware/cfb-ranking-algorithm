"""Regenerating a week is byte-identical. Equal Elo breaks by team name."""
import json

from algo_lab.runner import rank_through_week
from ranking_service import publish_order


def test_ties_break_by_team_name():
    ordered = publish_order({
        'team_rankings': [
            {'team_name': 'Zed', 'team_quality_score': 1500.0},
            {'team_name': 'Amy', 'team_quality_score': 1500.0},
            {'team_name': 'Mia', 'team_quality_score': 1600.0},
        ],
    })['team_rankings']
    assert [team['team_name'] for team in ordered] == ['Mia', 'Amy', 'Zed']


def test_regenerating_a_week_is_byte_identical():
    games = [
        {
            'year': 2024, 'week': 1,
            'home_team_name': 'Alpha', 'away_team_name': 'Beta',
            'home_score': 28, 'away_score': 14,
            'home_conference': 'SEC', 'away_conference': 'Big Ten',
            'home_conference_type': 'Power 4', 'away_conference_type': 'Power 4',
            'notes': '', 'season_type': 'regular', 'neutral_site': False,
        },
        {
            'year': 2024, 'week': 1,
            'home_team_name': 'Gamma', 'away_team_name': 'Delta',
            'home_score': 21, 'away_score': 17,
            'home_conference': 'Sun Belt', 'away_conference': 'MAC',
            'home_conference_type': 'Group of 5', 'away_conference_type': 'Group of 5',
            'notes': '', 'season_type': 'regular', 'neutral_site': False,
        },
    ]
    first, _ranker = rank_through_week(games, 1)
    second, _ranker = rank_through_week(games, 1)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    names = [team['team_name'] for team in first['team_rankings']]
    assert names == sorted(names, key=lambda name: (
        -next(team['team_quality_score'] for team in first['team_rankings'] if team['team_name'] == name),
        name,
    ))
