"""Cold scheduled precompute when CFBD omits X-CallLimit-Remaining.

Run 40184922420 died on the first /teams response because that header was
absent. The scheduled step is ``python scripts/precompute_rankings.py
--current`` with CFBD_MAX_CALLS=8 and no restored cache.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import precompute_rankings as pre
from spend_guards import get_cfbd_call_count, reset_cfbd_call_count

FRONTEND = ROOT / 'frontend' / 'static' / 'rankings'
PRIVATE = ROOT / 'static_rankings'
WHEN = datetime(2026, 10, 25, 10, 28)


class _Response:
    def __init__(self, payload, headers):
        self.status_code = 200
        self.headers = headers
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


def _team(school, conference):
    return {
        'school': school,
        'id': school,
        'conference': conference,
        'mascot': school,
        'abbreviation': school[:3].upper(),
        'color': '#111111',
        'alternateColor': '#eeeeee',
        'logos': [],
        'classification': 'fbs',
    }


def _game(year, week):
    return {
        'id': year * 100 + week,
        'completed': True,
        'week': week,
        'season': year,
        'homeTeam': 'Alpha',
        'awayTeam': 'Beta',
        'homePoints': 28,
        'awayPoints': 14,
        'homeConference': 'SEC',
        'awayConference': 'Big Ten',
        'seasonType': 'regular',
        'startDate': f'{year}-09-{week:02d}T16:00:00.000Z',
        'neutralSite': False,
        'notes': '',
    }


def _payload(url, params):
    if url.endswith('/teams'):
        return [
            _team('Alpha', 'SEC'),
            _team('Beta', 'Big Ten'),
        ]
    if url.endswith('/games'):
        year = int(params['year'])
        if year == 2026:
            return [_game(year, week) for week in (1, 2, 3)]
        return [_game(year, 1)]
    raise AssertionError(f'unexpected CFBD url {url}')


def _snapshot(root: Path) -> dict:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob('*')
        if path.is_file()
    }


def _run(monkeypatch, tmp_path, headers):
    import api_integration
    import ranking_service
    import static_rankings
    from cache import get_cache

    output = tmp_path / 'output'
    static = tmp_path / 'static'
    calls = []
    cache = get_cache()
    saved_memory = dict(cache._memory_cache)
    saved_index = {key: list(values) for key, values in cache._prefix_index.items()}
    cache._memory_cache.clear()
    cache._prefix_index.clear()
    frontend_before = _snapshot(FRONTEND)
    private_before = _snapshot(PRIVATE)
    private_existed = PRIVATE.exists()

    def fake_get(url, headers=None, params=None, timeout=None):
        del headers, timeout
        calls.append(url)
        return _Response(_payload(url, params), response_headers)

    response_headers = dict(headers)
    monkeypatch.setattr(api_integration.requests, 'get', fake_get)
    monkeypatch.setattr(pre, 'now_utc', lambda: WHEN)
    # Computed boards also write through DEFAULT_ROOT. Point that at tmp,
    # and pin the TTLs so this run's batch assignments are undone afterward.
    monkeypatch.setattr(static_rankings, 'DEFAULT_ROOT', str(output))
    monkeypatch.setattr(api_integration, 'get_games_ttl', api_integration.get_games_ttl)
    monkeypatch.setattr(api_integration, 'TTL_TEAMS', api_integration.TTL_TEAMS)
    monkeypatch.setattr(ranking_service, 'TTL_PRIORS', ranking_service.TTL_PRIORS)
    monkeypatch.setattr(cache.backend, 'cache_dir', str(tmp_path / 'cache'))
    monkeypatch.setenv('CFBD_OFFLINE', '0')
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('CFBD_MAX_CALLS', '8')
    monkeypatch.setenv('CFBD_API_KEY', 'test-key')
    monkeypatch.setenv('CFBD_KILL', '0')
    monkeypatch.delenv('SPEND_GATE_HOST', raising=False)
    reset_cfbd_call_count()
    spent = 0
    try:
        code = pre.main(['--current'], output_root=output, static_root=static)
        spent = get_cfbd_call_count()
    finally:
        reset_cfbd_call_count()
        cache._memory_cache.clear()
        cache._memory_cache.update(saved_memory)
        cache._prefix_index.clear()
        cache._prefix_index.update(saved_index)
    assert _snapshot(FRONTEND) == frontend_before
    assert _snapshot(PRIVATE) == private_before
    if not private_existed:
        assert not PRIVATE.exists()
    assert not (tmp_path / 'cache').exists()
    return code, calls, spent, output, static


def _weeks(root: Path) -> list:
    folder = root / '2026'
    if not folder.exists():
        return []
    return sorted(path.name for path in folder.glob('week-*.json'))


def test_cold_precompute_continues_when_remaining_header_is_missing(monkeypatch, tmp_path, capsys):
    code, calls, spent, output, static = _run(monkeypatch, tmp_path, {})
    assert code == 0
    assert 1 <= len(calls) <= 4
    assert spent == len(calls)
    logged = [line for line in capsys.readouterr().out.splitlines() if 'CFBD LIVE' in line]
    assert len(logged) == len(calls)
    assert all(line.endswith('remaining=unknown') for line in logged)
    assert _weeks(static) == ['week-1.json', 'week-2.json', 'week-3.json']
    assert _weeks(output) == ['week-1.json', 'week-2.json', 'week-3.json']
    manifest = json.loads((static / 'manifest.json').read_text(encoding='utf-8'))
    assert manifest['years']['2026'] == [1, 2, 3]
    output_manifest = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
    assert output_manifest['years']['2026'] == [1, 2, 3]


def test_cold_precompute_stops_when_remaining_header_is_zero(monkeypatch, tmp_path, capsys):
    code, calls, spent, output, static = _run(
        monkeypatch,
        tmp_path,
        {'X-CallLimit-Remaining': '0'},
    )
    captured = capsys.readouterr()
    assert code == 1
    assert len(calls) == 1
    assert calls[0].endswith('/teams')
    assert spent == 1
    assert _weeks(static) == []
    assert _weeks(output) == []
    assert 'below 27000' in captured.err
    assert 'Traceback' not in captured.err
    assert 'Traceback' not in captured.out
