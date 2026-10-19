"""Public board routes serve the precomputed manifest only.

Visitor-chosen formula parameters must not create a new cache key or a live
CFBD recompute. Year and week are accepted only when the manifest lists them.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

BUSY_MESSAGE = 'Busy right now. Try again later.'
FORMULA_MESSAGE = "Same numbers, same time, for everyone. Custom settings aren't accepted."
UNPUBLISHED_MESSAGE = "That week isn't on the board yet."
MISSING_WEEK_MESSAGE = 'year and week are required.'

# Keys that change the solver. Any of these on a public route is a 400.
FORMULA_PARAMS = frozenset({
    'power_conf_initial',
    'group5_initial',
    'fcs_initial',
    'base_factor',
    'hfa_elo',
    'upset_bonus_mult',
    'team_quality_weight',
    'conference_weight',
    'record_weight',
    'prior_strength',
    'use_ats',
    'ats_bonus',
    'use_reference_ranks',
})

# all_divisions is accepted and ignored. It must not trigger a second compute.
ROUTE_ALLOWED = {
    'rankings': frozenset({'year', 'week', 'all_divisions'}),
    'matchup': frozenset({'year', 'week', 'team_a', 'team_b', 'a', 'b', 'market_spread'}),
    'weeks': frozenset({'year'}),
    'team': frozenset({'year', 'week'}),
}

_REPO_ROOT = Path(__file__).resolve().parent
_DEFAULT_MANIFEST = _REPO_ROOT / 'frontend' / 'static' / 'rankings' / 'manifest.json'


def load_manifest(path: Optional[os.PathLike] = None) -> Dict[str, Any]:
    """Load the published year/week manifest. Missing or broken file → nothing published."""
    if path is None:
        override = os.environ.get('RANKINGS_MANIFEST_PATH', '').strip()
        manifest_path = Path(override) if override else _DEFAULT_MANIFEST
    else:
        manifest_path = Path(path)
    try:
        payload = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return {'years': {}}
    if not isinstance(payload, dict):
        return {'years': {}}
    years = payload.get('years')
    if not isinstance(years, dict):
        return {'years': {}}
    return {'years': years}


def published_weeks(manifest: Mapping[str, Any], year: int) -> list:
    raw = (manifest.get('years') or {}).get(str(year))
    if not isinstance(raw, list):
        return []
    weeks = []
    for item in raw:
        try:
            weeks.append(int(item))
        except (TypeError, ValueError):
            continue
    return weeks


def is_published(manifest: Mapping[str, Any], year: int, week: int) -> bool:
    return week in published_weeks(manifest, year)


def _read_int(args: Mapping[str, Any], name: str) -> Tuple[Optional[int], bool]:
    """Return (value, present). Value is None when missing or not an integer."""
    if name not in args:
        return None, False
    raw = args.get(name)
    if raw is None or str(raw).strip() == '':
        return None, True
    try:
        return int(str(raw).strip()), True
    except (TypeError, ValueError):
        return None, True


def rejected_param_names(route: str, args: Mapping[str, Any]) -> list:
    allowed = ROUTE_ALLOWED[route]
    names = []
    for key in args.keys():
        if key in FORMULA_PARAMS or key not in allowed:
            names.append(str(key))
    return names


def busy_body(code: str) -> Dict[str, Any]:
    return {
        'busy': True,
        'capped': True,
        'message': BUSY_MESSAGE,
        'code': code,
    }


def evaluate_public_query(
    route: str,
    args: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> Tuple[Optional[Dict[str, Any]], Optional[Tuple[Dict[str, Any], int]]]:
    """
    Validate a public rankings/matchup/weeks/team query.

    Returns (parsed, None) when the request may be served from precomputed files.
    Returns (None, (body, status)) when it must be rejected.
    """
    if route not in ROUTE_ALLOWED:
        raise ValueError(f'unknown public route {route}')

    rejected = rejected_param_names(route, args)
    if rejected:
        return None, ({
            'error': FORMULA_MESSAGE,
            'code': 'formula_params',
            'rejected': rejected,
        }, 400)

    year, year_present = _read_int(args, 'year')
    week, week_present = _read_int(args, 'week')

    if year_present and year is None:
        return None, ({'error': 'year must be an integer.', 'code': 'bad_year'}, 400)
    if week_present and week is None:
        return None, ({'error': 'week must be an integer.', 'code': 'bad_week'}, 400)

    if route == 'weeks':
        if year is None:
            return None, ({'error': 'year is required.', 'code': 'missing_year'}, 400)
        weeks = published_weeks(manifest, year)
        if not weeks:
            return None, ({
                'year': year,
                'weeks': [],
                'max_week': 0,
                'published': False,
                'message': UNPUBLISHED_MESSAGE,
            }, 200)
        return {
            'route': route,
            'year': year,
            'weeks': weeks,
            'max_week': max(weeks),
        }, None

    if year is None or week is None:
        return None, ({'error': MISSING_WEEK_MESSAGE, 'code': 'missing_week'}, 400)

    if not is_published(manifest, year, week):
        return None, ({
            'published': False,
            'busy': False,
            'message': UNPUBLISHED_MESSAGE,
            'code': 'not_published',
            'year': year,
            'week': week,
            'team_rankings': [],
            'conference_rankings': [],
        }, 200)

    return {'route': route, 'year': year, 'week': week}, None
