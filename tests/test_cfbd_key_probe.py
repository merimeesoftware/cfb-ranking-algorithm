"""The key probe is one /info call and does not print the key."""
import json
import sys
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import cfbd_key_probe  # noqa: E402

WORKFLOW = ROOT / '.github' / 'workflows' / 'cfbd-key-probe.yml'
PLANTED = ROOT / 'tests' / 'fixtures' / 'caps' / 'cfbd_key_probe_echoes_key.yml'
SECRET = 'super-secret-key'


def key_leaks(text: str) -> list[str]:
    leaks = []
    if 'echo "$CFBD_API_KEY"' in text or 'echo $CFBD_API_KEY' in text:
        leaks.append('echoes the key')
    if 'print(key' in text or 'print(os.environ' in text:
        leaks.append('prints the key')
    return leaks


def public_lines(captured: str) -> list[str]:
    return [
        line for line in captured.splitlines()
        if line and not line.startswith('::add-mask::')
    ]


class _Body:
    def __init__(self, payload, status=200):
        self.status = status
        self._raw = json.dumps(payload).encode('utf-8')

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def test_probe_prints_patron_level_and_remaining_only(monkeypatch, capsys):
    monkeypatch.setenv('CFBD_API_KEY', SECRET)
    calls = []

    def opener(request, timeout=30):
        calls.append(request.full_url)
        assert request.get_header('Authorization') == f'Bearer {SECRET}'
        assert timeout == 30
        return _Body({'patronLevel': 2, 'remainingCalls': 29000, 'tierName': 'hidden'})

    assert cfbd_key_probe.probe(opener) == 0
    assert calls == ['https://api.collegefootballdata.com/info']
    shown = public_lines(capsys.readouterr().out)
    assert shown == ['patronLevel=2', 'remainingCalls=29000']
    assert SECRET not in '\n'.join(shown)


def test_probe_fails_when_the_key_is_rejected(monkeypatch, capsys):
    monkeypatch.setenv('CFBD_API_KEY', SECRET)

    def opener(_request, timeout=30):
        raise urllib.error.HTTPError(cfbd_key_probe.INFO_URL, 401, 'no', None, None)

    assert cfbd_key_probe.probe(opener) == 1
    shown = public_lines(capsys.readouterr().out)
    assert shown == ['CFBD rejected the key (HTTP 401)']
    assert SECRET not in '\n'.join(shown)


def test_planted_workflow_that_echoes_the_key_trips():
    planted = PLANTED.read_text(encoding='utf-8')
    live = WORKFLOW.read_text(encoding='utf-8')
    script = (ROOT / 'scripts' / 'cfbd_key_probe.py').read_text(encoding='utf-8')
    assert key_leaks(planted)
    assert key_leaks(live) == []
    assert key_leaks(script) == []
    assert live.count('python scripts/cfbd_key_probe.py') == 1
    assert 'curl ' not in live
    assert script.count('https://api.collegefootballdata.com/info') == 1
    assert 'workflow_dispatch:' in live
    assert 'on a push to main that touches the probe' in live
    assert 'outside the cron budget' in live
    assert 'pull_request:' not in live
    assert 'head.repo.full_name' not in live
    assert 'branches:' in live
    assert '- main' in live
