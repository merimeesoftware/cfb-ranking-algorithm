#!/usr/bin/env python3
"""Fail unless xAI stays closed and the retired vendor name is gone.

xAI's production daily budget is hard 0 and XAI_ENABLED is off. A planted
open-budget fixture must fail this check. `git grep` proves the retired
vendor name is absent from the tree. History is not scanned. Workers AI's
call cap is checked by scripts/check_workers_ai_neurons.py.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRANGLER_PATH = ROOT / 'wrangler.toml'
SECRETS_PATH = ROOT / 'docs' / 'SECRETS.md'
FIXTURES = ROOT / 'tests' / 'fixtures' / 'caps'
PROVISIONED = "provisioned by DevSecOps on Michael's yes"
GATEWAY_NAME = 'true-rankings'
GATEWAY_URL = re.compile(
    r'^https://gateway\.ai\.cloudflare\.com/v1/'
    r'[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/grok/v1/chat/completions$'
)
DIRECT_HOST = 'api.x.ai'


def retired_name() -> str:
    """The retired vendor token, built so the source file does not contain it."""
    return ''.join(chr(code) for code in (109, 105, 110, 105, 109, 97, 120))


def production_vars(text: str) -> dict[str, str]:
    head = re.split(r'(?m)^\[env\.', text, maxsplit=1)[0]
    match = re.search(r'(?ms)^\[vars\]\n(.*?)(?=^\[|\Z)', head)
    if not match:
        return {}
    return {
        name: value
        for name, value in re.findall(r'(?m)^([A-Z0-9_]+)\s*=\s*"([^"]*)"', match.group(1))
    }


def closed_budget_errors(limit: int) -> list[str]:
    if limit != 0:
        return [f'daily budget {limit} is open; the production default is 0']
    return []


def gateway_bypass_errors(call: dict) -> list[str]:
    provider = call.get('provider')
    if provider == 'xai':
        url = str(call.get('url') or '').strip()
        if not GATEWAY_URL.fullmatch(url):
            return ['xAI call bypasses the gateway URL']
        return []
    if provider == 'workers_ai':
        gateway_id = str(call.get('gateway_id') or '').strip()
        if not re.fullmatch(r'[A-Za-z0-9_-]+', gateway_id):
            return ['Workers AI call bypasses the gateway binding']
        return []
    return [f'unknown AI provider {provider or "(missing)"}']


def worker_source_bypass() -> list[str]:
    hits: list[str] = []
    src = ROOT / 'worker' / 'src'
    for path in sorted(src.glob('*.ts')):
        if DIRECT_HOST in path.read_text(encoding='utf-8'):
            hits.append(f'{path.relative_to(ROOT)} calls {DIRECT_HOST}')
    providers = (src / 'providers.ts').read_text(encoding='utf-8')
    if 'gateway.ai.cloudflare.com' not in providers or '/grok/v1/chat/completions' not in providers:
        hits.append('xAI completion must target the gateway grok path')
    if 'gateway:' not in providers or 'skipCache: true' not in providers:
        hits.append('Workers AI completion must pass gateway id on the binding')
    return hits


def binding_count(text: str) -> int:
    return len(re.findall(r'(?m)^\[(?:env\.dev\.)?ai\]\n(?:.*\n)*?binding = "AI"', text))


def contains_retired_name(text: str) -> bool:
    return retired_name().casefold() in text.casefold()


def retired_name_hits() -> list[str]:
    result = subprocess.run(
        ['git', 'grep', '-i', '-n', '-I', retired_name()],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 1:
        return []
    if result.returncode != 0:
        return [result.stderr.strip() or 'git grep failed']
    return [line for line in result.stdout.splitlines() if line.strip()]


def evaluate() -> list[str]:
    text = WRANGLER_PATH.read_text(encoding='utf-8')
    wrangler = production_vars(text)
    errors: list[str] = []
    if wrangler.get('AI_MODE') != 'stub' or wrangler.get('CFBD_OFFLINE') != '1':
        errors.append('production AI_MODE must be stub and CFBD_OFFLINE must be 1')
    raw_xai = wrangler.get('XAI_MAX_CALLS')
    if raw_xai is None:
        errors.append('production XAI_MAX_CALLS is missing from wrangler.toml')
    else:
        try:
            errors.extend(
                f'production XAI_MAX_CALLS: {item}'
                for item in closed_budget_errors(int(raw_xai))
            )
        except ValueError:
            errors.append('production XAI_MAX_CALLS is not an integer')
    if wrangler.get('XAI_ENABLED') != '0':
        errors.append('production XAI_ENABLED must be 0')
    if 'AI_MAX_CALLS' not in wrangler:
        errors.append('production AI_MAX_CALLS is missing from wrangler.toml')
    if wrangler.get('AI_GATEWAY_ID') != GATEWAY_NAME:
        errors.append(f'production AI_GATEWAY_ID must be {GATEWAY_NAME}')
    if 'CF_ACCOUNT_ID' not in wrangler:
        errors.append('production CF_ACCOUNT_ID must be a non-secret var')
    dev = re.search(r'(?ms)^\[env\.dev\.vars\]\n(.*?)(?=^\[|\Z)', text)
    dev_vars = dict(re.findall(r'(?m)^([A-Z0-9_]+)\s*=\s*"([^"]*)"', dev.group(1))) if dev else {}
    if dev_vars.get('AI_GATEWAY_ID') != GATEWAY_NAME or 'CF_ACCOUNT_ID' not in dev_vars:
        errors.append('env.dev.vars must set CF_ACCOUNT_ID and AI_GATEWAY_ID=true-rankings')
    if re.search(r'(?m)^XAI_API_KEY\s*=', text):
        errors.append('XAI_API_KEY must be a secret name, not a wrangler var')
    if binding_count(text) < 2:
        errors.append('wrangler.toml needs an [ai] binding = "AI" for production and env.dev')
    secrets = SECRETS_PATH.read_text(encoding='utf-8')
    if 'XAI_API_KEY' not in secrets or PROVISIONED not in secrets:
        errors.append(f'docs/SECRETS.md must name XAI_API_KEY as {PROVISIONED}')
    planted_xai = json.loads((FIXTURES / 'xai_budget_open.json').read_text(encoding='utf-8'))
    if not closed_budget_errors(int(planted_xai['limit'])):
        errors.append('xai_budget_open.json should fail the closed-budget check')
    planted_gateway = json.loads((FIXTURES / 'gateway_bypass.json').read_text(encoding='utf-8'))
    calls = planted_gateway.get('calls') or []
    if len(calls) < 2 or any(not gateway_bypass_errors(call) for call in calls):
        errors.append('gateway_bypass.json should fail when an AI call skips the gateway')
    errors.extend(worker_source_bypass())
    hits = retired_name_hits()
    if hits:
        errors.append('retired provider name remains outside history:')
        errors.extend(hits)
    return errors


def main() -> int:
    errors = evaluate()
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print('xAI closed at 0; gateway route required; retired name absent')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
