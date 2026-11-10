"""Weekly dollar stop: estimate, $5 CI rule, and the pre-call refusal."""
import io
import json
import sys
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

from check_weekly_usd import live_spec, main  # noqa: E402
from spend_guards import AIBudgetError, guard_xai_spend, reset_xai_week_spend, xai_week_micros  # noqa: E402
from xai_usd import (  # noqa: E402
    iso_week_id,
    load_prices,
    usd_to_micros,
    weekly_cap_errors,
    weekly_total_micros,
    worst_case_micros,
    would_cross,
)

FIXTURE = ROOT / 'tests' / 'fixtures' / 'caps' / 'weekly_usd_at_5.json'


def test_prices_stay_marked_verify_and_cite_the_docs_page():
    prices = load_prices()
    assert prices['price_status'] == 'verify'
    assert prices['source_url'] == 'https://docs.x.ai/developers/pricing'
    assert prices['model'] == 'grok-4'
    assert usd_to_micros(prices['cfbd_tier1_usd_per_week']) == 230_000


def test_worst_case_is_prompt_chars_plus_max_output():
    assert worst_case_micros('hi') == 2 * 25 + 256 * 100
    assert worst_case_micros('') == 256 * 100
    assert would_cross(0, 25650, 0) is True
    assert would_cross(0, 25650, 25650) is False
    assert would_cross(1, 25650, 25650) is True


def test_iso_week_rolls_at_monday_utc():
    assert iso_week_id(datetime(2026, 10, 19, 5, 17, tzinfo=timezone.utc)) == '2026-W43'
    assert iso_week_id(datetime(2026, 1, 1, tzinfo=timezone.utc)) == '2026-W01'
    assert iso_week_id(datetime(2025, 12, 29, tzinfo=timezone.utc)) == '2026-W01'
    assert iso_week_id(datetime(2027, 1, 1, tzinfo=timezone.utc)) == '2026-W53'


def test_planted_five_dollar_fixture_fails_and_live_total_is_zero():
    prices = load_prices()
    planted = json.loads(FIXTURE.read_text(encoding='utf-8'))
    assert planted['xai_weekly_usd_cap'] == 5
    assert planted['cfbd_tier'] == 0
    assert weekly_cap_errors(planted['xai_weekly_usd_cap'], planted['cfbd_tier'], prices)
    assert usd_to_micros(planted['xai_weekly_usd_cap']) == usd_to_micros(prices['weekly_limit_usd'])
    assert weekly_cap_errors('4.99', 0, prices) == []
    assert weekly_total_micros('4.77', '1', prices) == 5_000_000
    assert weekly_cap_errors('4.77', '1', prices)
    assert weekly_cap_errors('4.76', '1', prices) == []
    assert weekly_cap_errors(0, 0, prices) == []
    assert weekly_total_micros(0, '1', prices) == 230_000
    spec = live_spec()
    assert spec['errors'] == []
    assert weekly_total_micros(spec['xai_weekly_usd_cap'], spec['cfbd_tier'], prices) == 0
    assert main() == 0


def test_cap_zero_refuses_before_a_reserve(monkeypatch):
    reset_xai_week_spend()
    monkeypatch.setenv('XAI_ENABLED', '1')
    monkeypatch.delenv('XAI_WEEKLY_USD_CAP', raising=False)
    monkeypatch.delenv('XAI_KILL', raising=False)
    monkeypatch.delenv('AI_KILL', raising=False)
    monkeypatch.delenv('SPEND_GATE_HOST', raising=False)
    with pytest.raises(AIBudgetError) as caught:
        guard_xai_spend('hi', commit=True)
    assert caught.value.code == 'xai_weekly_usd'
    assert xai_week_micros() == 0
    reset_xai_week_spend()


def test_a_fitting_week_cap_still_stops_on_the_daily_hard_zero(monkeypatch):
    reset_xai_week_spend()
    monkeypatch.setenv('XAI_ENABLED', '1')
    monkeypatch.setenv('XAI_WEEKLY_USD_CAP', '4')
    monkeypatch.delenv('XAI_KILL', raising=False)
    monkeypatch.delenv('AI_KILL', raising=False)
    monkeypatch.delenv('SPEND_GATE_HOST', raising=False)
    with pytest.raises(AIBudgetError) as caught:
        guard_xai_spend('hi', commit=True)
    assert caught.value.code == 'xai_budget'
    assert xai_week_micros() == 0
    reset_xai_week_spend()


def test_reserve_commits_until_the_next_request_would_cross(monkeypatch):
    reset_xai_week_spend()
    monkeypatch.setenv('XAI_ENABLED', '1')
    monkeypatch.setenv('XAI_WEEKLY_USD_CAP', '0.03')
    monkeypatch.delenv('XAI_KILL', raising=False)
    monkeypatch.delenv('AI_KILL', raising=False)
    monkeypatch.delenv('SPEND_GATE_HOST', raising=False)
    monkeypatch.setattr('spend_guards.provider_max_calls', lambda _provider: 5)
    import spend_guards

    spend_guards._xai_week_id = '2020-W01'
    spend_guards._xai_week_micros = 10_000_000
    assert guard_xai_spend('hi', commit=True) is True
    assert xai_week_micros() == worst_case_micros('hi')
    with pytest.raises(AIBudgetError) as caught:
        guard_xai_spend('hi', commit=True)
    assert caught.value.code == 'xai_weekly_usd'
    assert xai_week_micros() == worst_case_micros('hi')
    reset_xai_week_spend()


def test_remote_reserve_posts_the_prompt_and_stops_on_the_week_code(monkeypatch):
    reset_xai_week_spend()
    monkeypatch.setenv('XAI_ENABLED', '1')
    monkeypatch.setenv('XAI_WEEKLY_USD_CAP', '4')
    monkeypatch.setenv('SPEND_GATE_HOST', 'spend.budget')
    monkeypatch.delenv('XAI_KILL', raising=False)
    monkeypatch.delenv('AI_KILL', raising=False)
    monkeypatch.setattr('spend_guards.provider_max_calls', lambda _provider: 5)
    with patch('urllib.request.urlopen') as opened:
        assert guard_xai_spend('hi', commit=False) is False
        opened.assert_not_called()
        response = MagicMock()
        response.read.return_value = b'{"ok": true, "spent_micros": 25650}'
        response.__enter__.return_value = response
        opened.return_value = response
        assert guard_xai_spend('hi', commit=True) is True
    request = opened.call_args.args[0]
    body = json.loads(request.data.decode())
    assert body['action'] == 'reserve_usd'
    assert body['prompt'] == 'hi'
    assert request.full_url == 'http://spend.budget/consume'
    error = urllib.error.HTTPError(
        'http://spend.budget/consume',
        429,
        'busy',
        hdrs=None,
        fp=io.BytesIO(b'{"ok": false, "busy": true, "code": "xai_weekly_usd"}'),
    )
    with patch('urllib.request.urlopen', side_effect=error):
        with pytest.raises(AIBudgetError) as caught:
            guard_xai_spend('hi', commit=True)
    assert caught.value.code == 'xai_weekly_usd'
    assert xai_week_micros() == 0
    reset_xai_week_spend()
