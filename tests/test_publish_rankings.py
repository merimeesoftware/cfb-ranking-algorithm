"""The publish step commits derived rankings and ignores the private cache."""
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'publish_static_rankings.sh'
WORKFLOW = ROOT / '.github' / 'workflows' / 'precompute-rankings.yml'


def test_publish_step_ignores_the_private_cache(tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    subprocess.run(['git', 'init'], cwd=repo, check=True)
    subprocess.run(['git', 'config', 'user.email', 't@example.com'], cwd=repo, check=True)
    subprocess.run(['git', 'config', 'user.name', 't'], cwd=repo, check=True)
    (repo / '.gitignore').write_text('static_rankings/\n', encoding='utf-8')
    private = repo / 'static_rankings'
    private.mkdir()
    (private / 'secret.json').write_text('{"games": []}\n', encoding='utf-8')
    public = repo / 'frontend' / 'static' / 'rankings' / '2024'
    public.mkdir(parents=True)
    (public / 'week-1.json').write_text('{}\n', encoding='utf-8')
    subprocess.run(['git', 'add', '--', '.gitignore', 'frontend'], cwd=repo, check=True)
    subprocess.run(['git', 'commit', '-m', 'init'], cwd=repo, check=True)
    (public / 'week-1.json').write_text('{"week": 1}\n', encoding='utf-8')
    (repo / 'frontend' / 'static' / 'rankings' / 'priors').mkdir()
    (repo / 'frontend' / 'static' / 'rankings' / 'priors' / '2024.json').write_text(
        '{"algo":"v5.3","schema":1,"teams":{"Georgia":1800}}\n',
        encoding='utf-8',
    )

    subprocess.run(['bash', str(SCRIPT)], cwd=repo, check=True)
    tracked = subprocess.run(
        ['git', 'ls-files'],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert 'static_rankings/' not in tracked
    assert 'frontend/static/rankings/2024/week-1.json' in tracked
    assert 'frontend/static/rankings/priors/2024.json' in tracked
    assert 'baseline/' not in tracked
    assert 'teams/' not in tracked
    subprocess.run(['bash', str(SCRIPT)], cwd=repo, check=True)


def _action_path_steps(text: str, marker: str) -> list[list[str]]:
    """Path lists for every step whose ``uses:`` contains ``marker``."""
    lines = text.splitlines()
    steps = []
    index = 0
    while index < len(lines):
        stripped_line = lines[index].strip()
        if (
            stripped_line.startswith('#')
            or 'uses:' not in stripped_line
            or marker not in stripped_line
        ):
            index += 1
            continue
        index += 1
        collected = []
        while index < len(lines):
            line = lines[index]
            if line.startswith('      - ') or (line and not line[0].isspace()):
                break
            stripped = line.strip()
            if stripped == 'path: |':
                index += 1
                while index < len(lines) and (
                    lines[index].startswith('            ') or not lines[index].strip()
                ):
                    if lines[index].strip():
                        collected.append(lines[index].strip().strip('"').strip("'"))
                    index += 1
                continue
            if stripped.startswith('path:'):
                value = stripped.split(':', 1)[1].strip().strip('"').strip("'")
                if value and value != '|':
                    collected.append(value)
            index += 1
        steps.append(collected)
    return steps


def _rankings_root(path: str) -> str:
    return path.replace('\\', '/').strip().lstrip('./').rstrip('/')


def _upload_path_allowed(path: str) -> bool:
    """Public rankings only. Globs, ``..``, and the private cache directory are rejected."""
    normalized = path.replace('\\', '/').strip().strip('"').strip("'")
    if '*' in normalized or normalized in {'.', './', '..'}:
        return False
    segments = [segment for segment in normalized.split('/') if segment not in {'', '.'}]
    if not segments or '..' in segments:
        return False
    if segments[0].startswith('static_rankings'):
        return False
    root = '/'.join(segments)
    return root == 'frontend/static/rankings' or root.startswith('frontend/static/rankings/')


# Deploy and preview stills publish these concrete roots. They are not the
# private CFBD cache. The rankings allowlist in _upload_path_allowed is unchanged.
_OTHER_ARTIFACT_ROOTS = (
    'frontend/build',
    'preview-stills-out',
)


def _workflow_files() -> list[Path]:
    directory = ROOT / '.github' / 'workflows'
    return sorted(
        path for path in directory.iterdir()
        if path.is_file()
        and path.suffix in {'.yml', '.yaml'}
        and not path.name.endswith('.lock.yml')
    )


def _unrelated_public_artifact(path: str) -> bool:
    """Same glob, dot, and private-cache rejects as the rankings allowlist.

    A path outside ``frontend/static/rankings`` is still rejected unless it is
    exactly one of the non-rankings roots above, or a child of one.
    """
    normalized = path.replace('\\', '/').strip().strip('"').strip("'")
    if '*' in normalized or normalized in {'.', './', '..'}:
        return False
    segments = [segment for segment in normalized.split('/') if segment not in {'', '.'}]
    if not segments or '..' in segments:
        return False
    if any(segment.startswith('static_rankings') for segment in segments):
        return False
    root = '/'.join(segments)
    return any(
        root == allowed or root.startswith(allowed + '/')
        for allowed in _OTHER_ARTIFACT_ROOTS
    )


def test_upload_artifact_excludes_private_static_rankings():
    steps = _action_path_steps(WORKFLOW.read_text(encoding='utf-8'), 'actions/upload-artifact@')
    assert steps
    for paths in steps:
        assert paths
        assert all(_upload_path_allowed(path) for path in paths)

    workflows = _workflow_files()
    names = {path.name for path in workflows}
    assert {
        'precompute-rankings.yml',
        'precompute-blurbs.yml',
        'deploy-cloudflare.yml',
        'preview-stills.yml',
    } <= names
    seen = set()
    for workflow in workflows:
        upload_steps = _action_path_steps(
            workflow.read_text(encoding='utf-8'),
            'actions/upload-artifact@',
        )
        for paths in upload_steps:
            assert paths, workflow.name
            for path in paths:
                seen.add(path.replace('\\', '/').strip().rstrip('/'))
                if workflow.name == 'precompute-rankings.yml':
                    assert _upload_path_allowed(path), path
                else:
                    assert _upload_path_allowed(path) or _unrelated_public_artifact(path), (
                        workflow.name,
                        path,
                    )
    assert seen == {
        'frontend/static/rankings',
        'frontend/build',
        'preview-stills-out',
    }

    blurbs = (ROOT / '.github' / 'workflows' / 'precompute-blurbs.yml').read_text(encoding='utf-8')
    assert 'actions/upload-artifact@' not in blurbs
    assert 'actions/download-artifact@' not in blurbs
    assert 'static_rankings/' not in blurbs
    assert _action_path_steps(blurbs, 'actions/upload-artifact@') == []

    planted = """
      - uses: actions/upload-artifact@v7
        with:
          path: frontend/static/rankings/
      - uses: actions/upload-artifact@v7
        with:
          path: |
            *
            **
            .
            static_rankings*
            static_rankings/
            frontend/static/rankings/../../static_rankings
            frontend/static/rankings/
"""
    planted_steps = _action_path_steps(planted, 'actions/upload-artifact@')
    assert len(planted_steps) == 2
    assert all(_upload_path_allowed(path) for path in planted_steps[0])
    rejected = [path for path in planted_steps[1] if not _upload_path_allowed(path)]
    assert rejected == [
        '*',
        '**',
        '.',
        'static_rankings*',
        'static_rankings/',
        'frontend/static/rankings/../../static_rankings',
    ]
    assert _upload_path_allowed(planted_steps[1][-1])
    assert all(not _unrelated_public_artifact(path) for path in rejected)
    assert not _unrelated_public_artifact('frontend/build/../../static_rankings')
    assert not _unrelated_public_artifact('frontend/build/static_rankings')
    assert not _unrelated_public_artifact('coverage/')
    assert _unrelated_public_artifact('frontend/build')
    assert _unrelated_public_artifact('preview-stills-out/')
    assert not _upload_path_allowed('frontend/build')
    assert not _upload_path_allowed('preview-stills-out/')


def test_download_path_matches_upload_path(tmp_path):
    text = WORKFLOW.read_text(encoding='utf-8')
    uploads = [
        path
        for step in _action_path_steps(text, 'actions/upload-artifact@')
        for path in step
    ]
    downloads = [
        path
        for step in _action_path_steps(text, 'actions/download-artifact@')
        for path in step
    ]
    assert uploads and downloads
    assert 'actions/upload-artifact@v7' in text
    assert 'actions/download-artifact@v8' in text
    assert {_rankings_root(path) for path in uploads} == {_rankings_root(path) for path in downloads}
    assert _rankings_root(downloads[0]) == 'frontend/static/rankings'

    repo = tmp_path / 'repo'
    repo.mkdir()
    subprocess.run(['git', 'init'], cwd=repo, check=True)
    subprocess.run(['git', 'config', 'user.email', 't@example.com'], cwd=repo, check=True)
    subprocess.run(['git', 'config', 'user.name', 't'], cwd=repo, check=True)
    artifact = tmp_path / 'artifact'
    (artifact / '2024').mkdir(parents=True)
    (artifact / '2024' / 'week-15.json').write_text('{"week": 15}\n', encoding='utf-8')
    (artifact / 'priors').mkdir()
    (artifact / 'priors' / '2023.json').write_text('{"schema": 1}\n', encoding='utf-8')
    dest = repo.joinpath(*_rankings_root(downloads[0]).split('/'))
    shutil.copytree(artifact, dest)
    subprocess.run(['bash', str(SCRIPT)], cwd=repo, check=True)
    tracked = subprocess.run(
        ['git', 'ls-files'],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    names = tracked.splitlines()
    assert 'frontend/static/rankings/2024/week-15.json' in names
    assert 'frontend/static/rankings/priors/2023.json' in names
    assert 'week-15.json' not in names
    assert 'priors/2023.json' not in names


def test_workflow_publish_and_inputs():
    text = WORKFLOW.read_text(encoding='utf-8')
    script = SCRIPT.read_text(encoding='utf-8')
    assert 'git add -- frontend/static/rankings static_rankings' not in text
    assert 'static_rankings' not in script
    assert 'sh scripts/publish_static_rankings.sh' in text
    assert 'YEAR: ${{ github.event.inputs.year }}' in text
    assert 'THROUGH_WEEK: ${{ github.event.inputs.through_week }}' in text
    assert '"$YEAR"' in text
    assert '"$THROUGH_WEEK"' in text
    assert 'type: number' in text
    assert text.count('type: number') == 2
    assert 'permissions: {}' in text
    assert 'contents: write' in text
    assert 'persist-credentials: false' in text
    assert 'persist-credentials: true' in text
    assert 'group: precompute-rankings' in text
    assert 'cancel-in-progress: false' in text
    assert 'interim writer' in text.lower() or 'Interim writer' in text
    # Dispatch values are env bindings, never pasted into a run script.
    run_blocks = []
    capture = False
    for line in text.splitlines():
        if line.strip() == 'run: |' or line.strip().startswith('run:'):
            capture = True
            continue
        if capture:
            if line.startswith('      - ') or (line and not line.startswith(' ')):
                capture = False
            else:
                run_blocks.append(line)
    joined = '\n'.join(run_blocks)
    assert 'github.event.inputs' not in joined
