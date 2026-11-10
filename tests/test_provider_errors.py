"""Provider failures stay on the server. Visitors get a friendly state."""
import json
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest

FIXTURE = Path(__file__).parent / 'fixtures' / 'turnstile' / 'provider-error.json'
RANKINGS = Path(__file__).parent / 'fixtures' / 'sample_rankings_slim.json'


def _detail() -> str:
    return json.loads(FIXTURE.read_text(encoding='utf-8'))['detail']


def _rankings() -> dict:
    return json.loads(RANKINGS.read_text(encoding='utf-8'))


def _arm_live(monkeypatch):
    monkeypatch.setenv('AI_MODE', 'live')
    monkeypatch.setenv('AI_MAX_CALLS', '20')
    monkeypatch.setenv('XAI_MAX_CALLS', '0')
    monkeypatch.setenv('XAI_ENABLED', '0')
    monkeypatch.setenv('AI_WORKERS_HOST', 'ai.workers')
    monkeypatch.delenv('SPEND_GATE_HOST', raising=False)
    monkeypatch.delenv('AI_KILL', raising=False)
    monkeypatch.delenv('WORKERS_AI_KILL', raising=False)
    monkeypatch.setenv('AGENT_RATE_LIMIT', '500')
    from spend_guards import reset_provider_call_counts
    reset_provider_call_counts()


def _drop_blurb_cache():
    from cache import get_cache
    from shareable_blurb import blurb_cache_key, blurb_cache_period
    cache = get_cache()
    logical = blurb_cache_key('Oregon', 2024, 10, blurb_cache_period(), kind='share')
    cache.invalidate(cache._generate_key('share_blurb', logical))


@pytest.mark.parametrize('error_type', ['url', 'timeout'])
def test_call_provider_returns_fixed_string(monkeypatch, capsys, error_type):
    """The return value itself is the fixed string. An f-string of the exception fails this."""
    from agent_service import LLM_UNAVAILABLE, _call_provider

    detail = _detail()
    _arm_live(monkeypatch)

    def explode(*_args, **_kwargs):
        if error_type == 'url':
            raise urllib.error.URLError(detail)
        raise TimeoutError(detail)

    with patch('agent_service.urllib.request.urlopen', side_effect=explode):
        text = _call_provider('workers_ai', 'Oregon week 10')
    assert text == LLM_UNAVAILABLE
    assert detail not in text
    assert f'{detail}' not in text
    assert 'URLError' not in text
    assert 'TimeoutError' not in text
    assert detail in capsys.readouterr().out


@pytest.mark.parametrize('error_type', ['url', 'timeout'])
def test_explain_provider_error_hides_exception(client, monkeypatch, capsys, error_type):
    from agent_service import EXPLAIN_BREAKDOWN

    detail = _detail()
    _arm_live(monkeypatch)
    from agent_service import explain_cache_logical
    from cache import get_cache
    from shareable_blurb import blurb_cache_period
    cache = get_cache()
    logical = explain_cache_logical(
        'workers_ai', 2024, 10, 'Oregon', 'why_here', blurb_cache_period(),
    )
    cache.invalidate(cache._generate_key('explain', logical))

    def explode(*_args, **_kwargs):
        if error_type == 'url':
            raise urllib.error.URLError(detail)
        raise TimeoutError(detail)

    with patch('agent_service.get_or_calculate_rankings', return_value=_rankings()):
        with patch('agent_service.urllib.request.urlopen', side_effect=explode):
            response = client.post('/agent/explain', json={
                'team_name': 'Oregon',
                'year': 2024,
                'week': 10,
                'question_id': 'why_here',
                'provider': 'workers_ai',
            })
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert response.get_json()['explanation'] == EXPLAIN_BREAKDOWN
    assert detail not in body
    assert 'Traceback' not in body
    assert 'URLError' not in body
    assert detail in capsys.readouterr().out


@pytest.mark.parametrize('error_type', ['url', 'timeout'])
def test_blurb_provider_error_falls_back_to_stub(client, monkeypatch, capsys, error_type):
    detail = _detail()
    _arm_live(monkeypatch)
    _drop_blurb_cache()

    def explode(*_args, **_kwargs):
        if error_type == 'url':
            raise urllib.error.URLError(detail)
        raise TimeoutError(detail)

    with patch('agent_service._static_blurb_for_team', return_value=None):
        with patch('agent_service.get_or_calculate_rankings', return_value=_rankings()):
            with patch('agent_service.urllib.request.urlopen', side_effect=explode):
                response = client.post('/agent/blurb', json={
                    'team_name': 'Oregon',
                    'year': 2024,
                    'week': 10,
                })
    payload = response.get_json()
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert payload['ai_mode'] == 'stub'
    assert payload['blurb']
    assert 'Oregon' in payload['blurb']
    assert detail not in body
    assert 'Traceback' not in body
    assert 'URLError' not in body
    assert detail in capsys.readouterr().out
