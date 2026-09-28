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

# Allowlist for path segments. CFB weeks stay in 0–20 (regular + postseason).
_YEAR_MIN = 1869
_YEAR_MAX = 2100
_WEEK_MIN = 0
_WEEK_MAX = 20
_FILE_SUFFIXES = ('json', 'story.json', 'why.json', 'share.json', 'climb.json')


def _root_prefix(root: Optional[Union[str, Path]]) -> str:
    base = Path(root) if root is not None else Path(DEFAULT_ROOT)
    base_norm = os.path.normpath(str(base))
    if base_norm.endswith(os.sep):
        return base_norm
    return base_norm + os.sep


def _relative_name(year: int, week: int, suffix: str) -> str:
    """Allowlisted ``YYYY/week-N.<suffix>`` segment (digits only)."""
    if suffix not in _FILE_SUFFIXES:
        raise ValueError('unsupported static rankings suffix')
    if type(year) is not int or type(week) is not int:
        raise ValueError('year and week must be integers')
    if not (_YEAR_MIN <= year <= _YEAR_MAX and _WEEK_MIN <= week <= _WEEK_MAX):
        raise ValueError('year or week is outside the allowed range')
    return os.path.join(str(year), f'week-{week}.{suffix}')


def _contained_fullpath(
    year: int,
    week: int,
    suffix: str,
    root: Optional[Union[str, Path]],
) -> str:
    """Normalize and require the file to stay under the rankings root."""
    relative = _relative_name(year, week, suffix)
    base = Path(root) if root is not None else Path(DEFAULT_ROOT)
    base_norm = os.path.normpath(str(base))
    fullpath = os.path.normpath(os.path.join(base_norm, relative))
    if not fullpath.startswith(_root_prefix(root)):
        raise ValueError('static rankings path escapes the allowed root')
    return fullpath


def static_path_for(
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Path:
    return Path(_contained_fullpath(year, week, 'json', root))


def _write_contained(
    payload: Dict[str, Any],
    year: int,
    week: int,
    suffix: str,
    root: Optional[Union[str, Path]],
    *,
    pretty: bool,
) -> Path:
    fullpath = _contained_fullpath(year, week, suffix, root)
    # Re-check the normalized path in this function, immediately before IO.
    fullpath = os.path.normpath(fullpath)
    if not fullpath.startswith(_root_prefix(root)):
        raise ValueError('static rankings path escapes the allowed root')
    os.makedirs(os.path.dirname(fullpath), exist_ok=True)
    with open(fullpath, 'w', encoding='utf-8') as handle:
        if pretty:
            json.dump(payload, handle, indent=2)
            handle.write('\n')
        else:
            json.dump(payload, handle, separators=(',', ':'))
    return Path(fullpath)


def _read_contained(
    year: int,
    week: int,
    suffix: str,
    root: Optional[Union[str, Path]],
) -> Optional[Dict[str, Any]]:
    try:
        fullpath = _contained_fullpath(year, week, suffix, root)
    except ValueError:
        return None
    # Re-check the normalized path in this function, immediately before IO.
    fullpath = os.path.normpath(fullpath)
    prefix = _root_prefix(root)
    if not fullpath.startswith(prefix):
        return None
    if not os.path.exists(fullpath):
        return None
    try:
        with open(fullpath, 'r', encoding='utf-8') as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError):
        return None


def write_static_rankings(
    payload: Dict[str, Any],
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Path:
    return _write_contained(payload, year, week, 'json', root, pretty=False)


def read_static_rankings(
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    return _read_contained(year, week, 'json', root)


def read_static_rankings_any(
    year: int,
    week: int,
) -> Optional[Dict[str, Any]]:
    """Prefer SPA static copy, then STATIC_RANKINGS_DIR / static_rankings/."""
    frontend = Path(__file__).resolve().parent / 'frontend' / 'static' / 'rankings'
    for root in (frontend, Path(DEFAULT_ROOT)):
        data = read_static_rankings(year, week, root=root)
        if data is not None:
            return data
    return None


def story_path_for(
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Path:
    return Path(_contained_fullpath(year, week, 'story.json', root))


def why_path_for(
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Path:
    return Path(_contained_fullpath(year, week, 'why.json', root))


def share_path_for(
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Path:
    return Path(_contained_fullpath(year, week, 'share.json', root))


def climb_path_for(
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Path:
    return Path(_contained_fullpath(year, week, 'climb.json', root))


def read_week_story(
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """Load precomputed week-{n}.story.json if present."""
    return _read_contained(year, week, 'story.json', root)


def read_why_blurbs(
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """Load precomputed week-{n}.why.json if present."""
    return _read_contained(year, week, 'why.json', root)


def write_week_story(
    payload: Dict[str, Any],
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Path:
    return _write_contained(payload, year, week, 'story.json', root, pretty=True)


def write_why_blurbs(
    payload: Dict[str, Any],
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Path:
    return _write_contained(payload, year, week, 'why.json', root, pretty=True)


def read_share_blurbs(
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """Load precomputed week-{n}.share.json if present."""
    return _read_contained(year, week, 'share.json', root)


def read_climb_blurbs(
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """Load precomputed week-{n}.climb.json if present."""
    return _read_contained(year, week, 'climb.json', root)


def write_share_blurbs(
    payload: Dict[str, Any],
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Path:
    return _write_contained(payload, year, week, 'share.json', root, pretty=True)


def write_climb_blurbs(
    payload: Dict[str, Any],
    year: int,
    week: int,
    root: Optional[Union[str, Path]] = None,
) -> Path:
    return _write_contained(payload, year, week, 'climb.json', root, pretty=True)


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
