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
