#!/usr/bin/env python3
"""Fail when a committed week board's algo stamp is not ALGO_VERSION.

Priors stay the v5.3 blend seed and are not week boards. Story, why, share,
and climb files are not boards. 2025 has no week boards here; this check
does not create any.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ranking_service import ALGO_VERSION

WEEK_FILE = re.compile(r'^week-(\d+)\.json$')
DEFAULT_ROOT = ROOT / 'frontend' / 'static' / 'rankings'


def board_stamp_errors(root: Path, algo: str = ALGO_VERSION) -> list[str]:
    """Week files under ``root`` whose stamp is not ``algo``."""
    if not root.is_dir():
        return [f'{root} is not a rankings directory']
    errors: list[str] = []
    for path in sorted(root.rglob('week-*.json')):
        if not WEEK_FILE.match(path.name):
            continue
        if 'priors' in path.parts:
            continue
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f'{path}: {exc}')
            continue
        stamped = payload.get('algo') if isinstance(payload, dict) else None
        if stamped != algo:
            errors.append(f'{path}: algo {stamped!r} != {algo}')
    return errors


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[0]) if args else DEFAULT_ROOT
    errors = board_stamp_errors(root)
    if errors:
        print(f'{len(errors)} week board(s) are not {ALGO_VERSION}:', file=sys.stderr)
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f'Week boards under {root} are {ALGO_VERSION}.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
