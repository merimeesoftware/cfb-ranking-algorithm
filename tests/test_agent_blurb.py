"""API tests for shareable team blurbs."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

FIXTURES = Path(__file__).parent / 'fixtures'


@pytest.fixture
def mock_rankings():
    return json.loads((FIXTURES / 'sample_rankings_slim.json').read_text())


def test_agent_blurb_stub_mode_fits_x_limit(client, monkeypatch, mock_rankings):
    monkeypatch.setenv('AI_MODE', 'stub')
    monkeypatch.delenv('MINIMAX_API_KEY', raising=False)
    with patch('agent_service._static_blurb_for_team', return_value=None):
        with patch('agent_service.get_or_calculate_rankings', return_value=mock_rankings):
            # Clear any prior period cache so this assertion is stable across runs
            from cache import get_cache
            from shareable_blurb import blurb_cache_key, blurb_cache_period

            cache = get_cache()
            key = cache._generate_key(
                'share_blurb',
                blurb_cache_key('Oregon', 2024, 10, blurb_cache_period()),
            )
            cache.invalidate(key)

            response = client.post('/agent/blurb', json={
                'team_name': 'Oregon',
                'year': 2024,
                'week': 10,
            })
    assert response.status_code == 200
    data = response.get_json()
    assert data['ai_mode'] == 'stub'
    assert data['blurb']
    assert len(data['blurb']) <= 280
    assert 'Oregon' in data['blurb']
    assert data['max_chars'] == 280
    assert data['cache_period']
    assert data['cached'] is False


def test_agent_blurb_caches_second_request(client, monkeypatch, mock_rankings):
    monkeypatch.setenv('AI_MODE', 'stub')
    with patch('agent_service._static_blurb_for_team', return_value=None):
        with patch('agent_service.get_or_calculate_rankings', return_value=mock_rankings):
            first = client.post('/agent/blurb', json={
                'team_name': 'Oregon',
                'year': 2024,
                'week': 10,
            })
            second = client.post('/agent/blurb', json={
                'team_name': 'Oregon',
                'year': 2024,
                'week': 10,
            })
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.get_json()['blurb'] == second.get_json()['blurb']
    assert second.get_json()['cached'] is True


def test_agent_blurb_off_mode_still_returns_stub(client, monkeypatch, mock_rankings):
    """Modal always needs a blurb; off mode uses stub text (no MiniMax)."""
    monkeypatch.setenv('AI_MODE', 'off')
    with patch('agent_service._static_blurb_for_team', return_value=None):
        with patch('agent_service.get_or_calculate_rankings', return_value=mock_rankings):
            response = client.post('/agent/blurb', json={
                'team_name': 'Georgia',
                'year': 2024,
                'week': 10,
            })
    assert response.status_code == 200
    data = response.get_json()
    assert data['blurb']
    assert len(data['blurb']) <= 280
    assert data['ai_mode'] in ('off', 'stub')


def test_agent_climb_stub_is_plain_english(client, monkeypatch, mock_rankings):
    monkeypatch.setenv('AI_MODE', 'stub')
    with patch('agent_service._static_blurb_for_team', return_value=None):
        with patch('agent_service.get_or_calculate_rankings', return_value=mock_rankings):
            response = client.post('/agent/climb', json={
                'team_name': 'Ohio State',
                'year': 2024,
                'week': 10,
            })
    assert response.status_code == 200
    data = response.get_json()
    assert data['kind'] == 'climb'
    assert data['blurb']
    assert len(data['blurb']) <= 280
    assert 'Ohio State' in data['blurb']
    assert 'TQ' not in data['blurb']
    assert 'Δ' not in data['blurb']
    assert 'contrib' not in data['blurb'].lower()
