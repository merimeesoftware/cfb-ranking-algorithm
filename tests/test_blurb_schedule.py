"""Lookback periods, static blurbs, and skip-if-present precompute."""
from __future__ import annotations

import importlib.util
import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

from shareable_blurb import blurb_cache_period, lookback_cache_period
from static_rankings import team_blurb_from_static, write_share_blurbs, write_static_rankings

FIXTURES = Path(__file__).parent / 'fixtures'


def test_lookback_cache_period_quarterly():
    assert lookback_cache_period(date(2026, 2, 1)) == 'lookback-2026-Q1'
    assert lookback_cache_period(date(2026, 8, 10)) == 'lookback-2026-Q3'


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

    frontend_root = tmp_path / 'frontend'
    write_static_rankings(rankings, 2024, 10, root=frontend_root)

    spec = importlib.util.spec_from_file_location(
        'precompute_blurbs',
        Path(__file__).resolve().parents[1] / 'scripts' / 'precompute_blurbs.py',
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    monkeypatch.setattr(module, 'FRONTEND_ROOT', frontend_root)
    monkeypatch.setattr(module, 'DEFAULT_ROOT', str(tmp_path / 'static_rankings'))

    generated, _skipped = module.precompute_kind(
        kind='share',
        year=2024,
        week=10,
        top_n=2,
        period=blurb_cache_period(),
        force=False,
        lookback=False,
    )
    assert generated >= 1
    generated_again, skipped_again = module.precompute_kind(
        kind='share',
        year=2024,
        week=10,
        top_n=2,
        period=blurb_cache_period(),
        force=False,
        lookback=False,
    )
    assert generated_again == 0
    assert skipped_again >= 1
