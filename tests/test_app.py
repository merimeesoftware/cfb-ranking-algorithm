"""Tests for Flask API routes."""
import os
from unittest.mock import patch

import pytest

os.environ.setdefault('CFBD_API_KEY', 'test-key-for-unit-tests')


def test_index(client):
    response = client.get('/')
    assert response.status_code == 200
    data = response.get_json()
    assert 'True Rankings' in data['message']
    assert data.get('rating') == 'TR+'
    catalog = response.get_data(as_text=True)
    assert '/cache/clear' not in catalog
    assert '/cache/stats' not in catalog
    assert '/drop/subscribe' not in catalog
    assert '/agent/health' not in catalog


def test_cors_allowlist_has_no_wildcard_or_credentials(client, monkeypatch):
    monkeypatch.delenv('CORS_ORIGINS', raising=False)
    unset = client.get('/', headers={'Origin': 'https://evil.example'})
    assert 'Access-Control-Allow-Origin' not in unset.headers
    assert 'Access-Control-Allow-Credentials' not in unset.headers

    monkeypatch.setenv('CORS_ORIGINS', '*')
    wildcard = client.get('/', headers={'Origin': 'https://evil.example'})
    assert 'Access-Control-Allow-Origin' not in wildcard.headers
    assert 'Access-Control-Allow-Credentials' not in wildcard.headers

    monkeypatch.setenv('CORS_ORIGINS', 'https://board.example.test, *')
    denied = client.get('/', headers={'Origin': 'https://evil.example'})
    assert 'Access-Control-Allow-Origin' not in denied.headers
    allowed = client.get('/', headers={'Origin': 'https://board.example.test'})
    assert allowed.headers['Access-Control-Allow-Origin'] == 'https://board.example.test'
    assert 'Access-Control-Allow-Credentials' not in allowed.headers
    preflight = client.options('/', headers={
        'Origin': 'https://board.example.test',
        'Access-Control-Request-Method': 'POST',
    })
    assert preflight.status_code == 204
    assert preflight.headers['Access-Control-Allow-Origin'] == 'https://board.example.test'
    assert 'cf-turnstile-response' in preflight.headers['Access-Control-Allow-Headers']
    assert 'Access-Control-Allow-Credentials' not in preflight.headers


def test_mcp_query_route_is_gone(client):
    response = client.post('/agent/mcp/query', json={'tool': 'get-games', 'params': {'year': 2024}})
    assert response.status_code == 404
    body = response.get_data(as_text=True)
    assert 'MCP query failed' not in body
    assert 'CFBD_MCP_URL' not in body


def test_weeks_endpoint(client):
    with patch('app.data_processor') as mock_dp:
        mock_dp.get_available_weeks.side_effect = AssertionError('weeks must not call CFBD')
        response = client.get('/weeks?year=2024')
        assert response.status_code == 200
        data = response.get_json()
        assert data['weeks'] == list(range(1, 16))
        assert data['max_week'] == 15
        assert data['published'] is True
        mock_dp.get_available_weeks.assert_not_called()


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
        assert response.status_code == 400
        data = response.get_json()
        assert data['code'] == 'formula_params'


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


def test_cache_clear_requires_secret(client, monkeypatch):
    response = client.post('/cache/clear')
    assert response.status_code == 403
    monkeypatch.setenv('CACHE_CLEAR_SECRET', 'clear-test')
    query = client.post('/cache/clear?secret=clear-test')
    assert query.status_code == 401
    body = client.post('/cache/clear', json={'secret': 'clear-test'})
    assert body.status_code == 401
    ok = client.post('/cache/clear', headers={'X-Cache-Secret': 'clear-test'})
    assert ok.status_code == 200
    non_ascii = client.post('/cache/clear', headers={'X-Cache-Secret': 'caf\u00e9'})
    assert non_ascii.status_code == 401
    monkeypatch.setenv('CACHE_CLEAR_SECRET', 'cle\u00e1r')
    matched = client.post('/cache/clear', headers={'X-Cache-Secret': 'cle\u00e1r'})
    assert matched.status_code == 200
