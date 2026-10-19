"""Spend / offline controls for CFBD, xAI, and Workers AI."""
from __future__ import annotations

import os
import threading
import time
from collections import defaultdict
from typing import Any, Dict, Optional


class CFBDOfflineError(RuntimeError):
    """Raised when a live CFBD call is blocked by offline mode or call budget."""


class AIBudgetError(RuntimeError):
    """Raised when a live xAI or Workers AI prompt is refused."""


class AIRateLimitError(RuntimeError):
    """Raised when too many /agent/explain requests hit the rate limit."""


# In-code defaults. Unset env must never mean unlimited.
# These match the Worker daily budget on the spend-budget instance.
AI_PROVIDERS = ('xai', 'workers_ai')
DEFAULT_XAI_MAX_CALLS = 0
DEFAULT_WORKERS_AI_MAX_CALLS = 0
DEFAULT_CFBD_MAX_CALLS = 25

_call_lock = threading.Lock()
_live_call_count = 0
_live_call_day = ''
_provider_counts = {'xai': 0, 'workers_ai': 0}
_provider_days = {'xai': '', 'workers_ai': ''}
_ai_rate_events: Dict[str, list] = defaultdict(list)


def _env_flag(name: str, default: str = '0') -> bool:
    return os.environ.get(name, default).strip().lower() in ('1', 'true', 'yes', 'on')


def _parse_cap(raw: str, default: int) -> int:
    """Blank or garbage configuration falls back to the in-code default."""
    text = (raw or '').strip()
    if not text:
        return default
    try:
        return max(0, int(text))
    except ValueError:
        return default


def _utc_day() -> str:
    return time.strftime('%Y-%m-%d', time.gmtime())


def _is_development() -> bool:
    return os.environ.get('FLASK_ENV', '').lower() == 'development'


def is_ai_killed() -> bool:
    """AI_KILL=1 stops every live xAI and Workers AI call."""
    return _env_flag('AI_KILL', '0')


def is_provider_killed(provider: str) -> bool:
    """AI_KILL covers both providers. Each provider also has its own flag."""
    if is_ai_killed():
        return True
    if provider == 'xai':
        return _env_flag('XAI_KILL', '0')
    if provider == 'workers_ai':
        return _env_flag('WORKERS_AI_KILL', '0')
    return True


def is_cfbd_killed() -> bool:
    """CFBD_KILL=1 stops every live collegefootballdata.com call."""
    return _env_flag('CFBD_KILL', '0')


def is_cfbd_offline() -> bool:
    """
    Prefer static/cache; never hit CFBD when offline or killed.

    Default: offline in development when unset; online in production when unset.
    CFBD_KILL=1 forces offline even when CFBD_OFFLINE=0.
    """
    if is_cfbd_killed():
        return True
    raw = os.environ.get('CFBD_OFFLINE')
    if raw is not None and raw.strip() != '':
        return _env_flag('CFBD_OFFLINE', '0')
    return _is_development()


def cfbd_max_calls() -> int:
    """
    Max live CFBD HTTP calls this process per UTC day.

    Unset, blank, or invalid CFBD_MAX_CALLS uses DEFAULT_CFBD_MAX_CALLS (25).
    Never unlimited. The Worker Durable Object enforces the same number globally.
    """
    return _parse_cap(os.environ.get('CFBD_MAX_CALLS', ''), DEFAULT_CFBD_MAX_CALLS)


def provider_max_calls(provider: str) -> int:
    """
    Max live prompts for one provider this process per UTC day.

    Unset, blank, or invalid values use the in-code default of 0.
    Never unlimited. Stub/off modes never consume this budget.
    """
    if provider == 'xai':
        return _parse_cap(os.environ.get('XAI_MAX_CALLS', ''), DEFAULT_XAI_MAX_CALLS)
    if provider == 'workers_ai':
        return _parse_cap(
            os.environ.get('WORKERS_AI_MAX_CALLS', ''),
            DEFAULT_WORKERS_AI_MAX_CALLS,
        )
    return 0


def resolve_ai_provider(explicit: Optional[str] = None) -> str:
    """AI_PROVIDER selects the live path. Unknown values fall back to workers_ai."""
    raw = (explicit if explicit is not None else os.environ.get('AI_PROVIDER', ''))
    provider = (raw or 'workers_ai').strip().lower()
    if provider not in AI_PROVIDERS:
        return 'workers_ai'
    return provider


def agent_rate_limit_per_hour() -> int:
    """Per-IP /agent rate limit (all AI modes), keyed on CF-Connecting-IP.

    Unset or invalid AGENT_RATE_LIMIT uses 50/hour in development and 30/hour
    in production. An explicit 0 blocks further agent calls. Never unlimited.
    """
    raw = os.environ.get('AGENT_RATE_LIMIT', '').strip()
    if raw:
        return _parse_cap(raw, 50 if _is_development() else 30)
    return 50 if _is_development() else 30


def resolve_cfbd_api_key(explicit: Optional[str] = None) -> str:
    """Pick active CFBD key from dual-account slots.

    Env:
      CFBD_API_KEY      — account A (default)
      CFBD_API_KEY_B    — account B (optional second 1k/mo quota)
      CFBD_API_KEY_SLOT — ``A`` (default) or ``B``

    Each collegefootballdata.com account has its own monthly call budget.
    Flip ``CFBD_API_KEY_SLOT=B`` (with ``CFBD_API_KEY_B`` set) to burn the
    second quota without rotating secrets.
    """
    if explicit:
        return explicit
    slot = os.environ.get('CFBD_API_KEY_SLOT', 'A').strip().upper() or 'A'
    if slot == 'B':
        key = os.environ.get('CFBD_API_KEY_B') or os.environ.get('CFBD_API_KEY')
    else:
        key = os.environ.get('CFBD_API_KEY')
        if not key:
            key = os.environ.get('CFBD_API_KEY_B')
    return key or ''


