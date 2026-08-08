"""Live blurb resolution must never chop over-length model output."""
from __future__ import annotations

from unittest.mock import patch

from agent_service import _resolve_blurb
from shareable_blurb import BLURB_MAX_CHARS


def _ctx():
    return {
        'team_name': 'Indiana',
        'rank': 1,
        'conference': 'Big Ten',
        'neighbor_behind': 'Oregon',
        'records': {'total_wins': 16, 'total_losses': 0},
        'quality_wins': 7,
        'path_to_climb': {'at_top': True},
    }


def test_resolve_blurb_retries_until_under_280(monkeypatch):
    monkeypatch.setenv('AI_MODE', 'live')
    too_long = 'A' * 300 + ' Prove me wrong?'
    good = 'Indiana is No. 1 at 16-0 with seven quality wins. Can Oregon catch them?'
    assert len(good) <= BLURB_MAX_CHARS

    calls = {'n': 0}

    def fake_minimax(prompt, **kwargs):
        calls['n'] += 1
        return too_long if calls['n'] == 1 else good

    with patch('agent_service.MINIMAX_API_KEY', 'test-key'):
        with patch('agent_service._call_minimax', side_effect=fake_minimax):
            blurb, mode = _resolve_blurb(_ctx(), kind='share')

    assert mode == 'live'
    assert blurb == good
    assert len(blurb) <= BLURB_MAX_CHARS
    assert calls['n'] == 2
    assert blurb == good  # exact model text, not a truncated rewrite


def test_resolve_blurb_falls_back_to_stub_if_all_attempts_over_limit(monkeypatch):
    monkeypatch.setenv('AI_MODE', 'live')
    too_long = 'B' * 320

    with patch('agent_service.MINIMAX_API_KEY', 'test-key'):
        with patch('agent_service._call_minimax', return_value=too_long) as mock_call:
            blurb, mode = _resolve_blurb(_ctx(), kind='share')

    assert mode == 'stub'
    assert len(blurb) <= BLURB_MAX_CHARS
    assert 'Indiana' in blurb
    assert mock_call.call_count >= 2
