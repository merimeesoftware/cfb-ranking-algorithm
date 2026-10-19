#!/usr/bin/env python3
"""Fail when this app's projected CFBD calls exceed its monthly ceiling.

The budget is provider `cfbd`, source `app`. Monthly calls = cron calls +
live daily budget × days. Cron calls = the precompute workflow's per-run cap
× Sundays per year / months. The live budget is production CFBD_MAX_CALLS.

The free tier is about 1,000 calls a month and is shared. This app's ceiling
is 700. 150 is reserved for MCP via #115. 50 is margin. This repo does not
build the MCP wrapper. A planted over-budget fixture must fail.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / 'config' / 'cfbd-month.json'
WRANGLER_PATH = ROOT / 'wrangler.toml'
WORKFLOW_PATH = ROOT / '.github' / 'workflows' / 'precompute-rankings.yml'
OVER_FIXTURE = ROOT / 'tests' / 'fixtures' / 'caps' / 'cfbd_month_over_budget.json'

# App share of the shared CFBD free quota. 150 is reserved for MCP via #115.
# 50 is margin. 700 + 150 + 50 = 900.
APP_PROVIDER = 'cfbd'
APP_SOURCE = 'app'
APP_CEILING = 700
MCP_RESERVED = 150
MARGIN = 50


def monthly_total(
    cron_calls_per_run: int,
    live_cfbd_per_day: int,
    *,
    sundays_per_year: int,
    months: int,
    days: int,
) -> tuple[int, int]:
    """Return (monthly total, cron calls for the month)."""
    cron_calls = cron_calls_per_run * sundays_per_year // months
    return cron_calls + live_cfbd_per_day * days, cron_calls


def production_vars(text: str) -> dict[str, str]:
    """Top-level [vars] only. env.dev is not production."""
    head = re.split(r'(?m)^\[env\.', text, maxsplit=1)[0]
    match = re.search(r'(?ms)^\[vars\]\n(.*?)(?=^\[|\Z)', head)
    if not match:
        return {}
    found: dict[str, str] = {}
    for name, value in re.findall(r'(?m)^([A-Z0-9_]+)\s*=\s*"([^"]*)"', match.group(1)):
        found[name] = value
    return found


def workflow_cron_cap(text: str) -> int:
    match = re.search(r'(?m)^[ \t]*CFBD_MAX_CALLS:\s*"(\d+)"\s*$', text)
    if not match:
        raise ValueError('precompute-rankings.yml has no CFBD_MAX_CALLS')
    return int(match.group(1))


def evaluate(spec: dict) -> list[str]:
    total, cron_calls = monthly_total(
        int(spec['cron_calls_per_run']),
        int(spec['live_cfbd_per_day']),
        sundays_per_year=int(spec['sundays_per_year']),
        months=int(spec['months']),
        days=int(spec['days']),
    )
    ceiling = int(spec['ceiling'])
    errors = []
    if total > ceiling:
        errors.append(
            f'CFBD month is {total} ({cron_calls} cron + '
            f'{spec["live_cfbd_per_day"]}×{spec["days"]} live), ceiling is {ceiling}'
        )
    return errors


def live_spec() -> dict:
    formula = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    wrangler = production_vars(WRANGLER_PATH.read_text(encoding='utf-8'))
    errors = []
    if wrangler.get('AI_MODE') != 'stub' or wrangler.get('CFBD_OFFLINE') != '1':
        errors.append(
            'production AI_MODE must be stub and CFBD_OFFLINE must be 1'
        )
    if 'CFBD_MAX_CALLS' not in wrangler:
        errors.append('production CFBD_MAX_CALLS is missing from wrangler.toml')
        return {'errors': errors}
    if formula.get('provider') != APP_PROVIDER or formula.get('source') != APP_SOURCE:
        errors.append(f'CFBD budget must be provider {APP_PROVIDER} source {APP_SOURCE}')
    if int(formula.get('ceiling', -1)) != APP_CEILING:
        errors.append(f'app CFBD ceiling must be {APP_CEILING}')
    if int(formula.get('mcp_reserved', -1)) != MCP_RESERVED or int(formula.get('margin', -1)) != MARGIN:
        errors.append(
            f'CFBD share must reserve {MCP_RESERVED} for MCP via #115 and keep margin {MARGIN}'
        )
    spec = {
        'provider': formula.get('provider'),
        'source': formula.get('source'),
        'cron_calls_per_run': workflow_cron_cap(WORKFLOW_PATH.read_text(encoding='utf-8')),
        'live_cfbd_per_day': int(wrangler['CFBD_MAX_CALLS']),
        'sundays_per_year': formula['sundays_per_year'],
        'months': formula['months'],
        'days': formula['days'],
        'ceiling': formula['ceiling'],
        'mcp_reserved': formula.get('mcp_reserved'),
        'margin': formula.get('margin'),
    }
    spec['errors'] = errors
    return spec


def main() -> int:
    spec = live_spec()
    errors = list(spec.get('errors') or [])
    if 'cron_calls_per_run' in spec:
        total, cron_calls = monthly_total(
            spec['cron_calls_per_run'],
            spec['live_cfbd_per_day'],
            sundays_per_year=spec['sundays_per_year'],
            months=spec['months'],
            days=spec['days'],
        )
        print(
            f'CFBD {spec["provider"]}:{spec["source"]} month {total} = {cron_calls} cron '
            f'({spec["cron_calls_per_run"]}×{spec["sundays_per_year"]}/{spec["months"]}) '
            f'+ {spec["live_cfbd_per_day"]}×{spec["days"]} live; ceiling {spec["ceiling"]}; '
            f'{MCP_RESERVED} reserved for MCP via #115; margin {MARGIN}'
        )
        errors.extend(evaluate(spec))
    planted = json.loads(OVER_FIXTURE.read_text(encoding='utf-8'))
    if planted.get('provider') != APP_PROVIDER or planted.get('source') != APP_SOURCE:
        errors.append('cfbd_month_over_budget.json must name provider cfbd source app')
    if int(planted.get('ceiling', -1)) != APP_CEILING or not evaluate(planted):
        errors.append('cfbd_month_over_budget.json should fail the 700 ceiling')
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
