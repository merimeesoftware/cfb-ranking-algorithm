"""Tests for Flask API routes."""
import os
from unittest.mock import patch

import pytest

os.environ.setdefault('CFBD_API_KEY', 'test-key-for-unit-tests')


@pytest.fixture
def client():
    with patch('data_processor.CFBDataProcessor._initialize_conference_map'):
        from app import app
        app.config['TESTING'] = True
        with app.test_client() as c:
            yield c


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


def test_rankings_cached(client):
    mock_data = {
        'team_rankings': [{'team_name': 'Georgia', 'final_ranking_score': 95}],
        'conference_rankings': [],
        'year': 2024,
        'week': 10,
    }
    with patch('app.get_or_calculate_rankings', return_value=mock_data):
        response = client.get('/rankings?year=2024&week=10')
        assert response.status_code == 200
        data = response.get_json()
        assert data['team_rankings'][0]['team_name'] == 'Georgia'


def test_agent_health(client):
    response = client.get('/agent/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'ok'


def test_cache_clear_requires_secret(client):
    response = client.post('/cache/clear')
    assert response.status_code == 403
