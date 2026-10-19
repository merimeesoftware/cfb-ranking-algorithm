#!/usr/bin/env python3
"""Fail when xAI's weekly cap plus CFBD's paid tier reaches $5.

xAI cap defaults to 0. CFBD tier cost is 0 unless CFBD_TIER=1, which adds
$0.23. The total must stay under $5. A planted fixture at $5 must fail.

Prices: https://docs.x.ai/developers/pricing
grok-4 is not listed. config/xai-usd.json marks the rates "verify".
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from xai_usd import load_prices, usd_to_micros, weekly_cap_errors, weekly_total_micros  # noqa: E402

WRANGLER_PATH = ROOT / 'wrangler.toml'
WORKER_PATH = ROOT / 'worker' / 'src' / 'xai-usd.ts'
FIXTURE = ROOT / 'tests' / 'fixtures' / 'caps' / 'weekly_usd_at_5.json'


def production_vars(text: str) -> dict[str, str]:
    head = re.split(r'(?m)^\[env\.', text, maxsplit=1)[0]
    match = re.search(r'(?ms)^\[vars\]\n(.*?)(?=^\[|\Z)', head)
    if not match:
        return {}
    return {
        name: value
        for name, value in re.findall(r'(?m)^([A-Z0-9_]+)\s*=\s*"([^"]*)"', match.group(1))
    }


def live_spec() -> dict:
    formula = load_prices()
    wrangler = production_vars(WRANGLER_PATH.read_text(encoding='utf-8'))
    errors: list[str] = []
    if wrangler.get('AI_MODE') != 'stub' or wrangler.get('CFBD_OFFLINE') != '1':
        errors.append('production AI_MODE must be stub and CFBD_OFFLINE must be 1')
    if formula.get('price_status') != 'verify':
        errors.append('xAI prices must stay marked verify until the source lists grok-4')
    if formula.get('source_url') != 'https://docs.x.ai/developers/pricing':
        errors.append('xAI price source_url must be the docs pricing page')
    worker = WORKER_PATH.read_text(encoding='utf-8')
    for key in (
        'usd_per_million_input_tokens',
        'usd_per_million_output_tokens',
        'max_output_tokens',
        'input_tokens_per_char',
    ):
        if f'{key}: {int(formula[key])}' not in worker:
            errors.append(f'worker/src/xai-usd.ts must match config {key}')
    if 'docs.x.ai/developers/pricing' not in worker:
        errors.append('worker/src/xai-usd.ts must cite the xAI pricing URL')
    return {
        'xai_weekly_usd_cap': wrangler.get('XAI_WEEKLY_USD_CAP', '0'),
        'cfbd_tier': wrangler.get('CFBD_TIER', '0'),
        'errors': errors,
        'prices': formula,
    }


def main() -> int:
    spec = live_spec()
    errors = list(spec['errors'])
    prices = spec['prices']
    tier = spec['cfbd_tier']
    combined = weekly_total_micros(spec['xai_weekly_usd_cap'], tier, prices)
    print(
        f'weekly USD {combined} micros = xAI cap {spec["xai_weekly_usd_cap"]} '
        f'+ CFBD tier {tier}; limit {prices["weekly_limit_usd"]}'
    )
    errors.extend(weekly_cap_errors(spec['xai_weekly_usd_cap'], tier, prices))
    planted = json.loads(FIXTURE.read_text(encoding='utf-8'))
    if not weekly_cap_errors(planted['xai_weekly_usd_cap'], planted['cfbd_tier'], prices):
        errors.append('weekly_usd_at_5.json should fail at $5')
    if usd_to_micros(planted['xai_weekly_usd_cap']) != usd_to_micros(prices['weekly_limit_usd']):
        errors.append('weekly_usd_at_5.json must sit on the $5 limit')
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
