"""The rankings publisher opens a PR, or skips when the boards did not change."""
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / '.github' / 'workflows'
sys.path.insert(0, str(ROOT / 'scripts'))

import open_rankings_pr as publisher


RULESET_CONTEXTS = (
    'Python',
    'Worker caps',
    'Frontend',
    'Workers Builds: true-rankings-cfb',
)


def _ok(cmd, stdout=''):
    return subprocess.CompletedProcess(cmd, 0, stdout, '')


def _events(doc):
    raw = doc[True] if True in doc else doc.get('on')
    if isinstance(raw, dict):
        return {str(key) for key in raw}
    if isinstance(raw, str):
        return {raw}
    if isinstance(raw, list):
        return {str(item) for item in raw}
    return set()


def test_refspec_force_updates_the_bot_branch_and_leaves_main(tmp_path):
    remote = tmp_path / 'remote.git'
    repo = tmp_path / 'repo'
    subprocess.run(['git', 'init', '--bare', '-b', 'main', str(remote)], check=True)
    subprocess.run(['git', 'init', '-b', 'main', str(repo)], check=True)
    subprocess.run(['git', 'config', 'user.email', 't@example.com'], cwd=repo, check=True)
    subprocess.run(['git', 'config', 'user.name', 't'], cwd=repo, check=True)
    (repo / 'README').write_text('a\n', encoding='utf-8')
    subprocess.run(['git', 'add', 'README'], cwd=repo, check=True)
    subprocess.run(['git', 'commit', '-m', 'init'], cwd=repo, check=True)
    subprocess.run(['git', 'remote', 'add', 'origin', str(remote)], cwd=repo, check=True)
    subprocess.run(['git', 'push', 'origin', 'main'], cwd=repo, check=True)
    main_sha = subprocess.run(
        ['git', 'rev-parse', 'main'],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    for marker in ('b\n', 'c\n'):
        (repo / 'README').write_text(marker, encoding='utf-8')
        subprocess.run(['git', 'add', 'README'], cwd=repo, check=True)
        subprocess.run(['git', 'commit', '-m', 'boards'], cwd=repo, check=True)
        subprocess.run(
            ['git', 'push', 'origin', publisher.push_refspec('bot/precompute-2026-w11')],
            cwd=repo,
            check=True,
        )
    remote_main = subprocess.run(
        ['git', 'rev-parse', 'refs/heads/main'],
        cwd=remote,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    remote_bot = subprocess.run(
        ['git', 'rev-parse', 'refs/heads/bot/precompute-2026-w11'],
        cwd=remote,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    head = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert remote_main == main_sha
    assert remote_bot == head
    assert remote_bot != remote_main


def test_branch_plan_names_the_newest_week_and_refuses_main():
    branch = publisher.plan_branch([
        'frontend/static/rankings/2024/week-15.json',
        'frontend/static/rankings/2026/week-10.json',
        'frontend/static/rankings/2026/week-10.story.json',
        'frontend/static/rankings/priors/2025.json',
        'frontend/static/rankings/manifest.json',
    ])
    assert branch == 'bot/precompute-2026-w10'
    assert publisher.push_refspec(branch) == '+HEAD:refs/heads/bot/precompute-2026-w10'
    for refused in ('main', 'refs/heads/main', 'bot/precompute-2025-w1', 'bot/precompute-2026-w17'):
        try:
            publisher.push_refspec(refused)
        except ValueError:
            continue
        raise AssertionError(refused)


def test_manifest_only_change_uses_the_newest_published_week():
    text = json.dumps({'years': {'2024': [1, 15], '2026': [1, 11]}})
    assert publisher.plan_branch(
        ['frontend/static/rankings/manifest.json'],
        text,
    ) == 'bot/precompute-2026-w11'


def test_holdout_week_is_not_a_branch():
    try:
        publisher.plan_branch([
            'frontend/static/rankings/2026/week-11.json',
            'frontend/static/rankings/2025/week-15.json',
        ])
    except publisher.HoldoutRefusal as exc:
        assert '2025' in str(exc)
    else:
        raise AssertionError('2025 week boards must be refused')
    assert publisher.SEALED_HOLDOUT_YEAR == 2025


def test_actions_gap_is_exact_job_names():
    assert publisher.ACTIONS_CHECKS == RULESET_CONTEXTS[:3]
    assert publisher.WORKERS_BUILDS_CHECK == RULESET_CONTEXTS[3]
    assert publisher.actions_gap(list(publisher.ACTIONS_CHECKS)) == []
    assert publisher.actions_gap(['Frontend', 'Python', 'Worker caps']) == []
    assert 'Worker caps' in publisher.actions_gap(['Python', 'Frontend'])
    assert publisher.actions_gap(['CI / Python', 'Worker caps', 'Frontend'])
    assert publisher.actions_gap(list(publisher.ACTIONS_CHECKS) + ['Preview stills'])


def test_no_change_does_not_push_or_open_a_pr(monkeypatch):
    calls = []

    def fake(cmd):
        calls.append(cmd)
        return _ok(cmd, 'abc123\n')

    monkeypatch.setenv('BASE_SHA', 'abc123')
    monkeypatch.setattr(publisher, 'run', fake)
    assert publisher.main() == 0
    assert calls == [['git', 'rev-parse', 'HEAD']]


def test_unchanged_rankings_diff_does_not_open_a_pr(monkeypatch):
    calls = []

    def fake(cmd):
        calls.append(cmd)
        if cmd[:2] == ['git', 'rev-parse']:
            return _ok(cmd, 'newsha\n')
        return _ok(cmd, '')

    monkeypatch.setenv('BASE_SHA', 'oldsha')
    monkeypatch.setattr(publisher, 'run', fake)
    assert publisher.main() == 0
    assert [cmd[1] for cmd in calls] == ['rev-parse', 'diff']
    assert not any(cmd[0] == 'gh' for cmd in calls)


def _scripted(monkeypatch, paths, prs, views):
    calls = []
    view_box = {'left': list(views)}

    def fake(cmd):
        calls.append(list(cmd))
        if cmd[:2] == ['git', 'rev-parse']:
            return _ok(cmd, 'newsha\n')
        if cmd[:2] == ['git', 'diff']:
            return _ok(cmd, ''.join(f'{path}\n' for path in paths))
        if cmd[:2] == ['git', 'push']:
            return _ok(cmd, '')
        if cmd[:3] == ['gh', 'pr', 'list']:
            return _ok(cmd, json.dumps(prs))
        if cmd[:3] == ['gh', 'pr', 'create']:
            return _ok(cmd, 'https://example.test/pull/7\n')
        if cmd[:3] == ['gh', 'workflow', 'run']:
            return _ok(cmd, '')
        if cmd[:3] == ['gh', 'run', 'list']:
            return _ok(cmd, json.dumps([{
                'databaseId': 99,
                'headSha': 'newsha',
                'event': 'workflow_dispatch',
                'status': 'queued',
            }]))
        if cmd[:3] == ['gh', 'run', 'view']:
            names = view_box['left'].pop(0)
            jobs = [{'name': name, 'status': 'queued'} for name in names]
            return _ok(cmd, json.dumps({'jobs': jobs}))
        raise AssertionError(cmd)

    monkeypatch.setenv('BASE_SHA', 'oldsha')
    monkeypatch.setenv('GH_REPO', 'merimeesoftware/cfb-ranking-algorithm')
    monkeypatch.setenv('BASE_REF', 'main')
    monkeypatch.setattr(publisher, 'run', fake)
    return calls, view_box


def test_open_pr_pushes_bot_branch_and_dispatches_ci(monkeypatch):
    calls, _views = _scripted(
        monkeypatch,
        ['frontend/static/rankings/2026/week-11.json'],
        [],
        [list(publisher.ACTIONS_CHECKS)],
    )
    def fail_sleep(_seconds):
        raise AssertionError('names were already exact')

    monkeypatch.setattr(publisher.time, 'sleep', fail_sleep)
    assert publisher.main() == 0
    push = next(cmd for cmd in calls if cmd[:2] == ['git', 'push'])
    assert push == ['git', 'push', 'origin', '+HEAD:refs/heads/bot/precompute-2026-w11']
    assert 'main' not in push[-1]
    create = next(cmd for cmd in calls if cmd[:3] == ['gh', 'pr', 'create'])
    assert '--base' in create and create[create.index('--base') + 1] == 'main'
    assert create[create.index('--head') + 1] == 'bot/precompute-2026-w11'
    dispatch = next(cmd for cmd in calls if cmd[:3] == ['gh', 'workflow', 'run'])
    assert dispatch == [
        'gh', 'workflow', 'run', 'ci.yml',
        '--repo', 'merimeesoftware/cfb-ranking-algorithm',
        '--ref', 'bot/precompute-2026-w11',
    ]
    assert not any(cmd[:3] == ['gh', 'pr', 'edit'] for cmd in calls)


def test_existing_pr_is_updated_without_a_second_create(monkeypatch):
    calls, _views = _scripted(
        monkeypatch,
        ['frontend/static/rankings/2026/week-11.json'],
        [{'number': 12, 'url': 'https://example.test/pull/12'}],
        [list(publisher.ACTIONS_CHECKS)],
    )
    assert publisher.main() == 0
    assert any(cmd[:2] == ['git', 'push'] for cmd in calls)
    assert any(cmd[:3] == ['gh', 'workflow', 'run'] for cmd in calls)
    assert not any(cmd[:3] == ['gh', 'pr', 'create'] for cmd in calls)


def test_holdout_diff_does_not_push(monkeypatch):
    calls = []

    def fake(cmd):
        calls.append(cmd)
        if cmd[:2] == ['git', 'rev-parse']:
            return _ok(cmd, 'newsha\n')
        return _ok(cmd, 'frontend/static/rankings/2025/week-1.json\n')

    monkeypatch.setenv('BASE_SHA', 'oldsha')
    monkeypatch.setenv('GH_REPO', 'merimeesoftware/cfb-ranking-algorithm')
    monkeypatch.setattr(publisher, 'run', fake)
    assert publisher.main() == 2
    assert not any(cmd[:2] == ['git', 'push'] for cmd in calls)
    assert not any(cmd[0] == 'gh' for cmd in calls)


def test_dispatch_waits_until_job_names_match(monkeypatch):
    calls, _views = _scripted(
        monkeypatch,
        ['frontend/static/rankings/2026/week-11.json'],
        [],
        [['Python'], list(publisher.ACTIONS_CHECKS)],
    )
    slept = []
    monkeypatch.setattr(publisher.time, 'sleep', slept.append)
    monkeypatch.setattr(publisher, 'WAIT_SECONDS', 100)
    assert publisher.main() == 0
    assert slept == [publisher.INTERVAL_SECONDS]
    views = [cmd for cmd in calls if cmd[:3] == ['gh', 'run', 'view']]
    assert len(views) == 2


def test_publish_workflow_lint():
    text = (WORKFLOWS / 'precompute-rankings.yml').read_text(encoding='utf-8')
    doc = yaml.safe_load(text)
    assert doc['permissions'] == {}
    assert _events(doc) == {'schedule', 'workflow_dispatch'}
    publish = doc['jobs']['publish']
    precompute = doc['jobs']['precompute']
    assert publish['permissions'] == {
        'contents': 'write',
        'pull-requests': 'write',
        'actions': 'write',
    }
    assert publish['runs-on'] == 'ubuntu-latest'
    assert precompute['permissions'] == {'contents': 'read'}
    assert 'actions' not in precompute['permissions']
    assert 'self-hosted' not in text
    assert 'HEAD:${GITHUB_REF_NAME}' not in text
    assert 'PAT' not in text
    assert 'pull_request_target' not in text
    assert 'CFBD_MAX_CALLS: "8"' in text
    assert 'CFBD_KILL: ${{ vars.CFBD_KILL }}' in text

    checkout = next(
        step for step in publish['steps']
        if str(step.get('uses', '')).startswith('actions/checkout@')
    )
    assert checkout['with']['persist-credentials'] is True
    assert checkout['with']['ref'] == '${{ github.event.repository.default_branch }}'
    runs = '\n'.join(step.get('run', '') for step in publish['steps'])
    assert 'git push' not in runs
    assert 'github.sha' not in runs
    assert runs.index('git rev-parse HEAD') < runs.index('publish_static_rankings.sh')
    assert runs.index('publish_static_rankings.sh') < runs.index('python3 scripts/open_rankings_pr.py')
    env = {}
    for step in publish['steps']:
        if isinstance(step.get('env'), dict):
            env.update(step['env'])
    assert env['GH_TOKEN'] == '${{ secrets.GITHUB_TOKEN }}'
    assert env['GH_REPO'] == '${{ github.repository }}'
    assert env['BASE_REF'] == '${{ github.event.repository.default_branch }}'
    assert 'CFBD' not in yaml.dump(publish)

    ci_text = (WORKFLOWS / 'ci.yml').read_text(encoding='utf-8')
    ci = yaml.safe_load(ci_text)
    assert _events(ci) == {'push', 'pull_request', 'workflow_dispatch'}
    names = [job.get('name') for _name, job in ci['jobs'].items()]
    assert names == list(publisher.ACTIONS_CHECKS)
    for _name, job in ci['jobs'].items():
        assert job['runs-on'] == 'ubuntu-latest'
    assert 'self-hosted' not in ci_text
    assert publisher.WORKERS_BUILDS_CHECK not in ci_text
