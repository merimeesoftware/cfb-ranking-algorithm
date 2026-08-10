"""Tests for CFBD offline / AI spend guards."""
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from spend_guards import (
    AIBudgetError,
    CFBDOfflineError,
    get_ai_call_count,
    get_cfbd_call_count,
    is_cfbd_offline,
    register_live_ai_call,
    register_live_cfbd_call,
    reset_ai_call_count,
    reset_cfbd_call_count,
    resolve_ai_mode,
    spend_status,
    ai_max_calls,
    cfbd_max_calls,
)
from ai_stub import stub_explain_from_context


FIXTURES = Path(__file__).parent / 'fixtures'


def test_cfbd_offline_defaults_in_development(monkeypatch):
    monkeypatch.delenv('CFBD_OFFLINE', raising=False)
    monkeypatch.setenv('FLASK_ENV', 'development')
    assert is_cfbd_offline() is True


def test_cfbd_online_when_explicitly_disabled(monkeypatch):
    monkeypatch.setenv('CFBD_OFFLINE', '0')
    monkeypatch.setenv('FLASK_ENV', 'development')
    assert is_cfbd_offline() is False


def test_cfbd_max_calls_budget(monkeypatch):
    reset_cfbd_call_count()
    monkeypatch.setenv('CFBD_MAX_CALLS', '2')
    assert register_live_cfbd_call() == 1
    assert register_live_cfbd_call() == 2
    with pytest.raises(CFBDOfflineError):
        register_live_cfbd_call()
    assert get_cfbd_call_count() == 2
    reset_cfbd_call_count()


def test_cfbd_max_defaults_in_development(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'development')
    monkeypatch.delenv('CFBD_MAX_CALLS', raising=False)
    assert cfbd_max_calls() == 25


def test_ai_max_calls_budget(monkeypatch):
    reset_ai_call_count()
    monkeypatch.setenv('AI_MAX_CALLS', '2')
    assert register_live_ai_call() == 1
    assert register_live_ai_call() == 2
    with pytest.raises(AIBudgetError):
        register_live_ai_call()
    assert get_ai_call_count() == 2
    reset_ai_call_count()


def test_ai_max_defaults_in_development(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'development')
    monkeypatch.delenv('AI_MAX_CALLS', raising=False)
    assert ai_max_calls() == 25


def test_spend_status_shape(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'development')
    monkeypatch.setenv('CFBD_OFFLINE', '1')
    monkeypatch.setenv('AI_MODE', 'stub')
    monkeypatch.delenv('CFBD_MAX_CALLS', raising=False)
    monkeypatch.delenv('AI_MAX_CALLS', raising=False)
    status = spend_status()
    assert status['cfbd_offline'] is True
    assert status['ai_mode'] == 'stub'
    assert status['cfbd_max_calls'] == 25
    assert status['ai_max_calls'] == 25


def test_make_request_blocked_when_offline(monkeypatch):
    monkeypatch.setenv('CFBD_OFFLINE', '1')
    from api_integration import CFBDApiClient

    client = CFBDApiClient(api_key='test')
    with patch('api_integration.requests.get') as mock_get:
        with pytest.raises(CFBDOfflineError):
            client._make_request('/games', {'year': 2024})
        mock_get.assert_not_called()


def test_resolve_ai_mode_defaults(monkeypatch):
    monkeypatch.delenv('AI_MODE', raising=False)
    monkeypatch.setenv('FLASK_ENV', 'development')
    assert resolve_ai_mode() == 'stub'
    monkeypatch.setenv('FLASK_ENV', 'production')
    assert resolve_ai_mode() == 'off'


def test_stub_explain_from_fixture():
    context = json.loads((FIXTURES / 'sample_team_context.json').read_text())
    text = stub_explain_from_context(context, 'Why #1?')
    assert 'Oregon' in text
    assert 'AI_MODE=stub' in text
    assert '#1' in text


