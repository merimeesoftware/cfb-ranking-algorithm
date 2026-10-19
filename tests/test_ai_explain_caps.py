"""Allowlisted explain prompts, per-provider cache, and closed budgets."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from check_ai_providers import (  # noqa: E402
    closed_budget_errors,
    contains_retired_name,
    evaluate,
)

FIXTURES = Path(__file__).parent / 'fixtures' / 'caps'


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding='utf-8'))


def _rankings() -> dict:
    return json.loads(
        (Path(__file__).parent / 'fixtures' / 'sample_rankings_slim.json').read_text()
    )


class _Response:
    def __init__(self, payload: dict):
        self._payload = json.dumps(payload).encode()

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def test_unknown_question_id_is_400(client, monkeypatch):
    fixture = _load('question_id_rejected.json')
    monkeypatch.setenv('AI_MODE', 'stub')
    rejected = client.post('/agent/explain', json={
        'team_name': 'Oregon',
        'year': 2024,
        'week': 10,
        'question_id': fixture['question_id'],
    })
    assert rejected.status_code == 400
    assert rejected.get_json()['code'] == 'question_id'
    free_text = client.post('/agent/explain', json={
        'team_name': 'Oregon',
        'year': 2024,
        'week': 10,
        'question_id': 'why_here',
        'question': fixture['question'],
    })
    assert free_text.status_code == 400


def test_planted_open_budgets_fail_and_production_stays_closed():
    for name in ('xai_budget_open.json', 'workers_ai_budget_open.json'):
        planted = _load(name)
        assert closed_budget_errors(planted['limit'])
    assert evaluate() == []


def test_retired_name_detector_trips_on_planted_text():
    planted = ''.join(chr(code) for code in (109, 105, 110, 105, 109, 97, 120))
    assert contains_retired_name(f'the old client was {planted}')
    assert not contains_retired_name('xAI and Workers AI')


@pytest.mark.parametrize('fixture_name', [
    'xai_repeat_explain.json',
    'workers_ai_repeat_explain.json',
])
def test_repeat_explain_makes_one_paid_call(client, monkeypatch, fixture_name):
    fixture = _load(fixture_name)
    provider = fixture['provider']
    monkeypatch.setenv('AI_MODE', 'live')
    monkeypatch.setenv('XAI_MAX_CALLS', '5')
    monkeypatch.setenv('WORKERS_AI_MAX_CALLS', '5')
    monkeypatch.delenv('AI_KILL', raising=False)
    monkeypatch.delenv('XAI_KILL', raising=False)
    monkeypatch.delenv('WORKERS_AI_KILL', raising=False)
    monkeypatch.delenv('SPEND_GATE_HOST', raising=False)
    monkeypatch.setenv('AI_XAI_HOST', 'ai.xai')
    monkeypatch.setenv('AI_WORKERS_HOST', 'ai.workers')
    from agent_service import explain_cache_logical
    from cache import get_cache
    from shareable_blurb import blurb_cache_period

    cache = get_cache()
    logical = explain_cache_logical(
        provider,
        fixture['year'],
        fixture['week'],
        fixture['team_name'],
        fixture['question_id'],
        blurb_cache_period(),
    )
    cache.invalidate(cache._generate_key('explain', logical))
    calls = []

    def fake_urlopen(req, timeout=60):
        calls.append(req.full_url)
        return _Response({'ok': True, 'text': fixture['answer']})

    payload = {
        'team_name': fixture['team_name'],
        'year': fixture['year'],
        'week': fixture['week'],
        'question_id': fixture['question_id'],
        'provider': provider,
    }
    with patch('agent_service.get_or_calculate_rankings', return_value=_rankings()):
        with patch('agent_service.urllib.request.urlopen', side_effect=fake_urlopen):
            first = client.post('/agent/explain', json=payload)
            second = client.post('/agent/explain', json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.get_json()['cached'] is False
    assert second.get_json()['cached'] is True
    assert second.get_json()['explanation'] == fixture['answer']
    host = 'ai.xai' if provider == 'xai' else 'ai.workers'
    assert calls == [f'http://{host}/complete']


def test_provider_kill_serves_stub_for_each_path(client, monkeypatch):
    fixture = _load('provider_kill.json')
    monkeypatch.setenv('AI_MODE', 'live')
    monkeypatch.setenv('AI_KILL', fixture['AI_KILL'])
    monkeypatch.setenv('XAI_KILL', fixture['XAI_KILL'])
    monkeypatch.setenv('WORKERS_AI_KILL', fixture['WORKERS_AI_KILL'])
    monkeypatch.setenv('XAI_MAX_CALLS', '5')
    monkeypatch.setenv('WORKERS_AI_MAX_CALLS', '5')
    monkeypatch.setenv('AI_XAI_HOST', 'ai.xai')
    monkeypatch.setenv('AI_WORKERS_HOST', 'ai.workers')
    with patch('agent_service.urllib.request.urlopen') as opened:
        with patch('agent_service.get_or_calculate_rankings', return_value=_rankings()):
            for provider, question_id in (('xai', 'results'), ('workers_ai', 'neighbors')):
                response = client.post('/agent/explain', json={
                    'team_name': 'Georgia',
                    'year': 2024,
                    'week': 10,
                    'question_id': question_id,
                    'provider': provider,
                })
                assert response.status_code == 200
                body = response.get_json()
                assert body['busy'] is True
                assert body['code'] == 'kill_switch'
                assert body['explanation']
    opened.assert_not_called()
