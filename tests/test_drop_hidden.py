"""The closed Drop is not a form. Visitors never see the signup failure."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'frontend' / 'src'
BANNED = (
    'Could not subscribe right now.',
    'DropSignup',
    'Get The Drop',
    '#the-drop',
    'id="the-drop"',
)


def _hits(root: Path, suffixes: set[str] | None = None) -> list[str]:
    found = []
    if not root.exists():
        return found
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        if suffixes is not None and path.suffix not in suffixes:
            continue
        text = path.read_text(encoding='utf-8', errors='replace')
        for needle in BANNED:
            if needle in text:
                found.append(f'{path.relative_to(ROOT)}: {needle}')
    return found


def test_drop_form_is_not_rendered():
    assert _hits(SRC) == []
    built = _hits(ROOT / 'frontend' / 'build', {'.html', '.js', '.css'})
    assert built == []
