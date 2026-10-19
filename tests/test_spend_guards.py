"""Tests for CFBD offline / AI spend guards."""
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from spend_guards import (
    AIBudgetError,
    CFBDOfflineError,
    get_cfbd_call_count,
    get_provider_call_count,
    is_cfbd_offline,
    register_live_cfbd_call,
    register_live_provider_call,
    reset_cfbd_call_count,
    reset_provider_call_counts,
    resolve_ai_mode,
    resolve_cfbd_api_key,
    cfbd_key_status,
    spend_status,
    provider_max_calls,
    cfbd_max_calls,
)
from ai_stub import stub_explain_from_context


FIXTURES = Path(__file__).parent / 'fixtures'


def test_resolve_cfbd_api_key_uses_the_one_key(monkeypatch):
    monkeypatch.setenv('CFBD_API_KEY', 'key-aaaa')
    assert resolve_cfbd_api_key() == 'key-aaaa'
    assert resolve_cfbd_api_key('explicit-key') == 'explicit-key'


def test_cfbd_key_status_reports_presence_only(monkeypatch):
    monkeypatch.setenv('CFBD_API_KEY', 'key-aaaa')
    status = cfbd_key_status()
    assert status == {'active_configured': True}
    assert 'key-aaaa' not in status.values()
    monkeypatch.delenv('CFBD_API_KEY', raising=False)
    assert cfbd_key_status()['active_configured'] is False


def test_spend_status_includes_cfbd_key(monkeypatch):
    monkeypatch.setenv('CFBD_API_KEY', 'key-aaaa')
    monkeypatch.setenv('FLASK_ENV', 'development')
    status = spend_status()
    assert status['cfbd_key'] == {'active_configured': True}


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


def test_cfbd_gate_names_provider_and_app_source(monkeypatch):
    reset_cfbd_call_count()
    monkeypatch.setenv('CFBD_MAX_CALLS', '2')
    monkeypatch.setenv('SPEND_GATE_HOST', 'spend.budget')
    response = MagicMock()
    response.read.return_value = b'{"ok": true, "count": 1}'
    response.__enter__.return_value = response
    with patch('urllib.request.urlopen', return_value=response) as opened:
        assert register_live_cfbd_call() == 1
    request = opened.call_args.args[0]
    body = json.loads(request.data.decode())
    assert body['provider'] == 'cfbd'
    assert body['bucket'] == 'cfbd'
    assert body['source'] == 'app'
    assert request.full_url == 'http://spend.budget/consume'
    reset_cfbd_call_count()


def test_cfbd_max_defaults_in_development(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'development')
    monkeypatch.delenv('CFBD_MAX_CALLS', raising=False)
    assert cfbd_max_calls() == 25


def test_provider_max_calls_budget(monkeypatch):
    reset_provider_call_counts()
    monkeypatch.delenv('AI_KILL', raising=False)
    monkeypatch.delenv('WORKERS_AI_KILL', raising=False)
    monkeypatch.delenv('SPEND_GATE_HOST', raising=False)
    monkeypatch.setenv('AI_MAX_CALLS', '2')
    assert register_live_provider_call('workers_ai') == 1
    assert register_live_provider_call('workers_ai') == 2
    with pytest.raises(AIBudgetError):
        register_live_provider_call('workers_ai')
    assert get_provider_call_count('workers_ai') == 2
    reset_provider_call_counts()


def test_xai_stays_refused_when_the_cap_is_raised(monkeypatch):
    reset_provider_call_counts()
    monkeypatch.delenv('AI_KILL', raising=False)
    monkeypatch.delenv('XAI_KILL', raising=False)
    monkeypatch.delenv('SPEND_GATE_HOST', raising=False)
    monkeypatch.setenv('XAI_ENABLED', '1')
    monkeypatch.setenv('XAI_MAX_CALLS', '2')
    with pytest.raises(AIBudgetError):
        register_live_provider_call('xai')
    assert get_provider_call_count('xai') == 0
    reset_provider_call_counts()


