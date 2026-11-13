#!/usr/bin/env python3
"""Fail when a committee file is not hand-entered rows.

Committee files never carry ALGO_VERSION. A ``week-N.json`` name is a board
name and fails this check. 2025 is refused. The rankings manifest is not a
committee index. This script does not call CFBD.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from committee_ingest import WEEK_FILE, YEAR_FILE, committee_errors, path_is_sealed
from ranking_service import ALGO_VERSION

VALID_DIR = ROOT / 'tests' / 'fixtures' / 'committee' / 'valid'
RANKINGS_ROOT = ROOT / 'frontend' / 'static' / 'rankings'
STAMPS = (ALGO_VERSION, 'v5.5')


def file_errors(path: Path, stamps: tuple[str, ...] = STAMPS) -> list[str]:
    """Errors for one committee file, including a board-shaped name."""
    errors: list[str] = []
    if WEEK_FILE.match(path.name) or not YEAR_FILE.match(path.name):
        errors.append(f'{path}: committee files are named {{year}}.json, not week-N.json')
    if path_is_sealed(path):
        errors.append(f'{path}: 2025 is the sealed holdout.')
        return errors
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f'{path}: {exc}')
        return errors
    for error in committee_errors(payload, filename=path.name, forbidden_stamps=stamps):
        errors.append(f'{path}: {error}')
    return errors


def directory_errors(directory: Path, stamps: tuple[str, ...] = STAMPS) -> list[str]:
    """Errors for a directory of ``{year}.json`` committee files."""
    if not directory.is_dir():
        return [f'{directory} is not a committee directory']
    files = [path for path in sorted(directory.rglob('*')) if path.is_file()]
    if not files:
        return [f'{directory} has no committee files']
    errors: list[str] = []
    for path in files:
        if path.parent != directory or path.suffix != '.json':
            errors.append(f'{path}: committee files are {{year}}.json in one directory')
            continue
        errors.extend(file_errors(path, stamps))
    return errors


def published_errors(rankings_root: Path, stamps: tuple[str, ...] = STAMPS) -> list[str]:
    """Errors for a rankings tree. A missing committee directory is fine."""
    errors: list[str] = []
    manifest = rankings_root / 'manifest.json'
    if manifest.is_file() and 'committee' in manifest.read_text(encoding='utf-8').casefold():
        errors.append(f'{manifest}: committee files stay out of the manifest')
    committee = rankings_root / 'committee'
    if not committee.exists():
        return errors
    if not committee.is_dir():
        return errors + [f'{committee} is not a directory']
    files = [path for path in sorted(committee.rglob('*')) if path.is_file()]
    for path in files:
        if path.parent != committee:
            errors.append(f'{path}: nested committee files are refused')
            continue
        errors.extend(file_errors(path, stamps))
    return errors


def default_errors() -> list[str]:
    """The committed fixture must pass, and the published tree must stay clean."""
    return directory_errors(VALID_DIR) + published_errors(RANKINGS_ROOT)


def errors_for_path(path: Path) -> list[str]:
    """A file, a rankings tree, or a directory of ``{year}.json`` files."""
    if path.is_file():
        return file_errors(path)
    rankings_tree = path.is_dir() and (
        (path / 'manifest.json').is_file() or (path / 'committee').is_dir()
    )
    if rankings_tree:
        return published_errors(path)
    return directory_errors(path)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        errors = default_errors()
    else:
        errors = []
        for arg in args:
            errors.extend(errors_for_path(Path(arg)))
    if errors:
        print(f'{len(errors)} committee file error(s):', file=sys.stderr)
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print('Committee files are hand-entered rows and are not boards.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
