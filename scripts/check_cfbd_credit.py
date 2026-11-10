#!/usr/bin/env python3
"""The board must render the CFBD credit, and only one CFBD key name may exist.

The second-key names are assembled here so the rest of the tree can be scanned
for them without this file containing the contiguous token.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CREDIT = 'Data provided by CollegeFootballData.com.'
FOOTER = ROOT / 'frontend' / 'src' / 'lib' / 'components' / 'Footer.svelte'
LAYOUT = ROOT / 'frontend' / 'src' / 'routes' / '+layout.svelte'
BUILD = ROOT / 'frontend' / 'build'
SECOND_KEY = 'CFBD_API_KEY' + '_B'
SLOT_NAME = 'CFBD_API_KEY' + '_SLOT'
SKIP = {'.git', 'node_modules', 'venv', '.venv', '.cache', '__pycache__', '.svelte-kit', 'build'}
TEXT_SUFFIXES = {
    '.py', '.md', '.svelte', '.ts', '.js', '.mjs', '.yml', '.yaml', '.toml',
    '.html', '.txt', '.example', '.json',
}


def names_in(text: str) -> list[str]:
    return [name for name in (SECOND_KEY, SLOT_NAME) if name in text]


def credit_errors(footer: str | None = None, layout: str | None = None) -> list[str]:
    footer_text = FOOTER.read_text(encoding='utf-8') if footer is None else footer
    layout_text = LAYOUT.read_text(encoding='utf-8') if layout is None else layout
    errors: list[str] = []
    if CREDIT not in footer_text:
        errors.append(f'footer must contain {CREDIT!r}')
    if '<Footer' not in layout_text:
        errors.append('the board layout must render Footer')
    return errors


def marked_credit(html: str) -> bool:
    """The sentence has to sit inside the credit element, not elsewhere on the page."""
    pattern = r'<([a-zA-Z0-9]+)[^>]*\bdata-cfbd-credit\b[^>]*>(.*?)</\1>'
    return any(CREDIT in body for _, body in re.findall(pattern, html, flags=re.S))


def built_board_errors(build: Path | None = None) -> list[str]:
    """The prerendered week board and the client layout both include the credit."""
    root = build or BUILD
    weeks = list(root.glob('*/week/*.html'))
    if not weeks:
        return ['built week board HTML is missing']
    week = max(weeks, key=lambda path: int(path.stem) if path.stem.isdigit() else -1)
    page = week.read_text(encoding='utf-8')
    errors: list[str] = []
    if not marked_credit(page):
        errors.append(f'{week} must render the CFBD credit inside data-cfbd-credit')
    client = root / '_app'
    rendered = False
    if client.is_dir():
        for script in client.rglob('*.js'):
            if CREDIT in script.read_text(encoding='utf-8', errors='ignore'):
                rendered = True
                break
    if not rendered:
        errors.append('client bundle must include the CFBD credit for the live board')
    return errors


def forbidden_name_errors() -> list[str]:
    hits: list[str] = []
    for path in ROOT.rglob('*'):
        if not path.is_file() or any(part in SKIP for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name != '.env.example':
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        found = names_in(text)
        if found:
            hits.append(f'{path.relative_to(ROOT)}: {", ".join(found)}')
    return hits


def _build_arg(argv: list[str]) -> Path | None:
    if '--build' not in argv:
        return None
    index = argv.index('--build')
    if index + 1 >= len(argv):
        raise SystemExit('--build needs a directory')
    return Path(argv[index + 1])


def main() -> int:
    built = '--built' in sys.argv
    errors = credit_errors()
    if built:
        errors.extend(built_board_errors(_build_arg(sys.argv[1:])))
    errors.extend(forbidden_name_errors())
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    where = 'built board' if built else 'source'
    print(f'CFBD credit present on the {where}; one CFBD key name')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
