"""Raw CFBD rows stay out of Actions cache, and untrusted jobs never see the key.

Covers the cache scan (pip and npm only; no static_rankings, .cache, cfbd
keys, or ${{ paths) and the secret scan (no pull_request_target; no CFBD
secret on an untrusted event, including workflow_call from that event).
"""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / '.github' / 'workflows'
UNTRUSTED = {
    'pull_request',
    'pull_request_target',
    'issue_comment',
    'workflow_run',
    'pull_request_review',
    'pull_request_review_comment',
    'merge_group',
}
CACHE_ACTIONS = {'actions/cache', 'actions/cache/restore', 'actions/cache/save'}
SECRET = re.compile(r'secrets\s*(?:\.|\[)\s*[\'"]?CFBD', re.I)


def _load(name, text):
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise AssertionError(f'{name} did not parse: {exc}') from exc
    if not isinstance(doc, dict):
        raise AssertionError(f'{name} did not parse')
    return doc


def _events(doc):
    # PyYAML 1.1 reads the bare key `on` as True.
    raw = doc[True] if True in doc else doc.get('on')
    if raw is None or raw is True:
        return set()
    if isinstance(raw, str):
        return {raw}
    if isinstance(raw, list):
        return {str(item) for item in raw}
    if isinstance(raw, dict):
        return {str(key) for key in raw}
    raise AssertionError(f'unreadable on: {raw!r}')


def _jobs(doc):
    jobs = doc.get('jobs') or {}
    if not isinstance(jobs, dict):
        return []
    return [(str(name), job) for name, job in jobs.items() if isinstance(job, dict)]


