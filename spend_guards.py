"""Spend / offline controls for CFBD and AI providers."""
from __future__ import annotations

import os
import threading
from typing import Optional


class CFBDOfflineError(RuntimeError):
    """Raised when a live CFBD call is blocked by offline mode or call budget."""


_call_lock = threading.Lock()
_live_call_count = 0


def _env_flag(name: str, default: str = '0') -> bool:
    return os.environ.get(name, default).strip().lower() in ('1', 'true', 'yes', 'on')


def is_cfbd_offline() -> bool:
    """
    Prefer static/cache; never hit CFBD when offline.

    Default: offline in development (FLASK_ENV=development) when unset;
    online in production when unset.
    """
    raw = os.environ.get('CFBD_OFFLINE')
    if raw is not None and raw.strip() != '':
        return _env_flag('CFBD_OFFLINE', '0')
    flask_env = os.environ.get('FLASK_ENV', '').lower()
    return flask_env == 'development'


def cfbd_max_calls() -> Optional[int]:
    raw = os.environ.get('CFBD_MAX_CALLS', '').strip()
    if not raw:
        return None
    try:
        return max(0, int(raw))
    except ValueError:
        return None


def reset_cfbd_call_count() -> None:
    global _live_call_count
    with _call_lock:
        _live_call_count = 0


def get_cfbd_call_count() -> int:
    with _call_lock:
        return _live_call_count


def register_live_cfbd_call() -> int:
    """Increment and return the new live-call count. Raises if over budget."""
    global _live_call_count
    max_calls = cfbd_max_calls()
    with _call_lock:
        if max_calls is not None and _live_call_count >= max_calls:
            raise CFBDOfflineError(
                f'CFBD live call budget exhausted ({max_calls}). '
                'Set CFBD_MAX_CALLS higher or use CFBD_OFFLINE=1 with cache/static.'
            )
        _live_call_count += 1
        return _live_call_count


def resolve_ai_mode() -> str:
    """
    AI_MODE: off | stub | live

    Default stub in development, off otherwise (until explicitly enabled in prod).
    """
    raw = os.environ.get('AI_MODE', '').strip().lower()
    if raw in ('off', 'stub', 'live'):
        return raw
    if os.environ.get('FLASK_ENV', '').lower() == 'development':
        return 'stub'
    return 'off'
