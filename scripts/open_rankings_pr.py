#!/usr/bin/env python3
"""Push a rankings commit to a bot branch and open or update a pull request.

A GITHUB_TOKEN push does not start GitHub Actions. ci.yml is dispatched on
the bot branch so its job names are the required Actions checks. Workers
Builds is the GitHub App check on the push, not a job in that dispatch.

No change (the publish commit did not happen) exits 0 without a push or a
PR. A 2025 week path exits 2. This script does not call CFBD.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# Ruleset 27081269 contexts. The first three are ci.yml job names
# (integration GitHub Actions). The fourth is the Cloudflare GitHub App.
ACTIONS_CHECKS = ('Python', 'Worker caps', 'Frontend')
WORKERS_BUILDS_CHECK = 'Workers Builds: true-rankings-cfb'
OWNER_LABEL = 'owner:cfb-minicon'
SEALED_HOLDOUT_YEAR = 2025
SEALED_PREFIX = f'frontend/static/rankings/{SEALED_HOLDOUT_YEAR}/'
WEEK_PATH = re.compile(r'^frontend/static/rankings/(\d{4})/week-(\d+)\.json$')
BOT_BRANCH = re.compile(r'^bot/precompute-(\d{4})-w(\d{1,2})$')
MANIFEST = Path('frontend/static/rankings/manifest.json')
WAIT_SECONDS = 480
INTERVAL_SECONDS = 15


class HoldoutRefusal(Exception):
    """A 2025 rankings path must not be published."""


def _normalized(path: str) -> str:
    return path.replace('\\', '/').strip().lstrip('./')


def is_sealed_path(path: str) -> bool:
    return _normalized(path).startswith(SEALED_PREFIX)


def parse_week_path(path: str) -> tuple[int, int] | None:
    match = WEEK_PATH.fullmatch(_normalized(path))
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def newest_from_manifest(text: str) -> tuple[int, int] | None:
    if not text.strip():
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    years = payload.get('years') if isinstance(payload, dict) else None
    if not isinstance(years, dict):
        return None
    found: list[tuple[int, int]] = []
    for year, weeks in years.items():
        if not str(year).isdigit() or not isinstance(weeks, list) or not weeks:
            continue
        numbers = [
            int(week)
            for week in weeks
            if isinstance(week, int) or (isinstance(week, str) and str(week).isdigit())
        ]
        if numbers:
            found.append((int(year), max(numbers)))
    if not found:
        return None
    return max(found)


def plan_branch(paths: list[str], manifest_text: str | None = None) -> str:
    """Branch for this commit: bot/precompute-<year>-w<week>."""
    if any(is_sealed_path(path) for path in paths):
        raise HoldoutRefusal(
            '2025 is the sealed holdout. Not publishing week boards.'
        )
    weeks = [pair for pair in (parse_week_path(path) for path in paths) if pair]
    if weeks:
        year, week = max(weeks)
    else:
        chosen = newest_from_manifest(manifest_text or '')
        if chosen is None:
            raise ValueError('rankings changed but no week board to name the branch')
        year, week = chosen
    if year == SEALED_HOLDOUT_YEAR:
        raise HoldoutRefusal(
            '2025 is the sealed holdout. Not publishing week boards.'
        )
    if not 1 <= week <= 16:
        raise ValueError(f'refusing week {week}')
    return f'bot/precompute-{year}-w{week}'


def push_refspec(branch: str) -> str:
    """Force-update only this bot ref. The leading + is the force flag."""
    match = BOT_BRANCH.fullmatch(branch)
    if not match:
        raise ValueError(f'refusing to push {branch}')
    year = int(match.group(1))
    week = int(match.group(2))
    if year == SEALED_HOLDOUT_YEAR:
        raise ValueError('2025 is the sealed holdout. Not publishing week boards.')
    if not 1 <= week <= 16:
        raise ValueError(f'refusing week {week}')
    if branch in {'main', 'master'} or branch.startswith('refs/'):
        raise ValueError(f'refusing to push {branch}')
    return f'+HEAD:refs/heads/{branch}'


def actions_gap(job_names: list[str]) -> list[str]:
    """Empty when the dispatched run's job names are exactly the Actions contexts."""
    if set(job_names) == set(ACTIONS_CHECKS):
        return []
    missing = [name for name in ACTIONS_CHECKS if name not in job_names]
    extra = [name for name in job_names if name not in ACTIONS_CHECKS]
    return missing + [f'extra:{name}' for name in extra]


def matching_run(runs: list[dict], sha: str) -> dict | None:
    for run in runs:
        if run.get('headSha') == sha and run.get('event') == 'workflow_dispatch':
            return run
    return None


