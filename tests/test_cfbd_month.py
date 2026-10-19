"""Monthly CFBD projection: cron calls plus the live daily budget times 31."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from check_cfbd_month import (  # noqa: E402
    evaluate,
    live_spec,
    main,
    monthly_total,
    production_vars,
    share_errors,
    share_total,
)

FIXTURE = ROOT / 'tests' / 'fixtures' / 'caps' / 'cfbd_month_over_budget.json'
SHARE_FIXTURE = ROOT / 'tests' / 'fixtures' / 'caps' / 'cfbd_share_sum_over.json'


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
    assert spec['ceiling'] == 700
    assert cron_calls == 200 * 52 // 12
    assert total == cron_calls + 25 * 31
    assert total > spec['ceiling']
    assert evaluate(spec)


def test_planted_share_sum_exceeds_900():
    spec = json.loads(SHARE_FIXTURE.read_text(encoding='utf-8'))
    total = share_total(spec)
    assert spec['provider'] == 'cfbd'
    assert spec['ceiling'] == 800
    assert spec['mcp_reserved'] == 150
    assert spec['margin'] == 50
    assert total == 1000
    assert total > 900
    assert share_errors(spec)


def test_live_config_stays_under_700():
    spec = live_spec()
    assert spec['errors'] == []
    assert spec['provider'] == 'cfbd'
    assert spec['source'] == 'app'
    assert spec['ceiling'] == 700
    assert spec['mcp_reserved'] == 150
    assert spec['margin'] == 50
    assert share_total(spec) == 900
    assert share_errors(spec) == []
    assert spec['cron_calls_per_run'] == 24
    assert spec['live_cfbd_per_day'] == 4
    total, cron_calls = monthly_total(
        spec['cron_calls_per_run'],
        spec['live_cfbd_per_day'],
        sundays_per_year=spec['sundays_per_year'],
        months=spec['months'],
        days=spec['days'],
    )
    assert cron_calls == 104
    assert total == 228
    assert total <= spec['ceiling']
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
