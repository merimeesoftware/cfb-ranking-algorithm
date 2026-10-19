"""Planted-fixture proofs that every paid-call cap trips."""
import io
import json
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest

from public_board import BUSY_MESSAGE
from spend_guards import (
    AIBudgetError,
    CFBDOfflineError,
    cfbd_max_calls,
    get_cfbd_call_count,
    get_provider_call_count,
    provider_max_calls,
    register_live_cfbd_call,
    register_live_provider_call,
    reset_cfbd_call_count,
    reset_provider_call_counts,
)

FIXTURES = Path(__file__).parent / 'fixtures' / 'caps'
COUNTER_KEYS = {
    'ai_live_calls',
    'ai_max_calls',
    'xai_live_calls',
    'xai_max_calls',
    'workers_ai_live_calls',
    'workers_ai_max_calls',
    'cfbd_calls',
    'cfbd_max_calls',
    'cfbd_key',
    'agent_rate_limit_per_hour',
    'spend',
    'memory_entries',
    'cache_dir',
}


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding='utf-8'))


def test_unset_env_uses_in_code_defaults_not_unlimited(monkeypatch):
    fixture = _load('unset_defaults.json')
    monkeypatch.setenv('FLASK_ENV', fixture['FLASK_ENV'])
    monkeypatch.delenv('XAI_MAX_CALLS', raising=False)
    monkeypatch.delenv('AI_MAX_CALLS', raising=False)
    monkeypatch.delenv('CFBD_MAX_CALLS', raising=False)
    assert provider_max_calls('xai') == fixture['expect_xai']
    assert provider_max_calls('workers_ai') == fixture['expect_workers_ai']
    assert cfbd_max_calls() == fixture['expect_cfbd']
    assert provider_max_calls('xai') == 0
    assert provider_max_calls('workers_ai') == 100


def test_invalid_cap_env_falls_back_to_default(monkeypatch):
    monkeypatch.setenv('XAI_MAX_CALLS', 'nope')
    monkeypatch.setenv('AI_MAX_CALLS', '')
    monkeypatch.setenv('CFBD_MAX_CALLS', '')
    monkeypatch.setenv('FLASK_ENV', 'production')
    assert provider_max_calls('xai') == 0
    assert provider_max_calls('workers_ai') == 100
    assert cfbd_max_calls() == 25


def _trip_provider(monkeypatch, name: str):
    fixture = _load(name)
    reset_provider_call_counts()
    monkeypatch.delenv('SPEND_GATE_HOST', raising=False)
    monkeypatch.delenv('AI_KILL', raising=False)
    monkeypatch.delenv('XAI_KILL', raising=False)
    monkeypatch.delenv('WORKERS_AI_KILL', raising=False)
    env_name = 'XAI_MAX_CALLS' if fixture['bucket'] == 'xai' else 'AI_MAX_CALLS'
    monkeypatch.setenv(env_name, str(fixture['limit']))
    for _ in range(fixture['already_used']):
        register_live_provider_call(fixture['bucket'])
    with pytest.raises(AIBudgetError):
        register_live_provider_call(fixture['bucket'])
    assert get_provider_call_count(fixture['bucket']) == fixture['already_used']
    reset_provider_call_counts()


def test_xai_daily_budget_trips_from_planted_fixture(monkeypatch):
    _trip_provider(monkeypatch, 'xai_daily_at_cap.json')


def test_workers_ai_daily_budget_trips_from_planted_fixture(monkeypatch):
    _trip_provider(monkeypatch, 'workers_ai_daily_at_cap.json')


def test_cfbd_daily_budget_trips_from_planted_fixture(monkeypatch):
    fixture = _load('cfbd_daily_at_cap.json')
    reset_cfbd_call_count()
    monkeypatch.delenv('SPEND_GATE_HOST', raising=False)
    monkeypatch.delenv('CFBD_KILL', raising=False)
    monkeypatch.setenv('CFBD_MAX_CALLS', str(fixture['limit']))
    for _ in range(fixture['already_used']):
        register_live_cfbd_call()
    with pytest.raises(CFBDOfflineError):
        register_live_cfbd_call()
    assert get_cfbd_call_count() == fixture['already_used']
    reset_cfbd_call_count()


