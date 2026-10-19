"""Precompute must see CFBD_KILL and skip before any live fetch."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import precompute_rankings as pre

FIXTURE = ROOT / 'tests' / 'fixtures' / 'caps' / 'precompute_cfbd_kill.json'
WORKFLOW = ROOT / '.github' / 'workflows' / 'precompute-rankings.yml'


def precompute_kill_gaps(workflow_text: str, required_line: str) -> list[str]:
    if required_line in workflow_text:
        return []
    return ['precompute step must pass CFBD_KILL from the repo variable']


def test_planted_precompute_workflow_without_cfbd_kill_trips():
    fixture = json.loads(FIXTURE.read_text(encoding='utf-8'))
    assert precompute_kill_gaps(fixture['planted_step_env'], fixture['required_line'])
    assert precompute_kill_gaps(WORKFLOW.read_text(encoding='utf-8'), fixture['required_line']) == []


def test_precompute_honors_planted_cfbd_kill(monkeypatch):
    fixture = json.loads(FIXTURE.read_text(encoding='utf-8'))
    monkeypatch.setenv('CFBD_KILL', fixture['CFBD_KILL'])
    monkeypatch.setenv('CFBD_API_KEY', 'test-key')
    monkeypatch.setenv('CFBD_OFFLINE', '0')

    def explode(*_args, **_kwargs):
        raise AssertionError('precompute constructed a live processor')

    monkeypatch.setattr(pre, 'CFBDataProcessor', explode)
    assert pre.main(['--year', '2024', '--week', '1']) == 0
