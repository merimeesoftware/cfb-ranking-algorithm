"""
Static rankings storage for archived weeks (hybrid architecture).

Precompute writes JSON under STATIC_RANKINGS_DIR (default: static_rankings/).
Flask serves these for archived weeks; frontend can also fetch from
/static-rankings/ when files are copied into frontend/static/rankings/.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

DEFAULT_ROOT = os.environ.get(
    'STATIC_RANKINGS_DIR',
    os.path.join(os.path.dirname(__file__), 'static_rankings'),
)


def static_path_for(
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Path:
    base = Path(root) if root is not None else Path(DEFAULT_ROOT)
    return base / str(year) / f"week-{week}.json"


def write_static_rankings(
    payload: Dict[str, Any],
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Path:
    path = static_path_for(year, week, root=root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, separators=(',', ':'))
    return path


def read_static_rankings(
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    path = static_path_for(year, week, root=root)
    if not path.exists():
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