def test_provider_max_defaults(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'development')
    monkeypatch.delenv('XAI_MAX_CALLS', raising=False)
    monkeypatch.delenv('AI_MAX_CALLS', raising=False)
    assert provider_max_calls('xai') == 0
    assert provider_max_calls('workers_ai') == 100


def test_spend_status_shape(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'development')
    monkeypatch.setenv('CFBD_OFFLINE', '1')
    monkeypatch.setenv('AI_MODE', 'stub')
    monkeypatch.delenv('CFBD_MAX_CALLS', raising=False)
    monkeypatch.delenv('XAI_MAX_CALLS', raising=False)
    monkeypatch.delenv('AI_MAX_CALLS', raising=False)
    status = spend_status()
    assert status['cfbd_offline'] is True
    assert status['ai_mode'] == 'stub'
    assert status['cfbd_max_calls'] == 25
    assert status['xai_max_calls'] == 0
    assert status['workers_ai_max_calls'] == 100


def test_make_request_blocked_when_offline(monkeypatch):
    monkeypatch.setenv('CFBD_OFFLINE', '1')
    from api_integration import CFBDApiClient

    client = CFBDApiClient(api_key='test')
    with patch('api_integration.requests.get') as mock_get:
        with pytest.raises(CFBDOfflineError):
            client._make_request('/games', {'year': 2024})
        mock_get.assert_not_called()


def test_make_request_does_not_log_api_key(monkeypatch, capsys):
    monkeypatch.setenv('CFBD_OFFLINE', '0')
    monkeypatch.setenv('FLASK_ENV', 'development')
    monkeypatch.setenv('CFBD_MAX_CALLS', '5')
    reset_cfbd_call_count()
    from api_integration import CFBDApiClient

    secret = 'unit-test-token-wxyz'
    client = CFBDApiClient(api_key=secret)
    response = MagicMock()
    response.status_code = 200
    response.headers = {'X-CallLimit-Remaining': '999'}
    response.json.return_value = []
    response.raise_for_status.return_value = None
    with patch('api_integration.requests.get', return_value=response):
        assert client._make_request('/teams', {'year': 2024}) == []
    logged = capsys.readouterr().out
    assert secret not in logged
    assert 'wxyz' not in logged
    assert 'key=' not in logged
    assert 'CFBD LIVE' in logged
    reset_cfbd_call_count()


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
    assert '#1' in text or 'board' in text.lower()
    # Fan-visible explanation must not leak stub/AI mode language
    assert 'AI_MODE' not in text
    assert 'xAI' not in text
    assert 'stub' not in text.lower()
    assert 'TQ' not in text
    assert 'CQ' not in text
    assert 'Elo' not in text