def cfbd_key_slot_status() -> Dict[str, Any]:
    """Non-secret status for /agent/health and warm scripts."""
    slot = os.environ.get('CFBD_API_KEY_SLOT', 'A').strip().upper() or 'A'
    if slot not in ('A', 'B'):
        slot = 'A'
    has_a = bool(os.environ.get('CFBD_API_KEY'))
    has_b = bool(os.environ.get('CFBD_API_KEY_B'))
    return {
        'slot': slot,
        'has_key_a': has_a,
        'has_key_b': has_b,
        'active_configured': bool(resolve_cfbd_api_key()),
    }


def reset_cfbd_call_count() -> None:
    global _live_call_count, _live_call_day
    with _call_lock:
        _live_call_count = 0
        _live_call_day = _utc_day()


def reset_provider_call_counts() -> None:
    with _call_lock:
        today = _utc_day()
        for provider in AI_PROVIDERS:
            _provider_counts[provider] = 0
            _provider_days[provider] = today
        _ai_rate_events.clear()


def get_cfbd_call_count() -> int:
    with _call_lock:
        return _live_call_count


def get_provider_call_count(provider: str) -> int:
    with _call_lock:
        return _provider_counts.get(provider, 0)


def _consume_global_budget(bucket: str) -> None:
    """Ask the Worker Durable Object before a live paid call.

    No-op when SPEND_GATE_HOST is unset (local, CI, precompute). When the gate
    is configured, an unreachable gate fails closed.
    """
    host = os.environ.get('SPEND_GATE_HOST', '').strip()
    if not host:
        return
    import json
    import urllib.error
    import urllib.request

    url = f'http://{host}/consume'
    payload = json.dumps({'bucket': bucket}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={'content-type': 'application/json'},
        method='POST',
    )
    error_cls = CFBDOfflineError if bucket == 'cfbd' else AIBudgetError
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read().decode() or '{}')
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode() or '{}')
        except (json.JSONDecodeError, OSError):
            body = {}
        if not body.get('ok', False):
            raise error_cls(
                f'{bucket} daily budget or kill switch denied the live call.'
            ) from exc
        return
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        raise error_cls(f'{bucket} spend gate unreachable; live call refused.') from exc
    if not body.get('ok', False):
        raise error_cls(f'{bucket} daily budget exhausted.')


def register_live_cfbd_call() -> int:
    """Increment and return the new live-call count. Raises if over budget."""
    global _live_call_count, _live_call_day
    if is_cfbd_killed():
        raise CFBDOfflineError('CFBD kill switch is on. Live calls are stopped.')
    max_calls = cfbd_max_calls()
    with _call_lock:
        today = _utc_day()
        if _live_call_day != today:
            _live_call_count = 0
            _live_call_day = today
        if _live_call_count >= max_calls:
            raise CFBDOfflineError(
                f'CFBD live call budget exhausted ({max_calls}). '
                'Raise CFBD_MAX_CALLS or set CFBD_OFFLINE=1 and use static/cache.'
            )
    _consume_global_budget('cfbd')
    with _call_lock:
        today = _utc_day()
        if _live_call_day != today:
            _live_call_count = 0
            _live_call_day = today
        if _live_call_count >= max_calls:
            raise CFBDOfflineError(
                f'CFBD live call budget exhausted ({max_calls}). '
                'Raise CFBD_MAX_CALLS or set CFBD_OFFLINE=1 and use static/cache.'
            )
        _live_call_count += 1
        return _live_call_count


def register_live_provider_call(provider: str) -> int:
    """Increment one provider's live prompt count. Raises if over budget or killed."""
    if provider not in AI_PROVIDERS:
        raise AIBudgetError(f'Unknown AI provider: {provider}')
    if is_provider_killed(provider):
        raise AIBudgetError('AI kill switch is on. Live calls are stopped.')
    max_calls = provider_max_calls(provider)
    with _call_lock:
        today = _utc_day()
        if _provider_days[provider] != today:
            _provider_counts[provider] = 0
            _provider_days[provider] = today
        if _provider_counts[provider] >= max_calls:
            raise AIBudgetError(
                f'{provider} live prompt budget exhausted ({max_calls}). '
                'Raise the provider cap or use AI_MODE=stub.'
            )
    _consume_global_budget(provider)
    with _call_lock:
        today = _utc_day()
        if _provider_days[provider] != today:
            _provider_counts[provider] = 0
            _provider_days[provider] = today
        if _provider_counts[provider] >= max_calls:
            raise AIBudgetError(
                f'{provider} live prompt budget exhausted ({max_calls}). '
                'Raise the provider cap or use AI_MODE=stub.'
            )
        _provider_counts[provider] += 1
        return _provider_counts[provider]


def check_agent_rate_limit(client_key: str) -> None:
    """Sliding 1-hour window per CF-Connecting-IP. Never unlimited."""
    limit = agent_rate_limit_per_hour()
    if limit <= 0:
        raise AIRateLimitError(
            'Agent rate limit is closed. Wait or raise AGENT_RATE_LIMIT.'
        )
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
        'cfbd_key': cfbd_key_slot_status(),
        'ai_mode': resolve_ai_mode(),
        'ai_provider': resolve_ai_provider(),
        'xai_live_calls': get_provider_call_count('xai'),
        'xai_max_calls': provider_max_calls('xai'),
        'workers_ai_live_calls': get_provider_call_count('workers_ai'),
        'workers_ai_max_calls': provider_max_calls('workers_ai'),
        'agent_rate_limit_per_hour': agent_rate_limit_per_hour(),
        'development': _is_development(),
    }
