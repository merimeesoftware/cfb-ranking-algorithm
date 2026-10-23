"""Visitor routes must not construct a processor or call CFBD."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'app.py'
FIXTURE = ROOT / 'tests' / 'fixtures' / 'caps' / 'visitor_reaches_api.json'


def startup_hits(source: str) -> list[str]:
    hits = []
    if 'CFBDataProcessor(' in source:
        hits.append('constructs CFBDataProcessor')
    if 'api_integration' in source:
        hits.append('reaches api_integration')
    return hits


def test_planted_startup_processor_reaches_api():
    planted = json.loads(FIXTURE.read_text(encoding='utf-8'))
    assert startup_hits(planted['planted_source'])
    assert startup_hits(APP.read_text(encoding='utf-8')) == []


def test_visitor_routes_do_not_reach_api_integration(client, monkeypatch):
    planted = json.loads(FIXTURE.read_text(encoding='utf-8'))
    hit = []

    def boom(*_args, **_kwargs):
        hit.append('api_integration')
        raise AssertionError('visitor route reached api_integration')

    monkeypatch.setattr('api_integration.requests.get', boom)
    monkeypatch.setattr('api_integration.CFBDApiClient._make_request', boom)
    monkeypatch.setattr('data_processor.CFBDataProcessor.__init__', boom)

    for route in planted['routes']:
        if route['method'] == 'POST':
            client.post(route['path'], json={})
        else:
            client.get(route['path'])
    assert hit == []