def _gate_denies(monkeypatch, name: str):
    fixture = _load(name)
    reset_provider_call_counts()
    monkeypatch.delenv('AI_KILL', raising=False)
    monkeypatch.delenv('XAI_KILL', raising=False)
    monkeypatch.delenv('WORKERS_AI_KILL', raising=False)
    monkeypatch.setenv('XAI_MAX_CALLS', '5')
    monkeypatch.setenv('AI_MAX_CALLS', '5')
    monkeypatch.setenv('SPEND_GATE_HOST', 'spend.budget')
    body = json.dumps(fixture).encode()
    error = urllib.error.HTTPError(
        'http://spend.budget/consume', 429, 'denied', None, io.BytesIO(body),
    )
    with patch('urllib.request.urlopen', side_effect=error):
        with pytest.raises(AIBudgetError):
            register_live_provider_call(fixture['bucket'])
    assert get_provider_call_count(fixture['bucket']) == 0
    reset_provider_call_counts()


def test_xai_global_gate_denies_planted_fixture(monkeypatch):
    _gate_denies(monkeypatch, 'xai_gate_denied.json')


def test_workers_ai_global_gate_denies_planted_fixture(monkeypatch):
    _gate_denies(monkeypatch, 'workers_ai_gate_denied.json')


def test_cfbd_global_gate_denies_planted_fixture(monkeypatch):
    fixture = _load('cfbd_gate_denied.json')
    reset_cfbd_call_count()
    monkeypatch.delenv('CFBD_KILL', raising=False)
    monkeypatch.setenv('CFBD_MAX_CALLS', '25')
    monkeypatch.setenv('SPEND_GATE_HOST', 'spend.budget')
    body = json.dumps(fixture).encode()
    error = urllib.error.HTTPError(
        'http://spend.budget/consume', 429, 'denied', None, io.BytesIO(body),
    )
    with patch('urllib.request.urlopen', side_effect=error):
        with pytest.raises(CFBDOfflineError):
            register_live_cfbd_call()
    assert get_cfbd_call_count() == 0
    reset_cfbd_call_count()


def test_kill_switch_stops_live_calls(monkeypatch):
    fixture = _load('kill_switch.json')
    monkeypatch.setenv('AI_KILL', fixture['AI_KILL'])
    monkeypatch.setenv('CFBD_KILL', fixture['CFBD_KILL'])
    monkeypatch.setenv('CFBD_OFFLINE', '0')
    monkeypatch.setenv('CFBD_MAX_CALLS', '25')
    monkeypatch.setenv('XAI_MAX_CALLS', '5')
    monkeypatch.setenv('AI_MAX_CALLS', '5')
    monkeypatch.delenv('SPEND_GATE_HOST', raising=False)
    reset_provider_call_counts()
    reset_cfbd_call_count()
    with pytest.raises(AIBudgetError):
        register_live_provider_call('xai')
    with pytest.raises(AIBudgetError):
        register_live_provider_call('workers_ai')
    with pytest.raises(CFBDOfflineError):
        register_live_cfbd_call()
    assert get_provider_call_count('xai') == 0
    assert get_provider_call_count('workers_ai') == 0
    assert get_cfbd_call_count() == 0

    from api_integration import CFBDApiClient

    api = CFBDApiClient(api_key='test')
    with patch('api_integration.requests.get') as mock_get:
        with pytest.raises(CFBDOfflineError):
            api._make_request('/games', {'year': 2024})
        mock_get.assert_not_called()
    reset_provider_call_counts()
    reset_cfbd_call_count()


