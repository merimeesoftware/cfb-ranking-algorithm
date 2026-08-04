"""Spend / offline controls for CFBD and AI providers."""
from __future__ import annotations

import os
import threading
import time
from collections import defaultdict
from typing import Any, Dict, Optional


class CFBDOfflineError(RuntimeError):
    """Raised when a live CFBD call is blocked by offline mode or call budget."""


class AIBudgetError(RuntimeError):
    """Raised when the live MiniMax prompt budget is exhausted."""


class AIRateLimitError(RuntimeError):
    """Raised when too many /agent/explain requests hit the rate limit."""


_call_lock = threading.Lock()
_live_call_count = 0
_ai_call_count = 0
_ai_rate_events: Dict[str, list] = defaultdict(list)


def _env_flag(name: str, default: str = '0') -> bool:
    return os.environ.get(name, default).strip().lower() in ('1', 'true', 'yes', 'on')


def _is_development() -> bool:
    return os.environ.get('FLASK_ENV', '').lower() == 'development'


def is_cfbd_offline() -> bool:
    """
    Prefer static/cache; never hit CFBD when offline.

    Default: offline in development when unset; online in production when unset.
    """
    raw = os.environ.get('CFBD_OFFLINE')
    if raw is not None and raw.strip() != '':
        return _env_flag('CFBD_OFFLINE', '0')
    return _is_development()


def cfbd_max_calls() -> Optional[int]:
    """
    Max live CFBD HTTP calls this process.

    In development, defaults to 10 when unset (safety net if CFBD_OFFLINE=0).
    In production, unlimited unless CFBD_MAX_CALLS is set.
    """
    raw = os.environ.get('CFBD_MAX_CALLS', '').strip()
    if raw:
        try:
            return max(0, int(raw))
        except ValueError:
            return None
    if _is_development():
        return 10
    return None


def ai_max_calls() -> Optional[int]:
    """
    Max live MiniMax prompts this process.

    In development, defaults to 3 when unset.
    Stub/off modes never consume this budget.
    """
    raw = os.environ.get('AI_MAX_CALLS', '').strip()
    if raw:
        try:
            return max(0, int(raw))
        except ValueError:
            return None
    if _is_development():
        return 3
    return None


def agent_rate_limit_per_hour() -> int:
    """Per-IP /agent/explain rate limit (all AI modes). Default 20/hour in dev, 30 in prod."""
    raw = os.environ.get('AGENT_RATE_LIMIT', '').strip()
    if raw:
        try:
            return max(0, int(raw))
        except ValueError:
            pass
    return 20 if _is_development() else 30


def reset_cfbd_call_count() -> None:
    global _live_call_count
    with _call_lock:
        _live_call_count = 0


def reset_ai_call_count() -> None:
    global _ai_call_count
    with _call_lock:
        _ai_call_count = 0
        _ai_rate_events.clear()


def get_cfbd_call_count() -> int:
    with _call_lock:
        return _live_call_count


def get_ai_call_count() -> int:
    with _call_lock:
        return _ai_call_count


def register_live_cfbd_call() -> int:
    """Increment and return the new live-call count. Raises if over budget."""
    global _live_call_count
    max_calls = cfbd_max_calls()
    with _call_lock:
        if max_calls is not None and _live_call_count >= max_calls:
            raise CFBDOfflineError(
                f'CFBD live call budget exhausted ({max_calls}). '
                'Raise CFBD_MAX_CALLS or set CFBD_OFFLINE=1 and use static/cache.'
            )
        _live_call_count += 1
        return _live_call_count


def register_live_ai_call() -> int:
    """Increment live MiniMax prompt count. Raises if over budget."""
    global _ai_call_count
    max_calls = ai_max_calls()
    with _call_lock:
        if max_calls is not None and _ai_call_count >= max_calls:
            raise AIBudgetError(
                f'AI live prompt budget exhausted ({max_calls}). '
                'Raise AI_MAX_CALLS or use AI_MODE=stub|off for free template/null responses.'
            )
        _ai_call_count += 1
        return _ai_call_count


def check_agent_rate_limit(client_key: str) -> None:
    """Sliding 1-hour window per client key (usually IP)."""
    limit = agent_rate_limit_per_hour()
    if limit <= 0:
        return
    now = time.time()
    window = 3600.0
    with _call_lock:
        events = _ai_rate_events[client_key]
        _ai_rate_events[client_key] = [t for t in events if now - t < window]
        if len(_ai_rate_events[client_key]) >= limit:
            raise AIRateLimitError(
                f'Agent rate limit exceeded ({limit}/hour). Wait or raise AGENT_RATE_LIMIT.'
            )
        _ai_rate_events[client_key].append(now)


def resolve_ai_mode() -> str:
    """
    AI_MODE: off | stub | live

    Default stub in development, off otherwise (until explicitly enabled in prod).
    """
    raw = os.environ.get('AI_MODE', '').strip().lower()
    if raw in ('off', 'stub', 'live'):
        return raw
    if _is_development():
        return 'stub'
    return 'off'


def spend_status() -> Dict[str, Any]:
    """Snapshot for /agent/health and local smoke checks."""
    return {
        'cfbd_offline': is_cfbd_offline(),
        'cfbd_calls': get_cfbd_call_count(),
        'cfbd_max_calls': cfbd_max_calls(),
        'ai_mode': resolve_ai_mode(),
        'ai_live_calls': get_ai_call_count(),
        'ai_max_calls': ai_max_calls(),
        'agent_rate_limit_per_hour': agent_rate_limit_per_hour(),
        'development': _is_development(),
    }
