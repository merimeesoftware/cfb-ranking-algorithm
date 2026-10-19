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
    ai_max_calls,
    cfbd_max_calls,
    get_ai_call_count,
    get_cfbd_call_count,
    register_live_ai_call,
    register_live_cfbd_call,
    reset_ai_call_count,
    reset_cfbd_call_count,
)

FIXTURES = Path(__file__).parent / 'fixtures' / 'caps'
COUNTER_KEYS = {
    'ai_live_calls',
    'ai_max_calls',
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
    monkeypatch.delenv('AI_MAX_CALLS', raising=False)
    monkeypatch.delenv('CFBD_MAX_CALLS', raising=False)
    assert ai_max_calls() == fixture['expect_ai']
    assert cfbd_max_calls() == fixture['expect_cfbd']
    assert ai_max_calls() is not None
    assert cfbd_max_calls() is not None


def test_invalid_cap_env_falls_back_to_default(monkeypatch):
    monkeypatch.setenv('AI_MAX_CALLS', 'nope')
    monkeypatch.setenv('CFBD_MAX_CALLS', '')
    monkeypatch.setenv('FLASK_ENV', 'production')
    assert ai_max_calls() == 100
    assert cfbd_max_calls() == 25


def test_ai_daily_budget_trips_from_planted_fixture(monkeypatch):
    fixture = _load('ai_daily_at_cap.json')
    reset_ai_call_count()
    monkeypatch.delenv('SPEND_GATE_HOST', raising=False)
    monkeypatch.delenv('AI_KILL', raising=False)
    monkeypatch.setenv('AI_MAX_CALLS', str(fixture['limit']))
    for _ in range(fixture['already_used']):
        register_live_ai_call()
    with pytest.raises(AIBudgetError):
        register_live_ai_call()
    assert get_ai_call_count() == fixture['already_used']
    reset_ai_call_count()


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


def test_ai_global_gate_denies_planted_fixture(monkeypatch):
    fixture = _load('ai_gate_denied.json')
    reset_ai_call_count()
    monkeypatch.delenv('AI_KILL', raising=False)
    monkeypatch.setenv('AI_MAX_CALLS', '100')
    monkeypatch.setenv('SPEND_GATE_HOST', 'spend.budget')
    body = json.dumps(fixture).encode()
    error = urllib.error.HTTPError(
        'http://spend.budget/consume', 429, 'denied', None, io.BytesIO(body),
    )
    with patch('urllib.request.urlopen', side_effect=error):
        with pytest.raises(AIBudgetError):
            register_live_ai_call()
    assert get_ai_call_count() == 0
    reset_ai_call_count()


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
    monkeypatch.setenv('AI_MAX_CALLS', '100')
    monkeypatch.delenv('SPEND_GATE_HOST', raising=False)
    reset_ai_call_count()
    reset_cfbd_call_count()
    with pytest.raises(AIBudgetError):
        register_live_ai_call()
    with pytest.raises(CFBDOfflineError):
        register_live_cfbd_call()
    assert get_ai_call_count() == 0
    assert get_cfbd_call_count() == 0

    from api_integration import CFBDApiClient

    api = CFBDApiClient(api_key='test')
    with patch('api_integration.requests.get') as mock_get:
        with pytest.raises(CFBDOfflineError):
            api._make_request('/games', {'year': 2024})
        mock_get.assert_not_called()
    reset_ai_call_count()
    reset_cfbd_call_count()


def test_explain_kill_switch_returns_busy_not_minimax(client, monkeypatch):
    fixture = _load('kill_switch.json')
    monkeypatch.setenv('AI_MODE', 'live')
    monkeypatch.setenv('AI_KILL', fixture['AI_KILL'])
    mock_data = json.loads(
        (Path(__file__).parent / 'fixtures' / 'sample_rankings_slim.json').read_text()
    )
    with patch('agent_service.MINIMAX_API_KEY', 'paygo-test'):
        with patch('agent_service.requests.post') as mock_post:
            with patch('agent_service.get_or_calculate_rankings', return_value=mock_data):
                response = client.post('/agent/explain', json={
                    'team_name': 'Oregon',
                    'year': 2024,
                    'week': 10,
                })
    assert response.status_code == 429
    body = response.get_json()
    assert body['code'] == 'kill_switch'
    assert body['message'] == BUSY_MESSAGE
    assert body['busy'] is True
    assert COUNTER_KEYS.isdisjoint(body)
    mock_post.assert_not_called()


def test_rate_limit_keys_on_cf_connecting_ip(client, monkeypatch):
    fixture = _load('rate_limit_ip.json')
    monkeypatch.setenv('AI_MODE', 'stub')
    monkeypatch.setenv('AGENT_RATE_LIMIT', str(fixture['limit']))
    reset_ai_call_count()
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
        first = client.post('/agent/explain', json={
            'team_name': 'Oregon', 'year': 2024, 'week': 10,
        }, headers=capped_headers)
        second = client.post('/agent/explain', json={
            'team_name': 'Oregon', 'year': 2024, 'week': 10,
        }, headers=capped_headers)
        spoofed = client.post('/agent/explain', json={
            'team_name': 'Oregon', 'year': 2024, 'week': 10,
        }, headers=spoof_headers)
        other = client.post('/agent/explain', json={
            'team_name': 'Oregon', 'year': 2024, 'week': 10,
        }, headers=other_headers)
    assert first.status_code == 200
    assert second.status_code == 429
    tripped = second.get_json()
    assert tripped['code'] == 'agent_rate_limit'
    assert tripped['message'] == BUSY_MESSAGE
    assert COUNTER_KEYS.isdisjoint(tripped)
    # Same X-Forwarded-For does not share the capped visitor's bucket.
    assert spoofed.status_code == 200
    assert other.status_code == 200
    reset_ai_call_count()


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