def test_explain_kill_switch_returns_stub_and_makes_no_provider_call(client, monkeypatch):
    fixture = _load('kill_switch.json')
    monkeypatch.setenv('AI_MODE', 'live')
    monkeypatch.setenv('AI_KILL', fixture['AI_KILL'])
    monkeypatch.setenv('XAI_MAX_CALLS', '5')
    monkeypatch.setenv('AI_XAI_HOST', 'ai.xai')
    mock_data = json.loads(
        (Path(__file__).parent / 'fixtures' / 'sample_rankings_slim.json').read_text()
    )
    with patch('agent_service.urllib.request.urlopen') as mock_open:
        with patch('agent_service.get_or_calculate_rankings', return_value=mock_data):
            response = client.post('/agent/explain', json={
                'team_name': 'Oregon',
                'year': 2024,
                'week': 10,
                'question_id': 'why_here',
                'provider': 'xai',
            })
    assert response.status_code == 200
    body = response.get_json()
    assert body['code'] == 'kill_switch'
    assert body['message'] == BUSY_MESSAGE
    assert body['busy'] is True
    assert body['explanation']
    assert 'Oregon' in body['explanation']
    assert COUNTER_KEYS.isdisjoint(body)
    mock_open.assert_not_called()


def test_rate_limit_keys_on_cf_connecting_ip(client, monkeypatch):
    fixture = _load('rate_limit_ip.json')
    monkeypatch.setenv('AI_MODE', 'stub')
    monkeypatch.setenv('AGENT_RATE_LIMIT', str(fixture['limit']))
    reset_provider_call_counts()
    mock_data = json.loads(
        (Path(__file__).parent / 'fixtures' / 'sample_rankings_slim.json').read_text()
    )
    capped_headers = {
        'CF-Connecting-IP': fixture['cf_connecting_ip'],
        'X-Forwarded-For': fixture['x_forwarded_for'],
    }
    spoof_headers = {
        'X-Forwarded-For': fixture['cf_connecting_ip'],
    }
    other_headers = {
        'CF-Connecting-IP': fixture['other_ip'],
        'X-Forwarded-For': fixture['x_forwarded_for'],
    }
    with patch('agent_service.get_or_calculate_rankings', return_value=mock_data):
        payload = {
            'team_name': 'Oregon', 'year': 2024, 'week': 10, 'question_id': 'why_here',
        }
        first = client.post('/agent/explain', json=payload, headers=capped_headers)
        second = client.post('/agent/explain', json=payload, headers=capped_headers)
        spoofed = client.post('/agent/explain', json=payload, headers=spoof_headers)
        other = client.post('/agent/explain', json=payload, headers=other_headers)
    assert first.status_code == 200
    assert second.status_code == 429
    tripped = second.get_json()
    assert tripped['code'] == 'agent_rate_limit'
    assert tripped['message'] == BUSY_MESSAGE
    assert COUNTER_KEYS.isdisjoint(tripped)
    # Same X-Forwarded-For does not share the capped visitor's bucket.
    assert spoofed.status_code == 200
    assert other.status_code == 200
    reset_provider_call_counts()


def test_param_allowlist_rejects_formula_and_unlisted_week(client, monkeypatch):
    fixture = _load('manifest_allowlist.json')
    monkeypatch.setenv('RANKINGS_MANIFEST_PATH', str(FIXTURES / 'manifest_only_week_10.json'))

    with patch('ranking_service.calculate_rankings_logic', side_effect=AssertionError('recompute')):
        with patch('api_integration.requests.get', side_effect=AssertionError('cfbd')):
            rejected = client.get(fixture['reject_query'])
            allowed = client.get(fixture['allow_query'])
            unlisted = client.get(fixture['unlisted_query'])
            matchup = client.get(fixture['matchup_reject_query'])

    assert rejected.status_code == 400
    assert rejected.get_json()['code'] == 'formula_params'
    assert 'team_quality_weight' in rejected.get_json()['rejected']
    assert allowed.status_code == 200
    assert allowed.get_json()['team_rankings']
    assert unlisted.status_code == 200
    assert unlisted.get_json()['published'] is False
    assert unlisted.get_json()['team_rankings'] == []
    assert matchup.status_code == 400
    assert matchup.get_json()['code'] == 'formula_params'


def test_health_and_cache_stats_hide_counters(client):
    health = client.get('/agent/health')
    stats = client.get('/cache/stats')
    assert health.status_code == 200
    assert stats.status_code == 200
    assert COUNTER_KEYS.isdisjoint(health.get_json())
    assert COUNTER_KEYS.isdisjoint(stats.get_json())
    assert health.get_json()['status'] == 'ok'
    assert stats.get_json()['status'] == 'ok'
    assert 'memory_entries' not in stats.get_json()
