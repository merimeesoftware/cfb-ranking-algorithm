"""Monthly CFBD projection: cron calls plus the live daily budget times 31."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from check_cfbd_month import (  # noqa: E402
    APP_CEILING,
    HARD_CAP,
    IN_SEASON_MONTH_CAP,
    evaluate,
    expected_in_season_calls,
    in_season_errors,
    in_season_month_calls,
    live_spec,
    main,
    monthly_total,
    production_vars,
    share_errors,
    share_total,
)

FIXTURE = ROOT / 'tests' / 'fixtures' / 'caps' / 'cfbd_month_over_budget.json'
SHARE_FIXTURE = ROOT / 'tests' / 'fixtures' / 'caps' / 'cfbd_share_sum_over.json'
SEASON_FIXTURE = ROOT / 'tests' / 'fixtures' / 'caps' / 'cfbd_in_season_over_50.json'


def test_planted_over_budget_fixture_fails():
    spec = json.loads(FIXTURE.read_text(encoding='utf-8'))
    total, cron_calls = monthly_total(
        spec['cron_calls_per_run'],
        spec['live_cfbd_per_day'],
        sundays_per_year=spec['sundays_per_year'],
        months=spec['months'],
        days=spec['days'],
    )
    assert spec['provider'] == 'cfbd'
    assert spec['source'] == 'app'
    assert spec['ceiling'] == APP_CEILING
    assert cron_calls == 500 * 52 // 12
    assert total == cron_calls + 30 * 31
    assert total > spec['ceiling']
    assert total > HARD_CAP
    assert evaluate(spec)


def test_planted_share_sum_exceeds_hard_cap():
    spec = json.loads(SHARE_FIXTURE.read_text(encoding='utf-8'))
    total = share_total(spec)
    assert spec['provider'] == 'cfbd'
    assert spec['ceiling'] == 2900
    assert spec['mcp_reserved'] == 150
    assert spec['margin'] == 50
    assert total == 3100
    assert total > HARD_CAP
    assert share_errors(spec)


def test_planted_in_season_month_exceeds_50():
    spec = json.loads(SEASON_FIXTURE.read_text(encoding='utf-8'))
    calls = in_season_month_calls(
        spec['cron_calls_per_run'],
        spec['in_season_sundays_per_month'],
    )
    assert spec['provider'] == 'cfbd'
    assert calls == 55
    assert calls > IN_SEASON_MONTH_CAP
    assert in_season_errors(calls)


def test_live_config_stays_under_tier2_cap():
    spec = live_spec()
    assert spec['errors'] == []
    assert spec['provider'] == 'cfbd'
    assert spec['source'] == 'app'
    assert spec['ceiling'] == 2800
    assert spec['hard_cap'] == 3000
    assert spec['mcp_reserved'] == 150
    assert spec['margin'] == 50
    assert share_total(spec) == 3000
    assert share_errors(spec) == []
    assert spec['cron_calls_per_run'] == 8
    assert spec['live_cfbd_per_day'] == 4
    total, cron_calls = monthly_total(
        spec['cron_calls_per_run'],
        spec['live_cfbd_per_day'],
        sundays_per_year=spec['sundays_per_year'],
        months=spec['months'],
        days=spec['days'],
    )
    assert cron_calls == 8 * 52 // 12
    assert total == cron_calls + 4 * 31
    assert total <= spec['ceiling']
    worst = in_season_month_calls(8, spec['in_season_sundays_per_month'])
    expected = expected_in_season_calls(spec['in_season_sundays_per_month'])
    assert worst == 40
    assert expected == 8
    assert worst <= IN_SEASON_MONTH_CAP
    assert expected <= IN_SEASON_MONTH_CAP
    assert main() == 0


def test_production_vars_ignore_env_dev():
    text = """
[vars]
AI_MODE = "stub"
CFBD_OFFLINE = "1"
XAI_MAX_CALLS = "0"
CFBD_MAX_CALLS = "4"

[env.dev.vars]
AI_MODE = "stub"
CFBD_OFFLINE = "1"
CFBD_MAX_CALLS = "99"
"""
    found = production_vars(text)
    assert found['AI_MODE'] == 'stub'
    assert found['CFBD_OFFLINE'] == '1'
    assert found['XAI_MAX_CALLS'] == '0'
    assert found['CFBD_MAX_CALLS'] == '4'
