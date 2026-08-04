"""Tests for Flask API routes."""
import os
from unittest.mock import patch

import pytest

os.environ.setdefault('CFBD_API_KEY', 'test-key-for-unit-tests')


def test_index(client):
    response = client.get('/')
    assert response.status_code == 200
    data = response.get_json()
    assert 'CFB Ranking API' in data['message']


def test_weeks_endpoint(client):
    with patch('app.data_processor') as mock_dp:
        mock_dp.get_available_weeks.return_value = [1, 2, 3, 4, 5]
        response = client.get('/weeks?year=2024')
        assert response.status_code == 200
        data = response.get_json()
        assert data['weeks'] == [1, 2, 3, 4, 5]
        assert data['max_week'] == 5


def test_rankings_slim_by_default(client):
    mock_data = {
        'team_rankings': [{
            'team_name': 'Georgia',
            'final_ranking_score': 95,
            'wins_details': [{'opponent': 'X'}],
            'losses_details': [],
        }],
        'conference_rankings': [],
        'year': 2024,
        'week': 10,
        'rankings': {'Georgia': {}},
    }
    with patch('app.get_or_calculate_rankings', return_value=mock_data):
        response = client.get('/rankings?year=2024&week=10')
        assert response.status_code == 200
        data = response.get_json()
        assert 'rankings' not in data
        assert 'wins_details' not in data['team_rankings'][0]
        assert data['detail'] is False


def test_rankings_detail_preserves_wins_details(client):
    mock_data = {
        'team_rankings': [{
            'team_name': 'Georgia',
            'final_ranking_score': 95,
            'wins_details': [{'opponent': 'X', 'is_quality_win': True}],
            'losses_details': [],
        }],
        'conference_rankings': [],
        'year': 2024,
        'week': 10,
        'rankings': {'Georgia': {}},
    }
    with patch('app.get_or_calculate_rankings', return_value=mock_data):
        response = client.get('/rankings?year=2024&week=10&detail=true')
        assert response.status_code == 200
        data = response.get_json()
        assert data['team_rankings'][0]['wins_details'][0]['opponent'] == 'X'
        assert 'rankings' not in data


def test_team_breakdown_includes_game_details(client):
    mock_data = {
        'team_rankings': [{
            'team_name': 'Georgia',
            'conference': 'SEC',
            'conference_type': 'Power 4',
            'final_ranking_score': 100,
            'team_quality_score': 1500,
            'record_score': 100,
            'conference_quality_score': 50,
            'sos': 1400,
            'sov': 1450,
            'records': {
                'total_wins': 10, 'total_losses': 1,
                'conf_wins': 7, 'conf_losses': 1,
                'power_wins': 5, 'power_losses': 1,
                'group_five_wins': 2, 'group_five_losses': 0,
            },
            'wins_details': [{'opponent': 'Florida', 'is_quality_win': True}],
            'losses_details': [{'opponent': 'Alabama', 'is_bad_loss': False}],
        }],
        'conference_rankings': [],
        'year': 2024,
        'week': 10,
    }
    with patch('app.get_or_calculate_rankings', return_value=mock_data):
        response = client.get('/rankings/team/Georgia?year=2024&week=10')
        assert response.status_code == 200
        data = response.get_json()
        assert data['team']['name'] == 'Georgia'
        assert data['wins_details'][0]['opponent'] == 'Florida'
        assert data['losses_details'][0]['opponent'] == 'Alabama'
        assert 'path_to_climb' in data
        assert data['path_to_climb']['at_top'] is True
        assert 'summary' in data['path_to_climb']


def test_team_breakdown_path_to_climb_vs_team_above(client):
    mock_data = {
        'team_rankings': [
            {
                'team_name': 'Oregon',
                'conference': 'Big Ten',
                'conference_type': 'Power 4',
                'final_ranking_score': 100,
                'team_quality_score': 1900,
                'record_score': 95,
                'conference_quality_score': 90,
                'sos': 0.6,
                'sov': 0.65,
                'records': {
                    'total_wins': 9, 'total_losses': 0,
                    'conf_wins': 6, 'conf_losses': 0,
                    'power_wins': 7, 'power_losses': 0,
                    'group_five_wins': 2, 'group_five_losses': 0,
                },
                'wins_details': [],
                'losses_details': [],
            },
            {
                'team_name': 'Ohio State',
                'conference': 'Big Ten',
                'conference_type': 'Power 4',
                'final_ranking_score': 95,
                'team_quality_score': 1850,
                'record_score': 90,
                'conference_quality_score': 90,
                'sos': 0.58,
                'sov': 0.6,
                'records': {
                    'total_wins': 8, 'total_losses': 1,
                    'conf_wins': 5, 'conf_losses': 1,
                    'power_wins': 6, 'power_losses': 1,
                    'group_five_wins': 2, 'group_five_losses': 0,
                },
                'wins_details': [],
                'losses_details': [],
            },
        ],
        'conference_rankings': [],
        'year': 2024,
        'week': 10,
    }
    with patch('app.get_or_calculate_rankings', return_value=mock_data):
        response = client.get('/rankings/team/Ohio%20State?year=2024&week=10')
        assert response.status_code == 200
        data = response.get_json()
        path = data['path_to_climb']
        assert path['at_top'] is False
        assert path['team_above'] == 'Oregon'
        assert path['score_gap'] == 5.0
        assert path['summary']


def test_agent_health(client):
    response = client.get('/agent/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'ok'


def test_cache_clear_requires_secret(client):
    response = client.post('/cache/clear')
    assert response.status_code == 403