def test_agent_explain_stub_mode(client, monkeypatch):
    monkeypatch.setenv('AI_MODE', 'stub')
    monkeypatch.delenv('AI_XAI_HOST', raising=False)
    monkeypatch.delenv('AI_WORKERS_HOST', raising=False)
    mock_data = json.loads((FIXTURES / 'sample_rankings_slim.json').read_text())
    with patch('agent_service.get_or_calculate_rankings', return_value=mock_data):
        response = client.post('/agent/explain', json={
            'team_name': 'Oregon',
            'year': 2024,
            'week': 10,
            'question_id': 'why_here',
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['ai_mode'] == 'stub'
        assert data['explanation']
        assert 'Oregon' in data['explanation']
        assert 'AI_MODE' not in data['explanation']
        assert 'xAI' not in data['explanation']
        assert 'stub' not in data['explanation'].lower()


def test_agent_explain_stub_expanded_context(client, monkeypatch):
    """Phase 4: context includes formula, path_to_climb, neighbors, top quality wins."""
    from agent_service import explain_cache_logical
    from cache import get_cache
    from shareable_blurb import blurb_cache_period

    cache = get_cache()
    logical = explain_cache_logical('stub', 2024, 10, 'Ohio State', 'why_here', blurb_cache_period())
    cache.invalidate(cache._generate_key('explain', logical))
    monkeypatch.setenv('AI_MODE', 'stub')
    monkeypatch.delenv('AI_XAI_HOST', raising=False)
    monkeypatch.delenv('AI_WORKERS_HOST', raising=False)
    mock_data = json.loads((FIXTURES / 'sample_rankings_slim.json').read_text())
    with patch('agent_service.get_or_calculate_rankings', return_value=mock_data) as mock_get:
        response = client.post('/agent/explain', json={
            'team_name': 'Ohio State',
            'year': 2024,
            'week': 10,
            'question_id': 'why_here',
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
        assert fb['tq_contribution'] == round(1850 * 0.80, 2)
        assert fb['rec_contribution'] == round(90 * 0.15, 2)
        assert fb['cq_contribution'] == round(90 * 0.05, 2)
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
            'question_id': 'why_here',
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
    """Agent path always prefers static/slim rankings (no cold solver on explain)."""
    from agent_service import explain_cache_logical
    from cache import get_cache
    from shareable_blurb import blurb_cache_period

    cache = get_cache()
    logical = explain_cache_logical('stub', 2024, 10, 'Oregon', 'results', blurb_cache_period())
    cache.invalidate(cache._generate_key('explain', logical))
    monkeypatch.setenv('AI_MODE', 'stub')
    monkeypatch.setenv('CFBD_OFFLINE', '0')
    mock_data = json.loads((FIXTURES / 'sample_rankings_slim.json').read_text())
    with patch('agent_service.get_or_calculate_rankings', return_value=mock_data) as mock_get:
        response = client.post('/agent/explain', json={
            'team_name': 'Oregon',
            'year': 2024,
            'week': 10,
            'question_id': 'results',
        })
        assert response.status_code == 200
        assert mock_get.call_args.kwargs.get('prefer_static') is True


def test_agent_explain_live_falls_back_without_host(client, monkeypatch):
    monkeypatch.setenv('AI_MODE', 'live')
    monkeypatch.delenv('AI_XAI_HOST', raising=False)
    monkeypatch.delenv('AI_WORKERS_HOST', raising=False)
    mock_data = json.loads((FIXTURES / 'sample_rankings_slim.json').read_text())
    with patch('agent_service.get_or_calculate_rankings', return_value=mock_data):
            response = client.post('/agent/explain', json={
                'team_name': 'Oregon',
                'year': 2024,
                'week': 10,
                'question_id': 'why_here',
                'provider': 'workers_ai',
            })
            assert response.status_code == 200
            data = response.get_json()
            assert data['ai_mode'] == 'stub'
            assert data['explanation']
            assert 'Oregon' in data['explanation']
            assert 'AI_MODE' not in data['explanation']
            assert 'xAI' not in data['explanation']


def test_agent_health_hides_spend_counters(client, monkeypatch):
    monkeypatch.setenv('AI_MODE', 'stub')
    response = client.get('/agent/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'ok'
    for key in (
        'ai_mode',
        'ai_live_calls',
        'xai_max_calls',
        'workers_ai_max_calls',
        'cfbd_calls',
        'cfbd_max_calls',
        'cfbd_key',
        'agent_rate_limit_per_hour',
        'spend',
    ):
        assert key not in data


def test_stub_uses_path_to_climb_and_neighbors():
    context = json.loads((FIXTURES / 'sample_team_context.json').read_text())
    text = stub_explain_from_context(context)
    assert '#1' in text or 'Oregon' in text
    assert 'Ohio State' in text  # neighbor_behind / top win
    assert 'AI_MODE' not in text
    assert 'xAI' not in text
    assert 'board' in text.lower()