def test_agent_explain_stub_mode(client, monkeypatch):
    monkeypatch.setenv('AI_MODE', 'stub')
    monkeypatch.delenv('MINIMAX_API_KEY', raising=False)
    mock_data = json.loads((FIXTURES / 'sample_rankings_slim.json').read_text())
    with patch('agent_service.get_or_calculate_rankings', return_value=mock_data):
        response = client.post('/agent/explain', json={
            'team_name': 'Oregon',
            'year': 2024,
            'week': 10,
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['ai_mode'] == 'stub'
        assert data['explanation']
        assert 'Oregon' in data['explanation']
        assert 'MiniMax' not in data['explanation'] or 'no MiniMax' in data['explanation']


def test_agent_explain_stub_expanded_context(client, monkeypatch):
    """Phase 4: context includes formula, path_to_climb, neighbors, top quality wins."""
    monkeypatch.setenv('AI_MODE', 'stub')
    monkeypatch.delenv('MINIMAX_API_KEY', raising=False)
    mock_data = json.loads((FIXTURES / 'sample_rankings_slim.json').read_text())
    with patch('agent_service.get_or_calculate_rankings', return_value=mock_data) as mock_get:
        response = client.post('/agent/explain', json={
            'team_name': 'Ohio State',
            'year': 2024,
            'week': 10,
        })
        assert response.status_code == 200
        # Offline-first default in tests: prefer_static should be True
        assert mock_get.call_args.kwargs.get('prefer_static') is True

        data = response.get_json()
        ctx = data['context']
        assert ctx['team_name'] == 'Ohio State'
        assert ctx['rank'] == 2
        assert 'formula_breakdown' in ctx
        fb = ctx['formula_breakdown']
        assert fb['tq_contribution'] == round(1850 * 0.65, 2)
        assert fb['rec_contribution'] == round(90 * 0.27, 2)
        assert fb['cq_contribution'] == round(90 * 0.08, 2)
        assert ctx['quality_wins'] == 2
        assert ctx['quality_losses'] == 1
        assert ctx['bad_losses'] == 0
        assert ctx['top_quality_wins'] == ['Oregon', 'Penn State']
        assert ctx['neighbor_ahead'] == 'Oregon'
        assert ctx['neighbor_behind'] == 'Georgia'
        assert ctx['path_to_climb']['at_top'] is False
        assert ctx['path_to_climb']['team_above'] == 'Oregon'
        assert ctx['path_to_climb']['score_gap'] == 5.0
        assert 'Oregon' in data['explanation']
        # Stub uses path_to_climb.summary / neighbor phrasing (not literal "path"/"gap")
        expl = data['explanation'].lower()
        assert (
            'catch' in expl
            or 'stronger' in expl
            or 'ahead' in expl
            or 'path' in expl
            or 'gap' in expl
        )


def test_agent_explain_off_mode(client, monkeypatch):
    monkeypatch.setenv('AI_MODE', 'off')
    mock_data = json.loads((FIXTURES / 'sample_rankings_slim.json').read_text())
    with patch('agent_service.get_or_calculate_rankings', return_value=mock_data):
        response = client.post('/agent/explain', json={
            'team_name': 'Georgia',
            'year': 2024,
            'week': 10,
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['ai_mode'] == 'off'
        assert data['explanation'] is None
        assert data['context']['team_name'] == 'Georgia'
        assert data['context']['path_to_climb']['team_above'] == 'Ohio State'
        assert data['context']['neighbor_ahead'] == 'Ohio State'
        assert len(data['context']['top_quality_wins']) == 3


def test_agent_explain_prefer_static_online(client, monkeypatch):
    monkeypatch.setenv('AI_MODE', 'stub')
    monkeypatch.setenv('CFBD_OFFLINE', '0')
    mock_data = json.loads((FIXTURES / 'sample_rankings_slim.json').read_text())
    with patch('agent_service.get_or_calculate_rankings', return_value=mock_data) as mock_get:
        response = client.post('/agent/explain', json={
            'team_name': 'Oregon',
            'year': 2024,
            'week': 10,
        })
        assert response.status_code == 200
        assert mock_get.call_args.kwargs.get('prefer_static') is False


def test_agent_explain_live_falls_back_without_key(client, monkeypatch):
    monkeypatch.setenv('AI_MODE', 'live')
    monkeypatch.delenv('MINIMAX_API_KEY', raising=False)
    # Module captured MINIMAX_API_KEY at import — patch the module attr
    mock_data = json.loads((FIXTURES / 'sample_rankings_slim.json').read_text())
    with patch('agent_service.MINIMAX_API_KEY', ''):
        with patch('agent_service.get_or_calculate_rankings', return_value=mock_data):
            response = client.post('/agent/explain', json={
                'team_name': 'Oregon',
                'year': 2024,
                'week': 10,
            })
            assert response.status_code == 200
            data = response.get_json()
            assert data['ai_mode'] == 'stub'
            assert data['explanation']
            assert 'no MiniMax' in data['explanation']


def test_agent_health_includes_ai_mode(client, monkeypatch):
    monkeypatch.setenv('AI_MODE', 'stub')
    response = client.get('/agent/health')
    assert response.status_code == 200
    assert response.get_json()['ai_mode'] == 'stub'


def test_stub_uses_path_to_climb_and_neighbors():
    context = json.loads((FIXTURES / 'sample_team_context.json').read_text())
    text = stub_explain_from_context(context)
    assert '#1' in text or 'Oregon' in text
    assert 'Ohio State' in text  # neighbor_behind / top win
    assert 'AI_MODE=stub' in text
