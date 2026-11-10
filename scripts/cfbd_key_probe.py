#!/usr/bin/env python3
"""One authenticated GET /info. Prints patronLevel and remainingCalls only.

The key is masked and never written to a file, a log line, or the result.
A rejected key fails the process.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

INFO_URL = 'https://api.collegefootballdata.com/info'


def mask_key(key: str) -> None:
    """GitHub Actions treats this line as a mask command, not a log of the key."""
    if key:
        sys.stdout.write(f'::add-mask::{key}\n')
        sys.stdout.flush()


def probe(opener=None) -> int:
    opener = opener or urllib.request.urlopen
    key = os.environ.get('CFBD_API_KEY', '').strip()
    mask_key(key)
    if not key:
        print('CFBD rejected the key')
        return 1
    request = urllib.request.Request(
        INFO_URL,
        headers={
            'Authorization': f'Bearer {key}',
            'Accept': 'application/json',
        },
        method='GET',
    )
    try:
        with opener(request, timeout=30) as response:
            status = getattr(response, 'status', 200)
            raw = response.read()
    except urllib.error.HTTPError as exc:
        print(f'CFBD rejected the key (HTTP {exc.code})')
        return 1
    except urllib.error.URLError:
        print('CFBD rejected the key')
        return 1
    if status in (401, 403):
        print(f'CFBD rejected the key (HTTP {status})')
        return 1
    try:
        payload = json.loads(raw.decode('utf-8'))
    except (UnicodeError, json.JSONDecodeError):
        print('CFBD rejected the key')
        return 1
    if not isinstance(payload, dict):
        print('CFBD rejected the key')
        return 1
    if 'patronLevel' not in payload or 'remainingCalls' not in payload:
        print('CFBD rejected the key')
        return 1
    print(f'patronLevel={payload["patronLevel"]}')
    print(f'remainingCalls={payload["remainingCalls"]}')
    return 0


def main() -> int:
    return probe()


if __name__ == '__main__':
    raise SystemExit(main())
