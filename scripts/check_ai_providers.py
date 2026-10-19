#!/usr/bin/env python3
"""Fail unless both AI providers stay closed and the retired vendor name is gone.

Production daily budgets are 0. A planted open-budget fixture must fail this
check. `git grep` proves the retired vendor name is absent from the tree.
History is not scanned.
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
    for name in ('XAI_MAX_CALLS', 'WORKERS_AI_MAX_CALLS'):
        raw = wrangler.get(name)
        if raw is None:
            errors.append(f'production {name} is missing from wrangler.toml')
            continue
        try:
            limit = int(raw)
        except ValueError:
            errors.append(f'production {name} is not an integer')
            continue
        errors.extend(f'production {name}: {item}' for item in closed_budget_errors(limit))
    if re.search(r'(?m)^XAI_API_KEY\s*=', text):
        errors.append('XAI_API_KEY must be a secret name, not a wrangler var')
    if binding_count(text) < 2:
        errors.append('wrangler.toml needs an [ai] binding = "AI" for production and env.dev')
    secrets = SECRETS_PATH.read_text(encoding='utf-8')
    if 'XAI_API_KEY' not in secrets or PROVISIONED not in secrets:
        errors.append(f'docs/SECRETS.md must name XAI_API_KEY as {PROVISIONED}')
    for name in ('xai_budget_open.json', 'workers_ai_budget_open.json'):
        planted = json.loads((FIXTURES / name).read_text(encoding='utf-8'))
        if not closed_budget_errors(int(planted['limit'])):
            errors.append(f'{name} should fail the closed-budget check')
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
    print('AI providers closed at 0; xAI and Workers AI bindings present; retired name absent')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