def _texts(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _texts(item)
    elif isinstance(value, list):
        for item in value:
            yield from _texts(item)


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _callee(uses):
    if not isinstance(uses, str) or '.github/workflows/' not in uses:
        return None
    name = uses.split('.github/workflows/', 1)[1].split('@', 1)[0].strip()
    if name.endswith(('.yml', '.yaml')):
        return name
    return None


def _cache_hits(step):
    if not isinstance(step, dict):
        return []
    uses = str(step.get('uses') or '')
    action = uses.split('@', 1)[0]
    body = step.get('with') if isinstance(step.get('with'), dict) else {}
    if action not in CACHE_ACTIONS:
        cache_value = body.get('cache')
        if cache_value not in (None, 'pip', 'npm'):
            return [f'cache:{cache_value}']
        return []
    hits = [action]
    for path in _as_list(body.get('path')):
        normalized = path.replace('\\', '/')
        segments = [part for part in normalized.split('/') if part not in {'', '.'}]
        if (
            '${{' in path
            or 'static_rankings' in path.lower()
            or '.cache' in segments
            or normalized.rstrip('/') in {'.cache', './.cache'}
        ):
            hits.append(path)
    for key_name in ('key', 'restore-keys'):
        for key in _as_list(body.get(key_name)):
            lowered = key.lower()
            if 'cfbd' in lowered or 'static_rankings' in lowered:
                hits.append(key)
    return hits


def violations(files):
    docs = {name: _load(name, text) for name, text in files}
    events = {name: _events(doc) for name, doc in docs.items()}
    reachable = {name: set(found) for name, found in events.items()}
    growing = True
    while growing:
        growing = False
        for name, doc in docs.items():
            for _job_name, job in _jobs(doc):
                callee = _callee(job.get('uses'))
                if callee not in reachable:
                    continue
                extra = reachable[name] - reachable[callee]
                if extra:
                    reachable[callee] |= reachable[name]
                    growing = True
    problems = []
    for name, doc in docs.items():
        if 'pull_request_target' in events[name]:
            problems.append(f'{name} uses pull_request_target')
        for job_name, job in _jobs(doc):
            for step in job.get('steps') or []:
                for hit in _cache_hits(step):
                    problems.append(f'{name}:{job_name} {hit}')
            if not (reachable[name] & UNTRUSTED):
                continue
            blobs = list(_texts(job)) + list(_texts(doc.get('env')))
            if any(SECRET.search(text) for text in blobs):
                problems.append(f'{name}:{job_name} CFBD secret')
    return problems


def _workflow_files():
    return sorted(
        path for path in WORKFLOWS.iterdir()
        if path.suffix in {'.yml', '.yaml'} and not path.name.endswith('.lock.yml')
    )


def _plant(on_block, body):
    return f'name: Planted\non:\n{on_block}\njobs:\n  job:\n{body}'


def test_workflows_keep_raw_cfbd_off_untrusted_runs():
    probe = (WORKFLOWS / 'cfbd-key-probe.yml').read_text(encoding='utf-8')
    precompute = (WORKFLOWS / 'precompute-rankings.yml').read_text(encoding='utf-8')
    assert True in yaml.safe_load(probe)
    assert _events(_load('cfbd-key-probe.yml', probe)) == {'workflow_dispatch', 'push'}
    assert _events(_load('precompute-rankings.yml', precompute)) == {
        'schedule',
        'workflow_dispatch',
    }
    files = [(path.name, path.read_text(encoding='utf-8')) for path in _workflow_files()]
    assert {name for name, _text in files} >= {
        'precompute-rankings.yml',
        'precompute-blurbs.yml',
        'ci.yml',
        'cfbd-key-probe.yml',
    }
    assert violations(files) == []

    try:
        violations([('bad.yml', 'on: [\n')])
    except AssertionError as exc:
        assert 'did not parse' in str(exc)
    else:
        raise AssertionError('a broken workflow must fail')

    secret = '    steps:\n      - run: echo ${{ secrets.CFBD_API_KEY }}\n'
    for event in sorted(UNTRUSTED):
        assert violations([('e.yml', _plant(f'  {event}:\n', secret))]), event
    assert violations([('t.yml', _plant('  pull_request_target:\n', '    steps:\n      - run: echo hi\n'))])
    assert violations([('s.yml', _plant(
        "  schedule:\n    - cron: '0 6 * * 0'\n",
        '    env:\n      CFBD_API_KEY: ${{ secrets.CFBD_API_KEY }}\n    steps:\n      - run: probe\n',
    ))]) == []
    assert violations([('ci.yml', _plant(
        '  pull_request:\n',
        '    steps:\n      - run: pytest\n        env:\n          CFBD_API_KEY: test-key-for-unit-tests\n',
    ))]) == []
    assert violations([('deps.yml', _plant(
        '  pull_request:\n',
        '    steps:\n'
        '      - uses: actions/setup-python@v7\n        with:\n          cache: pip\n'
        '      - uses: actions/setup-node@v7\n        with:\n          cache: npm\n',
    ))]) == []

    raw_cache = (
        '    steps:\n'
        '      - uses: actions/cache/restore@v4\n'
        '        with:\n'
        '          path: |\n'
        '            static_rankings\n'
        '            .cache\n'
        '            ${{ github.workspace }}/rows\n'
        '          key: cfbd-precompute-${{ github.run_id }}\n'
        '          restore-keys: |\n'
        '            cfbd-\n'
        '            static_rankings\n'
    )
    hits = violations([('c.yml', _plant('  schedule:\n', raw_cache))])
    assert any('static_rankings' in hit for hit in hits)
    assert any('.cache' in hit for hit in hits)
    assert any('${{' in hit for hit in hits)
    assert any('cfbd' in hit.lower() for hit in hits)
    assert violations([('n.yml', _plant(
        '  schedule:\n',
        '    steps:\n      - uses: actions/cache/save@v4\n        with:\n          path: ~/.npm\n          key: npm\n',
    ))])
    caller = (
        'name: Caller\non:\n  pull_request:\njobs:\n  call:\n'
        '    uses: ./.github/workflows/callee.yml\n'
    )
    callee = (
        'name: Callee\non:\n  workflow_call:\njobs:\n  restore:\n'
        '    steps:\n      - env:\n          CFBD_API_KEY: ${{ secrets.CFBD_API_KEY }}\n'
        '        run: probe\n'
    )
    assert any('CFBD secret' in hit for hit in violations([
        ('caller.yml', caller),
        ('callee.yml', callee),
    ]))
