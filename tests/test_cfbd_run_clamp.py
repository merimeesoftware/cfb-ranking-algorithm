"""Per-run CFBD ceiling and the remaining-call floor."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from spend_guards import (
    CFBDOfflineError,
    cfbd_max_calls,
    register_live_cfbd_call,
    reset_cfbd_call_count,
)

FIXTURES = Path(__file__).parent / 'fixtures' / 'caps'


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding='utf-8'))


def test_env_above_8_is_clamped(monkeypatch):
    fixture = _load('cfbd_max_calls_above_8.json')
    monkeypatch.setenv('CFBD_MAX_CALLS', fixture['CFBD_MAX_CALLS'])
    monkeypatch.setenv('CFBD_KILL', '0')
    monkeypatch.delenv('SPEND_GATE_HOST', raising=False)
    reset_cfbd_call_count()
    assert cfbd_max_calls() == fixture['expect']
    assert fixture['expect'] == 8
    for _ in range(8):
        register_live_cfbd_call()
    with pytest.raises(CFBDOfflineError):
        register_live_cfbd_call()
    reset_cfbd_call_count()


def _live_response(headers):
    response = MagicMock()
    response.status_code = 200
    response.headers = headers
    response.json.return_value = []
    response.raise_for_status.return_value = None
    return response


def test_remaining_below_floor_stops_the_next_call(monkeypatch):
    fixture = _load('cfbd_remaining_low.json')
    monkeypatch.setenv('CFBD_OFFLINE', '0')
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('CFBD_MAX_CALLS', '8')
    monkeypatch.setenv('CFBD_KILL', '0')
    monkeypatch.delenv('SPEND_GATE_HOST', raising=False)
    reset_cfbd_call_count()
    from api_integration import CFBDApiClient

    client = CFBDApiClient(api_key='test')
    low = _live_response({'X-CallLimit-Remaining': fixture['remaining']})
    with patch('api_integration.requests.get', return_value=low) as mock_get:
        with pytest.raises(CFBDOfflineError):
            client._make_request('/games', {'year': 2026})
        assert mock_get.call_count == 1
        with pytest.raises(CFBDOfflineError):
            client._make_request('/games', {'year': 2026})
        assert mock_get.call_count == 1
    reset_cfbd_call_count()


def test_missing_remaining_header_stops_the_next_call(monkeypatch):
    fixture = _load('cfbd_remaining_missing.json')
    monkeypatch.setenv('CFBD_OFFLINE', '0')
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('CFBD_MAX_CALLS', '8')
    monkeypatch.setenv('CFBD_KILL', '0')
    monkeypatch.delenv('SPEND_GATE_HOST', raising=False)
    reset_cfbd_call_count()
    from api_integration import CFBDApiClient

    client = CFBDApiClient(api_key='test')
    bare = _live_response(fixture['headers'])
    with patch('api_integration.requests.get', return_value=bare) as mock_get:
        with pytest.raises(CFBDOfflineError):
            client._make_request('/info', None)
        with pytest.raises(CFBDOfflineError):
            client._make_request('/info', None)
        assert mock_get.call_count == 1
    reset_cfbd_call_count()
