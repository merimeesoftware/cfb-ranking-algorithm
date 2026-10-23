#!/usr/bin/env python3
"""Fail when this app's projected CFBD calls exceed its monthly ceiling.

The budget is provider `cfbd`, source `app`. Tier 2 allows 30,000 calls a
month. This repo's hard cap is 3,000 (app ceiling 2,800 + 150 MCP reserve
+ 50 margin). The cron path is tighter: an in-season month stays under 50.

Actions does not cache CFBD responses, so each Sunday starts cold.
Cold Sunday: ``/teams`` + two prior seasons + one bulk ``/games`` = 4.
``frontend/static/rankings/priors/{year}.json`` skips those two prior-season
calls. None are checked in, so the steady month still counts them.
Off-season (Jan 21–Aug 23): 0.
Peak Sundays in one month: 5.
Expected steady month: 4×5 = 20.
Per-run cap × 5 must also stay ≤ 50, so a loop cannot hide inside the cap.
The guard is the worst in-season month, not the 12-month average
(8×52/12 + 4×31 = 158). With the old 4/day visitor budget that worst month
is 8×5 + 4×31 = 164. Visitor CFBD in this model is 0, so the guarded month
is 8×5 = 40. Wrangler ``CFBD_MAX_CALLS`` stays 4 and is not the model.

A planted over-budget fixture must fail, a planted share fixture must break
the 3,000 sum, and a planted in-season fixture must break 50.
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
SCRIPT_PATH = ROOT / 'scripts' / 'precompute_rankings.py'
OVER_FIXTURE = ROOT / 'tests' / 'fixtures' / 'caps' / 'cfbd_month_over_budget.json'
SHARE_FIXTURE = ROOT / 'tests' / 'fixtures' / 'caps' / 'cfbd_share_sum_over.json'
IN_SEASON_FIXTURE = ROOT / 'tests' / 'fixtures' / 'caps' / 'cfbd_in_season_over_50.json'

# Tier 2 is 30,000 calls/month. The CI hard cap stays at 3,000.
# 2,800 + 150 MCP (#115) + 50 margin = 3,000.
APP_PROVIDER = 'cfbd'
APP_SOURCE = 'app'
HARD_CAP = 3000
APP_CEILING = 2800
SHARE_CAP = 3000
IN_SEASON_MONTH_CAP = 50
STEADY_CALLS_PER_RUN = 4
SEASON_SETUP_CALLS = 0
TIER2_MONTHLY_CALLS = 30000
VISITOR_CFBD_PER_DAY = 0


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


def worst_month(
    cron_calls_per_run: int,
    sundays: int,
    visitor_per_day: int,
    days: int,
) -> int:
    """True worst month: every in-season Sunday plus the visitor daily budget."""
    return int(cron_calls_per_run) * int(sundays) + int(visitor_per_day) * int(days)


def in_season_month_calls(cron_calls_per_run: int, sundays: int) -> int:
    """Worst in-season month if every Sunday spends the per-run cap."""
    return int(cron_calls_per_run) * int(sundays)


def expected_in_season_calls(sundays: int) -> int:
    """Cold Sunday: teams, two prior seasons, and one bulk games call."""
    return STEADY_CALLS_PER_RUN * int(sundays) + SEASON_SETUP_CALLS


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


def script_default_cap(text: str) -> int:
    match = re.search(r"setdefault\('CFBD_MAX_CALLS', '(\d+)'\)", text)
    if not match:
        raise ValueError('precompute_rankings.py has no CFBD_MAX_CALLS default')
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
    if total > HARD_CAP:
        errors.append(f'CFBD month is {total}, hard cap is {HARD_CAP}')
    return errors


def share_total(spec: dict) -> int:
    """App ceiling plus the MCP reserve plus margin."""
    return int(spec['ceiling']) + int(spec['mcp_reserved']) + int(spec['margin'])


def share_errors(spec: dict, cap: int = SHARE_CAP) -> list[str]:
    """Fail when the configured shares sum to more than the hard cap."""
    total = share_total(spec)
    if total > cap:
        return [
            f'CFBD shares {spec["ceiling"]} + {spec["mcp_reserved"]} + '
            f'{spec["margin"]} = {total}, cap {cap}'
        ]
    return []


def in_season_errors(calls: int, cap: int = IN_SEASON_MONTH_CAP) -> list[str]:
    if calls > cap:
        return [f'in-season cron month is {calls}, cap {cap}']
    return []


def live_spec() -> dict:
    formula = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    wrangler = production_vars(WRANGLER_PATH.read_text(encoding='utf-8'))
    errors = []
    if wrangler.get('AI_MODE') != 'live' or wrangler.get('CFBD_OFFLINE') != '1':
        errors.append(
            'production AI_MODE must be live and CFBD_OFFLINE must be 1'
        )
    if 'CFBD_MAX_CALLS' not in wrangler:
        errors.append('production CFBD_MAX_CALLS is missing from wrangler.toml')
        return {'errors': errors}
    if formula.get('provider') != APP_PROVIDER or formula.get('source') != APP_SOURCE:
        errors.append(f'CFBD budget must be provider {APP_PROVIDER} source {APP_SOURCE}')
    for name in (
        'ceiling', 'mcp_reserved', 'margin', 'hard_cap',
        'in_season_sundays_per_month', 'tier2_monthly_calls',
        'visitor_cfbd_per_day',
    ):
        if name not in formula:
            errors.append(f'config/cfbd-month.json missing {name}')
    cron_cap = workflow_cron_cap(WORKFLOW_PATH.read_text(encoding='utf-8'))
    script_cap = script_default_cap(SCRIPT_PATH.read_text(encoding='utf-8'))
    if cron_cap != script_cap:
        errors.append(
            f'workflow CFBD_MAX_CALLS {cron_cap} != script default {script_cap}'
        )
    spec = {
        'provider': formula.get('provider'),
        'source': formula.get('source'),
        'cron_calls_per_run': cron_cap,
        'live_cfbd_per_day': VISITOR_CFBD_PER_DAY,
        'visitor_cfbd_per_day': formula.get('visitor_cfbd_per_day'),
        'wrangler_cfbd_max_calls': wrangler.get('CFBD_MAX_CALLS'),
        'sundays_per_year': formula.get('sundays_per_year'),
        'months': formula.get('months'),
        'days': formula.get('days'),
        'ceiling': formula.get('ceiling'),
        'mcp_reserved': formula.get('mcp_reserved'),
        'margin': formula.get('margin'),
        'hard_cap': formula.get('hard_cap'),
        'in_season_sundays_per_month': formula.get('in_season_sundays_per_month'),
        'tier2_monthly_calls': formula.get('tier2_monthly_calls'),
    }
    if spec.get('ceiling') != APP_CEILING:
        errors.append(f'app ceiling must stay {APP_CEILING}')
    if spec.get('hard_cap') != HARD_CAP:
        errors.append(f'hard cap must stay {HARD_CAP}')
    if spec.get('tier2_monthly_calls') != TIER2_MONTHLY_CALLS:
        errors.append(f'tier2_monthly_calls must stay {TIER2_MONTHLY_CALLS}')
    if spec.get('visitor_cfbd_per_day') != VISITOR_CFBD_PER_DAY:
        errors.append(f'visitor CFBD budget must stay {VISITOR_CFBD_PER_DAY}')
    if HARD_CAP >= TIER2_MONTHLY_CALLS:
        errors.append(f'hard cap {HARD_CAP} must stay under Tier 2 {TIER2_MONTHLY_CALLS}')
    spec['errors'] = errors
    return spec


def main() -> int:
    spec = live_spec()
    errors = list(spec.get('errors') or [])
    if 'cron_calls_per_run' in spec and spec.get('sundays_per_year') is not None:
        total, cron_calls = monthly_total(
            spec['cron_calls_per_run'],
            spec['live_cfbd_per_day'],
            sundays_per_year=spec['sundays_per_year'],
            months=spec['months'],
            days=spec['days'],
        )
        if total > APP_CEILING:
            errors.append(f'app projection {total} exceeds {APP_CEILING}')
        if total > HARD_CAP:
            errors.append(f'app projection {total} exceeds hard cap {HARD_CAP}')
        errors.extend(evaluate(spec))
        sundays = int(spec['in_season_sundays_per_month'])
        cron_worst = in_season_month_calls(spec['cron_calls_per_run'], sundays)
        expected = expected_in_season_calls(sundays)
        visitor = spec.get('visitor_cfbd_per_day')
        guarded = None
        if isinstance(visitor, int):
            guarded = worst_month(
                spec['cron_calls_per_run'],
                sundays,
                visitor,
                spec['days'],
            )
            if guarded > APP_CEILING or guarded > HARD_CAP:
                errors.append(f'guarded worst month {guarded} exceeds the ceiling')
        errors.extend(in_season_errors(cron_worst))
        errors.extend(in_season_errors(expected))
        if all(spec.get(name) is not None for name in ('ceiling', 'mcp_reserved', 'margin')):
            shares = share_total(spec)
            print(
                f'CFBD {spec["provider"]}:{spec["source"]} '
                f'average {total} = {cron_calls} cron '
                f'({spec["cron_calls_per_run"]}×{spec["sundays_per_year"]}/{spec["months"]}) '
                f'+ {spec["visitor_cfbd_per_day"]}×{spec["days"]} visitor; '
                f'worst month if visitors were 4/day '
                f'{worst_month(spec["cron_calls_per_run"], sundays, 4, spec["days"])} '
                f'(not the 158 average); '
                f'guarded worst month {guarded} '
                f'({spec["cron_calls_per_run"]}×{sundays}={cron_worst}, '
                f'{spec["cron_calls_per_run"]}×{sundays}+{visitor}×{spec["days"]}); '
                f'ceiling {APP_CEILING}; hard cap {HARD_CAP}; '
                f'in-season cron worst {cron_worst}, '
                f'expected steady month {expected} '
                f'({STEADY_CALLS_PER_RUN}×{sundays}+{SEASON_SETUP_CALLS}={expected}); '
                f'shares {spec["ceiling"]} + {spec["mcp_reserved"]} + {spec["margin"]} = {shares}, '
                f'cap {SHARE_CAP}'
            )
            errors.extend(share_errors(spec))
        else:
            print(
                f'CFBD {spec["provider"]}:{spec["source"]} month {total} = {cron_calls} cron '
                f'+ {spec["live_cfbd_per_day"]}×{spec["days"]} live; ceiling {APP_CEILING}'
            )
    planted = json.loads(OVER_FIXTURE.read_text(encoding='utf-8'))
    if planted.get('provider') != APP_PROVIDER or planted.get('source') != APP_SOURCE:
        errors.append('cfbd_month_over_budget.json must name provider cfbd source app')
    if int(planted.get('ceiling', -1)) != APP_CEILING or not evaluate(planted):
        errors.append(f'cfbd_month_over_budget.json should fail the {APP_CEILING} ceiling')
    shares = json.loads(SHARE_FIXTURE.read_text(encoding='utf-8'))
    if shares.get('provider') != APP_PROVIDER or not share_errors(shares):
        errors.append(f'cfbd_share_sum_over.json should fail the {SHARE_CAP} share cap')
    season = json.loads(IN_SEASON_FIXTURE.read_text(encoding='utf-8'))
    season_calls = in_season_month_calls(
        season['cron_calls_per_run'],
        season['in_season_sundays_per_month'],
    )
    if season.get('provider') != APP_PROVIDER or not in_season_errors(season_calls):
        errors.append('cfbd_in_season_over_50.json should fail the 50 in-season cap')
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
