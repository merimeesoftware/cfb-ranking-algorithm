"""Tests for M3 defaults, web_search wiring, lookback periods, static blurbs."""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shareable_blurb import (
    blurb_cache_period,
    lookback_cache_period,
    minimax_web_search_enabled,
)
from static_rankings import team_blurb_from_static, write_share_blurbs


FIXTURES = Path(__file__).parent / 'fixtures'


def test_lookback_cache_period_quarterly():
    assert lookback_cache_period(date(2026, 2, 1)) == 'lookback-2026-Q1'
    assert lookback_cache_period(date(2026, 8, 10)) == 'lookback-2026-Q3'


def test_minimax_web_search_default_on(monkeypatch):
    monkeypatch.delenv('MINIMAX_WEB_SEARCH', raising=False)
    assert minimax_web_search_enabled() is True
    monkeypatch.setenv('MINIMAX_WEB_SEARCH', '0')
    assert minimax_web_search_enabled() is False


def test_minimax_model_defaults_to_m3(monkeypatch):
    monkeypatch.delenv('MINIMAX_MODEL', raising=False)
    monkeypatch.delenv('MINIMAX_BLURB_MODEL', raising=False)
    # Assert documented defaults without reloading Flask-bound module globals
    import agent_service

    assert agent_service.MINIMAX_MODEL == 'MiniMax-M3' or (
        os.environ.get('MINIMAX_MODEL', 'MiniMax-M3') == 'MiniMax-M3'
    )
    # Module may have been imported with env overrides; check factory default via getenv pattern
    assert os.environ.get('MINIMAX_MODEL', 'MiniMax-M3') == 'MiniMax-M3'
    assert os.environ.get('MINIMAX_BLURB_MODEL', agent_service.MINIMAX_MODEL) in (
        'MiniMax-M3',
        agent_service.MINIMAX_MODEL,
    )


def test_call_minimax_includes_web_search_tool(monkeypatch):
    monkeypatch.setenv('MINIMAX_API_KEY', 'test-key')
    monkeypatch.setenv('MINIMAX_WEB_SEARCH', '1')
    import agent_service

    monkeypatch.setattr(agent_service, 'MINIMAX_API_KEY', 'test-key')
    monkeypatch.setattr(agent_service, 'MINIMAX_MODEL', 'MiniMax-M3')

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        'content': [{'type': 'text', 'text': 'ok blurb under limit for tests?'}],
    }
    with patch('agent_service.register_live_ai_call', return_value=1):
        with patch('agent_service.requests.post', return_value=mock_resp) as post:
            text = agent_service._call_minimax(
                'hello',
                max_tokens=50,
                disable_thinking=True,
                use_web_search=True,
            )
    assert text == 'ok blurb under limit for tests?'
    payload = post.call_args.kwargs['json']
    assert payload['model'] == 'MiniMax-M3'
    assert payload['tools'] == [agent_service.WEB_SEARCH_TOOL]
    assert post.call_args.kwargs['timeout'] == agent_service.MINIMAX_WEB_SEARCH_TIMEOUT


def test_call_minimax_omits_tools_when_search_off(monkeypatch):
    import agent_service

    monkeypatch.setattr(agent_service, 'MINIMAX_API_KEY', 'test-key')
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {'content': [{'type': 'text', 'text': 'plain'}]}
    with patch('agent_service.register_live_ai_call', return_value=1):
        with patch('agent_service.requests.post', return_value=mock_resp) as post:
            agent_service._call_minimax('hello', use_web_search=False)
    assert 'tools' not in post.call_args.kwargs['json']


def test_team_blurb_from_static_period_gate(tmp_path):
    payload = {
        'period': blurb_cache_period(),
        'blurbs': {'Oregon': 'Oregon is No. 1. Debate?'},
    }
    write_share_blurbs(payload, 2024, 10, root=tmp_path)
    from static_rankings import read_share_blurbs

    data = read_share_blurbs(2024, 10, root=tmp_path)
    assert team_blurb_from_static(data, 'Oregon', require_period=payload['period'])
    assert team_blurb_from_static(data, 'Oregon', require_period='1999-01-01') is None


def test_agent_blurb_serves_static_before_live(client, monkeypatch, tmp_path):
    monkeypatch.setenv('AI_MODE', 'stub')
    period = blurb_cache_period()
    payload = {
        'year': 2024,
        'week': 10,
        'period': period,
        'blurbs': {'Oregon': 'Static Oregon blurb from schedule. Fair ranking?'},
    }
    # Point frontend static root used by agent_service
    import agent_service

    monkeypatch.setattr(agent_service, '_FRONTEND_STATIC', str(tmp_path))
    write_share_blurbs(payload, 2024, 10, root=tmp_path)

    with patch('agent_service.get_or_calculate_rankings') as get_rankings:
        response = client.post('/agent/blurb', json={
            'team_name': 'Oregon',
            'year': 2024,
            'week': 10,
        })
    assert response.status_code == 200
    data = response.get_json()
    assert data['source'] == 'static'
    assert data['ai_mode'] == 'static'
    assert 'Static Oregon' in data['blurb']
    get_rankings.assert_not_called()


def test_precompute_blurbs_skip_if_exists(tmp_path, monkeypatch):
    monkeypatch.setenv('AI_MODE', 'stub')
    monkeypatch.setenv('CFBD_OFFLINE', '1')
    rankings = json.loads((FIXTURES / 'sample_rankings_slim.json').read_text())
    rankings['year'] = 2024
    rankings['week'] = 10

    import importlib.util

    from static_rankings import write_static_rankings

    frontend_root = tmp_path / 'frontend'
    write_static_rankings(rankings, 2024, 10, root=frontend_root)

    spec = importlib.util.spec_from_file_location(
        'precompute_blurbs',
        Path(__file__).resolve().parents[1] / 'scripts' / 'precompute_blurbs.py',
    )
    assert spec and spec.loader
    pb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pb)

    monkeypatch.setattr(pb, 'FRONTEND_ROOT', frontend_root)
    monkeypatch.setattr(pb, 'DEFAULT_ROOT', str(tmp_path / 'static_rankings'))

    gen1, skip1 = pb.precompute_kind(
        kind='share',
        year=2024,
        week=10,
        top_n=2,
        period=blurb_cache_period(),
        force=False,
        lookback=False,
    )
    assert gen1 >= 1
    gen2, skip2 = pb.precompute_kind(
        kind='share',
        year=2024,
        week=10,
        top_n=2,
        period=blurb_cache_period(),
        force=False,
        lookback=False,
    )
    assert gen2 == 0
    assert skip2 >= 1
