#!/usr/bin/env python3
"""Fail when Workers AI calls times worst-case Neurons per call exceed 8,000.

Worst case uses the published per-million-token rates for the configured model
and the input and output token caps. A planted over-budget fixture must fail.
The free Workers AI allowance is 10,000 Neurons a day. 8,000 leaves margin.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / 'config' / 'workers-ai-neurons.json'
WRANGLER_PATH = ROOT / 'wrangler.toml'
PROVIDERS_PATH = ROOT / 'worker' / 'src' / 'providers.ts'
OVER_FIXTURE = ROOT / 'tests' / 'fixtures' / 'caps' / 'workers_ai_neurons_over.json'


def production_vars(text: str) -> dict[str, str]:
    head = re.split(r'(?m)^\[env\.', text, maxsplit=1)[0]
    match = re.search(r'(?ms)^\[vars\]\n(.*?)(?=^\[|\Z)', head)
    if not match:
        return {}
    return {
        name: value
        for name, value in re.findall(r'(?m)^([A-Z0-9_]+)\s*=\s*"([^"]*)"', match.group(1))
    }


def worst_case_neurons(
    max_input_tokens: int,
    max_output_tokens: int,
    neurons_per_million_input: int,
    neurons_per_million_output: int,
) -> int:
    """Ceil of input tokens and capped output tokens at the published rates."""
    raw = (
        max_input_tokens * neurons_per_million_input
        + max_output_tokens * neurons_per_million_output
    )
    return (raw + 999_999) // 1_000_000


def daily_neurons(calls_per_day: int, per_call: int) -> int:
    return calls_per_day * per_call


def evaluate(spec: dict) -> list[str]:
    per_call = worst_case_neurons(
        int(spec['max_input_tokens']),
        int(spec['max_output_tokens']),
        int(spec['neurons_per_million_input']),
        int(spec['neurons_per_million_output']),
    )
    total = daily_neurons(int(spec['calls_per_day']), per_call)
    ceiling = int(spec['ceiling'])
    if total > ceiling:
        return [
            f'Workers AI neurons {total} = {spec["calls_per_day"]} calls '
            f'× {per_call} worst-case, ceiling {ceiling}'
        ]
    return []


def live_spec() -> dict:
    formula = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    wrangler = production_vars(WRANGLER_PATH.read_text(encoding='utf-8'))
    providers = PROVIDERS_PATH.read_text(encoding='utf-8')
    errors: list[str] = []
    if wrangler.get('AI_MODE') != 'stub' or wrangler.get('CFBD_OFFLINE') != '1':
        errors.append('production AI_MODE must be stub and CFBD_OFFLINE must be 1')
    if 'AI_MAX_CALLS' not in wrangler:
        errors.append('production AI_MAX_CALLS is missing from wrangler.toml')
        return {'errors': errors}
    model = formula['model']
    if f"DEFAULT_WORKERS_AI_MODEL = '{model}'" not in providers:
        errors.append(f'providers.ts must call {model}')
    if 'web_search' in providers or re.search(r'\btools\b', providers):
        errors.append('Workers AI calls must not send web search or tools')
    output = re.search(r'WORKERS_AI_MAX_OUTPUT_TOKENS = (\d+)', providers)
    input_cap = re.search(r'WORKERS_AI_MAX_INPUT_CHARS = (\d+)', providers)
    if not output or int(output.group(1)) != int(formula['max_output_tokens']):
        errors.append('output token cap must match config/workers-ai-neurons.json')
    if not input_cap or int(input_cap.group(1)) != int(formula['max_input_tokens']):
        errors.append('input cap must match config/workers-ai-neurons.json')
    spec = {
        'calls_per_day': int(wrangler['AI_MAX_CALLS']),
        'max_input_tokens': int(formula['max_input_tokens']),
        'max_output_tokens': int(formula['max_output_tokens']),
        'neurons_per_million_input': int(formula['neurons_per_million_input']),
        'neurons_per_million_output': int(formula['neurons_per_million_output']),
        'ceiling': int(formula['ceiling']),
    }
    spec['errors'] = errors
    return spec


def main() -> int:
    spec = live_spec()
    errors = list(spec.get('errors') or [])
    if 'calls_per_day' in spec:
        per_call = worst_case_neurons(
            spec['max_input_tokens'],
            spec['max_output_tokens'],
            spec['neurons_per_million_input'],
            spec['neurons_per_million_output'],
        )
        total = daily_neurons(spec['calls_per_day'], per_call)
        print(
            f'Workers AI neurons {total} = {spec["calls_per_day"]} calls '
            f'× {per_call} worst-case; ceiling {spec["ceiling"]}'
        )
        errors.extend(evaluate(spec))
    planted = json.loads(OVER_FIXTURE.read_text(encoding='utf-8'))
    if not evaluate(planted):
        errors.append('workers_ai_neurons_over.json should fail the neuron ceiling')
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
