"""The publish step commits derived rankings and ignores the private cache."""
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


def _upload_artifact_paths(text: str) -> list[str]:
    """Paths named on actions/upload-artifact steps. Cache paths are ignored."""
    lines = text.splitlines()
    collected = []
    index = 0
    while index < len(lines):
        if 'actions/upload-artifact@' not in lines[index]:
            index += 1
            continue
        index += 1
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
                        collected.append(lines[index].strip())
                    index += 1
                continue
            if stripped.startswith('path:'):
                value = stripped.split(':', 1)[1].strip().strip('"').strip("'")
                if value and value != '|':
                    collected.append(value)
            index += 1
    return collected


def _names_private_static_rankings(path: str) -> bool:
    """True when a path selects repo-root static_rankings, not the public tree."""
    normalized = path.replace('\\', '/').strip().lstrip('./')
    if normalized.startswith('frontend/static/rankings/') or normalized.rstrip('/') == 'frontend/static/rankings':
        return False
    segments = [segment for segment in normalized.split('/') if segment]
    return 'static_rankings' in segments


def test_upload_artifact_excludes_private_static_rankings():
    paths = _upload_artifact_paths(WORKFLOW.read_text(encoding='utf-8'))
    assert paths
    assert all(not _names_private_static_rankings(path) for path in paths)
    assert any(
        path.replace('\\', '/').rstrip('/') == 'frontend/static/rankings'
        for path in paths
    )
    planted = """
      - uses: actions/upload-artifact@v7
        with:
          path: |
            static_rankings/
            frontend/static/rankings/
"""
    planted_paths = _upload_artifact_paths(planted)
    assert 'static_rankings/' in planted_paths
    assert any(_names_private_static_rankings(path) for path in planted_paths)


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
