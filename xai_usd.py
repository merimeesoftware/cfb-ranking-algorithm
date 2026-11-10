"""xAI weekly dollar estimate.

Prices: https://docs.x.ai/developers/pricing
grok-4 is the configured model and is not on that page. The page lists
grok-4.7 at $2 input / $6 output per 1M tokens, and $4 / $12 once the prompt
reaches 200k. config/xai-usd.json marks grok-4 rates "verify" and uses a
higher placeholder so the estimate does not under-count.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / 'config' / 'xai-usd.json'
MICROS = Decimal(1_000_000)


def load_prices(path: Path | None = None) -> dict:
    return json.loads((path or CONFIG_PATH).read_text(encoding='utf-8'))


def usd_to_micros(value: object) -> int:
    micros = (Decimal(str(value)) * MICROS).to_integral_value(rounding=ROUND_HALF_UP)
    if micros < 0:
        raise ValueError('usd must be >= 0')
    return int(micros)


def iso_week_id(now: datetime | None = None) -> str:
    """UTC ISO week. The id rolls at Monday 00:00 UTC."""
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    else:
        moment = moment.astimezone(timezone.utc)
    iso = moment.isocalendar()
    return f'{iso.year}-W{iso.week:02d}'


def worst_case_micros(prompt: str, prices: dict | None = None) -> int:
    """max_tokens times the output price, plus one token per prompt character."""
    spec = prices or load_prices()
    chars = len(prompt or '')
    input_tokens = chars * int(spec['input_tokens_per_char'])
    output_tokens = int(spec['max_output_tokens'])
    return (
        input_tokens * int(spec['usd_per_million_input_tokens'])
        + output_tokens * int(spec['usd_per_million_output_tokens'])
    )


def would_cross(spent_micros: int, worst_micros: int, cap_micros: int) -> bool:
    """True when reserving the next request would go past the cap."""
    return spent_micros + worst_micros > cap_micros


def cfbd_week_micros(tier: object, prices: dict | None = None) -> int:
    """0 unless CFBD_TIER=1, which adds the configured paid-tier week cost."""
    if str(tier).strip() != '1':
        return 0
    spec = prices or load_prices()
    return usd_to_micros(spec['cfbd_tier1_usd_per_week'])


def weekly_total_micros(xai_cap: object, cfbd_tier: object, prices: dict | None = None) -> int:
    return usd_to_micros(xai_cap) + cfbd_week_micros(cfbd_tier, prices)


def weekly_cap_errors(xai_cap: object, cfbd_tier: object, prices: dict | None = None) -> list[str]:
    spec = prices or load_prices()
    limit = usd_to_micros(spec['weekly_limit_usd'])
    total = weekly_total_micros(xai_cap, cfbd_tier, spec)
    if total >= limit:
        return [
            f'weekly spend {total} micros >= {limit} '
            f'(xAI cap {xai_cap} + CFBD tier {cfbd_tier})'
        ]
    return []