def job_names_from_view(payload: dict) -> list[str]:
    names = []
    for job in payload.get('jobs') or []:
        name = job.get('name') if isinstance(job, dict) else None
        if isinstance(name, str) and name:
            names.append(name)
    return names


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    print('+', ' '.join(cmd), flush=True)
    completed = subprocess.run(
        cmd,
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.stdout:
        sys.stdout.write(completed.stdout)
        if not completed.stdout.endswith('\n'):
            sys.stdout.write('\n')
    if completed.returncode != 0:
        if completed.stderr:
            sys.stderr.write(completed.stderr)
        raise subprocess.CalledProcessError(
            completed.returncode,
            cmd,
            completed.stdout,
            completed.stderr,
        )
    return completed


def _manifest_text() -> str | None:
    if not MANIFEST.is_file():
        return None
    return MANIFEST.read_text(encoding='utf-8')


def _week_of(branch: str) -> tuple[int, int]:
    match = BOT_BRANCH.fullmatch(branch)
    if not match:
        raise ValueError(f'refusing to push {branch}')
    return int(match.group(1)), int(match.group(2))


def _pr_body(year: int, week: int, sha: str) -> str:
    return (
        f'Weekly boards for {year} week {week} ({sha}).\n\n'
        'A GITHUB_TOKEN push does not start ci.yml, so this job dispatches '
        'that workflow on this branch. Workers Builds is the GitHub App '
        'check on the push.\n'
    )


def ensure_pr(repo: str, base: str, branch: str, year: int, week: int, sha: str) -> str:
    listed = json.loads(run([
        'gh', 'pr', 'list',
        '--repo', repo,
        '--head', branch,
        '--base', base,
        '--state', 'open',
        '--json', 'number,url',
    ]).stdout or '[]')
    if listed:
        url = listed[0]['url']
        run([
            'gh', 'pr', 'edit', url,
            '--repo', repo,
            '--add-label', OWNER_LABEL,
        ])
        print(f'Updated {url}')
        return url
    created = run([
        'gh', 'pr', 'create',
        '--repo', repo,
        '--base', base,
        '--head', branch,
        '--title', f'Publish precomputed rankings ({year} week {week})',
        '--body', _pr_body(year, week, sha),
        '--label', OWNER_LABEL,
    ])
    url = created.stdout.strip()
    print(f'Opened {url}')
    return url


def wait_for_actions(repo: str, branch: str, sha: str) -> int:
    """Return 0 once the dispatched ci.yml jobs are exactly ACTIONS_CHECKS."""
    deadline = time.monotonic() + WAIT_SECONDS
    observed: list[str] = []
    while True:
        runs = json.loads(run([
            'gh', 'run', 'list',
            '--repo', repo,
            '--workflow', 'ci.yml',
            '--branch', branch,
            '--event', 'workflow_dispatch',
            '--limit', '5',
            '--json', 'databaseId,headSha,event,status',
        ]).stdout or '[]')
        match = matching_run(runs, sha)
        if match is None:
            gap: list[str] = ['run']
            observed = []
        else:
            view = json.loads(run([
                'gh', 'run', 'view', str(match['databaseId']),
                '--repo', repo,
                '--json', 'jobs',
            ]).stdout or '{}')
            observed = job_names_from_view(view)
            gap = actions_gap(observed)
        if not gap:
            print('Dispatched ci.yml checks: ' + ', '.join(ACTIONS_CHECKS))
            return 0
        if time.monotonic() >= deadline:
            print(
                f'ci.yml job names {observed!r} != {list(ACTIONS_CHECKS)!r} ({gap})',
                file=sys.stderr,
            )
            return 1
        time.sleep(INTERVAL_SECONDS)


def main() -> int:
    base_sha = os.environ.get('BASE_SHA', '').strip()
    if not base_sha:
        print('BASE_SHA is required', file=sys.stderr)
        return 1
    head = run(['git', 'rev-parse', 'HEAD']).stdout.strip()
    if head == base_sha:
        print('No ranking changes to publish')
        return 0
    diff = run([
        'git', 'diff', '--name-only', base_sha, head, '--',
        'frontend/static/rankings',
    ])
    paths = [line.strip() for line in diff.stdout.splitlines() if line.strip()]
    if not paths:
        print('No ranking changes to publish')
        return 0
    try:
        branch = plan_branch(paths, _manifest_text())
        refspec = push_refspec(branch)
        year, week = _week_of(branch)
    except HoldoutRefusal as exc:
        print(exc, file=sys.stderr)
        return 2
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    repo = os.environ.get('GH_REPO', '').strip()
    if not repo:
        print('GH_REPO is required', file=sys.stderr)
        return 1
    base_ref = os.environ.get('BASE_REF', 'main').strip() or 'main'
    if base_ref == branch:
        print('refusing to open a PR onto itself', file=sys.stderr)
        return 1
    run(['git', 'push', 'origin', refspec])
    ensure_pr(repo, base_ref, branch, year, week, head)
    run(['gh', 'workflow', 'run', 'ci.yml', '--repo', repo, '--ref', branch])
    return wait_for_actions(repo, branch, head)


if __name__ == '__main__':
    raise SystemExit(main())
