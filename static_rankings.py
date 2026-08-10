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


def story_path_for(
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Path:
    base = Path(root) if root is not None else Path(DEFAULT_ROOT)
    return base / str(year) / f"week-{week}.story.json"


def why_path_for(
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Path:
    base = Path(root) if root is not None else Path(DEFAULT_ROOT)
    return base / str(year) / f"week-{week}.why.json"


def share_path_for(
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Path:
    base = Path(root) if root is not None else Path(DEFAULT_ROOT)
    return base / str(year) / f"week-{week}.share.json"


def climb_path_for(
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Path:
    base = Path(root) if root is not None else Path(DEFAULT_ROOT)
    return base / str(year) / f"week-{week}.climb.json"


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def read_week_story(
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """Load precomputed week-{n}.story.json if present."""
    return _read_json(story_path_for(year, week, root=root))


def read_why_blurbs(
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """Load precomputed week-{n}.why.json if present."""
    return _read_json(why_path_for(year, week, root=root))


def write_week_story(
    payload: Dict[str, Any],
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Path:
    path = story_path_for(year, week, root=root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
        f.write('\n')
    return path


def write_why_blurbs(
    payload: Dict[str, Any],
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Path:
    path = why_path_for(year, week, root=root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
        f.write('\n')
    return path


def _write_kind_blurbs(
    path: Path,
    payload: Dict[str, Any],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
        f.write('\n')
    return path


def read_share_blurbs(
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """Load precomputed week-{n}.share.json if present."""
    return _read_json(share_path_for(year, week, root=root))


def read_climb_blurbs(
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """Load precomputed week-{n}.climb.json if present."""
    return _read_json(climb_path_for(year, week, root=root))


def write_share_blurbs(
    payload: Dict[str, Any],
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Path:
    return _write_kind_blurbs(share_path_for(year, week, root=root), payload)


def write_climb_blurbs(
    payload: Dict[str, Any],
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Path:
    return _write_kind_blurbs(climb_path_for(year, week, root=root), payload)


def team_blurb_from_static(
    payload: Optional[Dict[str, Any]],
    team_name: str,
    *,
    require_period: Optional[str] = None,
) -> Optional[str]:
    """
    Return a team's blurb from a share/climb static payload.

    When require_period is set, the file's period must match (daily freshness).
    Lookback files may omit period matching by passing require_period=None and
    treating any existing team entry as durable.
    """
    if not payload or not isinstance(payload, dict):
        return None
    if require_period is not None and payload.get('period') != require_period:
        return None
    blurbs = payload.get('blurbs') or {}
    if not isinstance(blurbs, dict):
        return None
    if team_name in blurbs and blurbs[team_name]:
        return str(blurbs[team_name])
    # Case-insensitive fallback
    lower = team_name.lower()
    for name, text in blurbs.items():
        if str(name).lower() == lower and text:
            return str(text)
    return None
