"""The publish step commits derived rankings and ignores the private cache."""
import re
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


# PyYAML is not installed in CI (requirements.txt + pytest). This parser is
# the subset of workflow YAML the cache guard needs.
_BLOCK_INDICATORS = {'|', '|-', '|+', '>', '>-', '>+'}
_PR_EVENTS = ('pull_request', 'pull_request_target')
_PR_REF = {
    'pull_request': 'refs/pull/1/merge',
    'pull_request_target': 'refs/heads/main',
}
_CACHE_ACTION = re.compile(r'actions/cache(?:/(?:restore|save))?@\S+')
_STATIC_TOKEN = re.compile(r'(^|[^A-Za-z0-9_])static_rankings([^A-Za-z0-9_]|$)')


class _Step:
    __slots__ = ('uses', 'step_if', 'paths', 'keys', 'restore_keys')

    def __init__(self, uses, step_if, paths, keys, restore_keys):
        self.uses = uses
        self.step_if = step_if
        self.paths = paths
        self.keys = keys
        self.restore_keys = restore_keys


class _Job:
    __slots__ = ('workflow', 'name', 'events', 'job_if', 'uses', 'steps')

    def __init__(self, workflow, name, events, job_if, uses, steps):
        self.workflow = workflow
        self.name = name
        self.events = events
        self.job_if = job_if
        self.uses = uses
        self.steps = steps


class _Tok:
    def __init__(self, text):
        self.s = text
        self.i = 0
        self.n = len(text)

    def skip(self):
        while self.i < self.n and self.s[self.i].isspace():
            self.i += 1

    def startswith(self, word):
        self.skip()
        return self.s.startswith(word, self.i)

    def eat(self, word):
        self.skip()
        if word == '!' and self.s.startswith('!=', self.i):
            return False
        if self.s.startswith(word, self.i):
            self.i += len(word)
            return True
        return False

    def done(self):
        self.skip()
        return self.i >= self.n


def _indent(line):
    return len(line) - len(line.lstrip(' '))


def _strip_inline_comment(line):
    out = []
    quote = None
    for ch in line:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
            out.append(ch)
            continue
        if ch == '#':
            break
        out.append(ch)
    return ''.join(out).rstrip()


def _unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _read_block_scalar(lines, index, key_indent, fold):
    parts = []
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            look = index + 1
            while look < len(lines) and not lines[look].strip():
                look += 1
            if look >= len(lines) or _indent(lines[look]) <= key_indent:
                break
            parts.append('')
            index += 1
            continue
        if _indent(line) <= key_indent:
            break
        content = line.strip()
        if content.startswith('#'):
            index += 1
            continue
        parts.append(content)
        index += 1
    if fold:
        return ' '.join(part for part in parts if part != ''), index
    return '\n'.join(parts), index


def _skip_nested(lines, index, key_indent):
    while index < len(lines):
        if not lines[index].strip():
            index += 1
            continue
        if _indent(lines[index]) <= key_indent:
            break
        index += 1
    return index


def _take_scalar(lines, index, key_indent, inline):
    if inline in _BLOCK_INDICATORS:
        return _read_block_scalar(lines, index, key_indent, inline.startswith('>'))
    if inline:
        return _unquote(inline), index
    return '', _skip_nested(lines, index, key_indent)


def _split_flow(inline):
    inner = inline.strip()[1:-1]
    return [_unquote(part.strip()) for part in inner.split(',') if part.strip()]


def _scalar_list(inline, block_text, literal):
    if inline in _BLOCK_INDICATORS:
        if literal:
            return [line.strip() for line in block_text.splitlines() if line.strip()]
        return [block_text] if block_text else []
    if inline.startswith('[') and inline.endswith(']'):
        return _split_flow(inline)
    if inline:
        return [_unquote(inline)]
    return []


def _parse_with(lines, index, with_indent):
    data = {'path': [], 'key': [], 'restore-keys': []}
    while index < len(lines):
        if not lines[index].strip():
            index += 1
            continue
        if _indent(lines[index]) <= with_indent:
            break
        if lines[index].lstrip().startswith('#'):
            index += 1
            continue
        key_indent = _indent(lines[index])
        stripped = _strip_inline_comment(lines[index]).strip()
        key, _, inline = stripped.partition(':')
        key = key.strip()
        inline = inline.strip()
        index += 1
        if inline in _BLOCK_INDICATORS:
            text, index = _read_block_scalar(
                lines, index, key_indent, inline.startswith('>'),
            )
            values = _scalar_list(inline, text, inline.startswith('|'))
        elif inline:
            values = _scalar_list(inline, '', False)
        else:
            index = _skip_nested(lines, index, key_indent)
            values = []
        if key in data:
            data[key] = values
    return data, index


def _parse_step(lines, key_indent):
    uses = ''
    step_if = ''
    paths = []
    keys = []
    restore_keys = []
    index = 0
    while index < len(lines):
        if not lines[index].strip() or lines[index].lstrip().startswith('#'):
            index += 1
            continue
        if _indent(lines[index]) < key_indent:
            break
        if _indent(lines[index]) > key_indent:
            index += 1
            continue
        stripped = _strip_inline_comment(lines[index]).strip()
        key, _, inline = stripped.partition(':')
        key = key.strip()
        inline = inline.strip()
        index += 1
        if key == 'with' and not inline:
            with_map, index = _parse_with(lines, index, key_indent)
            paths = with_map['path']
            keys = with_map['key']
            restore_keys = with_map['restore-keys']
            continue
        value, index = _take_scalar(lines, index, key_indent, inline)
        if key == 'if':
            step_if = value
        elif key == 'uses':
            uses = value
    return _Step(uses, step_if, paths, keys, restore_keys)


def _read_sequence(lines, index, parent_indent):
    items = []
    while index < len(lines):
        while index < len(lines) and not lines[index].strip():
            index += 1
        if index >= len(lines) or _indent(lines[index]) <= parent_indent:
            break
        if lines[index].lstrip().startswith('#'):
            index += 1
            continue
        stripped = lines[index].lstrip()
        if not stripped.startswith('- '):
            break
        item_indent = _indent(lines[index])
        first = stripped[2:].strip()
        index += 1
        body = []
        if first:
            body.append(' ' * (item_indent + 2) + first)
        while index < len(lines):
            if not lines[index].strip():
                look = index + 1
                while look < len(lines) and not lines[look].strip():
                    look += 1
                if look < len(lines) and _indent(lines[look]) > item_indent:
                    index += 1
                    continue
                break
            if _indent(lines[index]) <= item_indent:
                break
            body.append(lines[index])
            index += 1
        items.append(_parse_step(body, item_indent + 2))
    return items, index


def _parse_job_body(lines):
    job_if = ''
    uses = ''
    steps = []
    index = 0
    while index < len(lines):
        if not lines[index].strip() or lines[index].lstrip().startswith('#'):
            index += 1
            continue
        indent = _indent(lines[index])
        stripped = _strip_inline_comment(lines[index]).strip()
        key, _, inline = stripped.partition(':')
        key = key.strip()
        inline = inline.strip()
        index += 1
        if key == 'steps' and not inline:
            steps, index = _read_sequence(lines, index, indent)
            continue
        value, index = _take_scalar(lines, index, indent, inline)
        if key == 'if':
            job_if = value
        elif key == 'uses':
            uses = value
    return job_if, uses, steps


def _top_sections(lines):
    sections = {}
    index = 0
    while index < len(lines):
        raw = lines[index]
        if not raw.strip() or raw.lstrip().startswith('#') or raw[0].isspace():
            index += 1
            continue
        stripped = _strip_inline_comment(raw).strip()
        key, _, inline = stripped.partition(':')
        inline = inline.strip()
        index += 1
        start = index
        while index < len(lines):
            line = lines[index]
            if line.strip() and not line[0].isspace() and not line.lstrip().startswith('#'):
                break
            index += 1
        sections[key.strip()] = (inline, lines[start:index])
    return sections


def _parse_events(inline, lines):
    if inline.startswith('[') and inline.endswith(']'):
        return set(_split_flow(inline))
    if inline and inline not in _BLOCK_INDICATORS:
        return {_unquote(inline)}
    events = set()
    for line in lines:
        if not line.strip() or line.lstrip().startswith('#') or _indent(line) != 2:
            continue
        stripped = _strip_inline_comment(line).strip()
        if stripped.startswith('- '):
            continue
        name = _unquote(stripped.split(':', 1)[0].strip())
        if name:
            events.add(name)
    return events


def _parse_jobs(workflow, events, lines):
    jobs = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith('#'):
            index += 1
            continue
        if _indent(line) != 2:
            index += 1
            continue
        name = _unquote(_strip_inline_comment(line).strip().split(':', 1)[0].strip())
        index += 1
        start = index
        while index < len(lines):
            current = lines[index]
            if current.strip() and not current.lstrip().startswith('#') and _indent(current) <= 2:
                break
            index += 1
        job_if, uses, steps = _parse_job_body(lines[start:index])
        jobs.append(_Job(workflow, name, set(events), job_if, uses, steps))
    return jobs


def _parse_workflow(name, text):
    sections = _top_sections(text.splitlines())
    on_inline, on_lines = sections.get('on', ('', []))
    events = _parse_events(on_inline, on_lines)
    _jobs_inline, job_lines = sections.get('jobs', ('', []))
    return _parse_jobs(name, events, job_lines)


def _is_cache_action(uses):
    value = _unquote(uses.strip())
    if not value:
        return False
    return _CACHE_ACTION.match(value.split()[0]) is not None


def _glob_covers_static_rankings(pattern):
    cleaned = pattern.lstrip('./')
    regex = re.escape(cleaned).replace(r'\*\*', '.*').replace(r'\*', '[^/]*').replace(r'\?', '[^/]')
    return any(
        re.fullmatch(regex, candidate) is not None
        for candidate in ('static_rankings', 'static_rankings/games.json')
    )


def _path_covers_static_rankings(path):
    normalized = _unquote(path.strip()).replace('\\', '/')
    if normalized in {'.', './', '*', '**', '**/*', './**', '/*', './*'}:
        return True
    if _STATIC_TOKEN.search(normalized):
        return True
    parts = []
    for segment in normalized.split('/'):
        if segment in ('', '.'):
            continue
        if segment == '..':
            if parts:
                parts.pop()
            continue
        parts.append(segment)
    if any(
        segment == 'static_rankings' or segment.startswith('static_rankings')
        for segment in parts
    ):
        return True
    if any(ch in normalized for ch in '*?['):
        return _glob_covers_static_rankings(normalized)
    return False


def _paths_cover(paths):
    return any(_path_covers_static_rankings(path) for path in paths)


def _key_literals(step):
    literals = []
    for raw in list(step.keys) + list(step.restore_keys):
        text = _unquote(raw.strip())
        if not text:
            continue
        literal = text.split('${{', 1)[0].strip()
        if literal:
            literals.append(literal)
    return literals


def _associated_prefixes(jobs):
    prefixes = []
    for job in jobs:
        for step in job.steps:
            if not _is_cache_action(step.uses) or not _paths_cover(step.paths):
                continue
            for literal in _key_literals(step):
                if len(literal) >= 8 and literal not in prefixes:
                    prefixes.append(literal)
    return prefixes


def _keys_cover(step, prefixes):
    for raw in list(step.keys) + list(step.restore_keys):
        if _STATIC_TOKEN.search(raw):
            return True
    for literal in _key_literals(step):
        if len(literal) < 8:
            continue
        for prefix in prefixes:
            if literal.startswith(prefix) or prefix.startswith(literal):
                return True
    return False


def _covers(step, prefixes):
    return _paths_cover(step.paths) or _keys_cover(step, prefixes)


def _read_string(tok):
    tok.skip()
    quote = tok.s[tok.i]
    tok.i += 1
    chars = []
    while tok.i < tok.n:
        ch = tok.s[tok.i]
        tok.i += 1
        if ch == quote:
            return ''.join(chars)
        chars.append(ch)
    raise ValueError('unterminated string')


def _read_ident(tok):
    tok.skip()
    start = tok.i
    while tok.i < tok.n and (tok.s[tok.i].isalnum() or tok.s[tok.i] in '._'):
        tok.i += 1
    return tok.s[start:tok.i]


def _skip_balanced(tok):
    depth = 1
    quote = None
    while tok.i < tok.n and depth:
        ch = tok.s[tok.i]
        tok.i += 1
        if quote:
            if ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
        elif ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
    return depth == 0


def _negate(value):
    if value is None:
        return None
    return not value


def _and(left, right):
    if left is False or right is False:
        return False
    if left is True and right is True:
        return True
    return None


def _or(left, right):
    if left is True or right is True:
        return True
    if left is False and right is False:
        return False
    return None


def _cmp(left, right, equal):
    if left is None or right is None:
        return None
    return (left == right) if equal else (left != right)


def _parse_primary(tok, event, ref):
    if tok.eat('('):
        value = _parse_or(tok, event, ref)
        if not tok.eat(')'):
            raise ValueError('paren')
        return value
    if tok.startswith("'") or tok.startswith('"'):
        return _read_string(tok)
    ident = _read_ident(tok)
    if not ident:
        raise ValueError('token')
    if tok.eat('('):
        if not _skip_balanced(tok):
            raise ValueError('call')
        return None
    if ident == 'github.event_name':
        return event
    if ident == 'github.ref':
        return ref
    if ident == 'true':
        return True
    if ident == 'false':
        return False
    return None


def _parse_unary(tok, event, ref):
    if tok.eat('!'):
        return _negate(_parse_unary(tok, event, ref))
    return _parse_primary(tok, event, ref)


def _parse_cmp(tok, event, ref):
    value = _parse_unary(tok, event, ref)
    if tok.eat('=='):
        return _cmp(value, _parse_unary(tok, event, ref), True)
    if tok.eat('!='):
        return _cmp(value, _parse_unary(tok, event, ref), False)
    return value


def _parse_and(tok, event, ref):
    value = _parse_cmp(tok, event, ref)
    while tok.eat('&&'):
        value = _and(value, _parse_cmp(tok, event, ref))
    return value


def _parse_or(tok, event, ref):
    value = _parse_and(tok, event, ref)
    while tok.eat('||'):
        value = _or(value, _parse_and(tok, event, ref))
    return value


def _decision(expr, event, ref):
    """True, False, or None when the if expression cannot be proved."""
    if not expr or not expr.strip():
        return True
    text = ' '.join(expr.replace('\n', ' ').split())
    if text.startswith('${{') and text.endswith('}}'):
        text = text[3:-2].strip()
    try:
        tok = _Tok(text)
        value = _parse_or(tok, event, ref)
        if not tok.done():
            return None
        return value
    except ValueError:
        return None


def _local_workflow(uses):
    value = _unquote(uses.strip())
    if not (value.startswith('./') or value.startswith('.github/')):
        return None
    match = re.search(r'\.github/workflows/([^/@\s]+\.ya?ml)', value)
    if not match:
        return None
    return match.group(1)


def _load_jobs(workflows):
    jobs = []
    events = {}
    for name, text in workflows:
        parsed = _parse_workflow(name, text)
        jobs.extend(parsed)
        if parsed:
            events[name] = set(parsed[0].events)
        else:
            sections = _top_sections(text.splitlines())
            on_inline, on_lines = sections.get('on', ('', []))
            events[name] = _parse_events(on_inline, on_lines)
    return jobs, events


def static_rankings_cache_pr_violations(workflows):
    """Cache steps on pull_request or pull_request_target that can read the raw rows."""
    jobs, events = _load_jobs(workflows)
    prefixes = _associated_prefixes(jobs)
    by_file = {}
    for job in jobs:
        by_file.setdefault(job.workflow, []).append(job)
    violations = []
    queue = []
    for job in jobs:
        for event in _PR_EVENTS:
            if event in job.events:
                queue.append((job, event, _PR_REF[event], event, job.workflow))
    seen = set()
    while queue:
        job, trigger, ref, context, origin = queue.pop()
        marker = (job.workflow, job.name, trigger, context, origin)
        if marker in seen:
            continue
        seen.add(marker)
        if _decision(job.job_if, context, ref) is False:
            continue
        for step in job.steps:
            if not _is_cache_action(step.uses) or not _covers(step, prefixes):
                continue
            if _decision(step.step_if, context, ref) is False:
                continue
            violations.append(
                f'{origin} -> {job.workflow}:{job.name} can restore static_rankings '
                f'on {trigger} ({context}) via {step.uses}'
            )
        callee = _local_workflow(job.uses)
        if not callee or 'workflow_call' not in events.get(callee, ()):
            continue
        for callee_job in by_file.get(callee, []):
            queue.append((callee_job, trigger, ref, 'workflow_call', job.workflow))
    return violations


def _triggered_restores(workflows):
    jobs, events = _load_jobs(workflows)
    prefixes = _associated_prefixes(jobs)
    rows = {
        name: {'events': set(event_names), 'reaches': set()}
        for name, event_names in events.items()
    }
    for job in jobs:
        for step in job.steps:
            if not _is_cache_action(step.uses) or not _covers(step, prefixes):
                continue
            for event in job.events:
                ref = _PR_REF.get(event, 'refs/heads/main')
                if _decision(job.job_if, event, ref) is False:
                    continue
                if _decision(step.step_if, event, ref) is False:
                    continue
                rows[job.workflow]['reaches'].add(event)
    return rows


def _planted(on_block, steps, job_if=''):
    if_line = f'    if: {job_if}\n' if job_if else ''
    return (
        'name: Planted\n'
        'on:\n'
        f'{on_block.rstrip()}\n'
        'jobs:\n'
        '  job:\n'
        f'{if_line}'
        '    runs-on: ubuntu-latest\n'
        '    steps:\n'
        f'{steps}'
    )


_CACHE_STEP = """\
      - name: Restore raw rows
        uses: actions/cache@v4
        with:
          path: static_rankings
          key: cfbd-precompute-${{ github.run_id }}
          restore-keys: cfbd-precompute-
"""

_ALLOW_IF = (
    "github.event_name == 'schedule' || "
    "github.event_name == 'workflow_dispatch' || "
    "(github.event_name == 'push' && github.ref == 'refs/heads/main')"
)


def test_pull_request_workflows_do_not_restore_static_rankings_cache():
    """pull_request and pull_request_target jobs cannot restore the raw cache."""
    assert _decision(_ALLOW_IF, 'pull_request', 'refs/pull/1/merge') is False
    assert _decision(_ALLOW_IF, 'pull_request_target', 'refs/heads/main') is False
    assert _decision(_ALLOW_IF, 'workflow_call', 'refs/pull/1/merge') is False
    assert _decision(_ALLOW_IF, 'workflow_run', 'refs/heads/main') is False
    assert _decision(_ALLOW_IF, 'schedule', 'refs/heads/main') is True
    assert _decision(_ALLOW_IF, 'workflow_dispatch', 'refs/heads/feature') is True
    assert _decision(_ALLOW_IF, 'push', 'refs/heads/main') is True
    assert _decision(_ALLOW_IF, 'push', 'refs/heads/feature') is False
    deny = (
        "github.event_name != 'pull_request' && "
        "github.event_name != 'pull_request_target'"
    )
    assert _decision(deny, 'pull_request', 'refs/pull/1/merge') is False
    assert _decision(deny, 'pull_request_target', 'refs/heads/main') is False
    assert _decision(deny, 'workflow_call', 'refs/pull/1/merge') is True
    assert _decision("github.ref == 'refs/heads/main'", 'pull_request', 'refs/pull/1/merge') is False
    assert _decision(
        "github.ref == 'refs/heads/main'",
        'pull_request_target',
        'refs/heads/main',
    ) is True

    files = [(path.name, path.read_text(encoding='utf-8')) for path in _workflow_files()]
    by_name = dict(files)
    assert static_rankings_cache_pr_violations(files) == []
    rows = _triggered_restores(files)
    assert rows['ci.yml']['events'] == {'push', 'pull_request'}
    assert rows['preview-stills.yml']['events'] == {'pull_request'}
    assert rows['ci.yml']['reaches'] == set()
    assert rows['preview-stills.yml']['reaches'] == set()
    precompute = rows['precompute-rankings.yml']
    assert precompute['events'] == {'schedule', 'workflow_dispatch'}
    assert {'schedule', 'workflow_dispatch'} <= precompute['reaches']
    assert precompute['reaches'] <= {'schedule', 'workflow_dispatch', 'push'}
    assert precompute['reaches'].isdisjoint({'pull_request', 'pull_request_target'})
    for row in rows.values():
        assert row['reaches'].isdisjoint({'pull_request', 'pull_request_target'})

    jobs = _parse_workflow('precompute-rankings.yml', by_name['precompute-rankings.yml'])
    assert [job.name for job in jobs] == ['precompute', 'publish']
    cache_steps = [
        step for step in jobs[0].steps if _is_cache_action(step.uses)
    ]
    assert len(cache_steps) == 1
    assert cache_steps[0].paths == ['.cache', 'static_rankings']
    assert cache_steps[0].keys == ['cfbd-precompute-${{ github.run_id }}']
    assert cache_steps[0].restore_keys == ['cfbd-precompute-']
    assert _decision(cache_steps[0].step_if, 'pull_request', 'refs/pull/1/merge') is False
    assert _decision(cache_steps[0].step_if, 'pull_request_target', 'refs/heads/main') is False
    assert _decision(cache_steps[0].step_if, 'workflow_call', 'refs/pull/1/merge') is False
    assert _decision(cache_steps[0].step_if, 'schedule', 'refs/heads/main') is True
    assert _decision(cache_steps[0].step_if, 'workflow_dispatch', 'refs/heads/main') is True
    assert _decision(cache_steps[0].step_if, 'push', 'refs/heads/main') is True
    assert _decision(cache_steps[0].step_if, 'push', 'refs/heads/feature') is False
    assert 'uses: actions/cache@v4' in by_name['precompute-rankings.yml']

    def violations_for(on_block, steps, job_if='', extra=()):
        planted = [('planted.yml', _planted(on_block, steps, job_if)), *extra]
        return static_rankings_cache_pr_violations(planted)

    assert violations_for('  pull_request:', _CACHE_STEP)
    assert violations_for('  pull_request_target:', _CACHE_STEP)
    assert violations_for('  pull_request:\n  pull_request_target:', _CACHE_STEP)
    assert violations_for(
        '  pull_request:',
        _CACHE_STEP,
        job_if=_ALLOW_IF,
    ) == []
    assert violations_for(
        '  pull_request:\n  pull_request_target:',
        """\
      - uses: actions/cache/restore@v4
        if: github.event_name != 'pull_request' && github.event_name != 'pull_request_target'
        with:
          path: |
            .cache
            static_rankings
          key: cfbd-precompute-${{ github.run_id }}
""",
    ) == []
    assert violations_for(
        '  pull_request_target:',
        """\
      - if: github.event_name != 'pull_request'
        uses: actions/cache/save@v4
        with:
          path: static_rankings
          key: cfbd-precompute-${{ github.run_id }}
""",
    )
    assert violations_for(
        '  pull_request_target:',
        """\
      - uses: actions/cache@0123456789abcdef0123456789abcdef01234567
        if: github.ref == 'refs/heads/main'
        with:
          path: static_rankings
          key: cfbd-precompute-${{ github.run_id }}
""",
    )
    assert violations_for(
        '  pull_request:',
        """\
      - uses: actions/cache@v4
        if: github.ref == 'refs/heads/main'
        with:
          path: static_rankings
          key: private-${{ github.run_id }}
""",
    ) == []
    assert violations_for(
        '  pull_request:',
        """\
      - uses: actions/setup-python@v7
        with:
          python-version: "3.11"
          cache: pip
      - uses: actions/cache@v4
        with:
          path: frontend/static/rankings
          key: public-${{ github.run_id }}
      - run: |
          echo uses: actions/cache@v4
          echo static_rankings
""",
    ) == []
    assert violations_for(
        '  pull_request:',
        """\
      - uses: actions/cache@v4
        with:
          path: |
            *
            .
            static_rankings*
            frontend/static/rankings/../../static_rankings
          key: other-${{ github.run_id }}
""",
    )
    assert violations_for(
        '  pull_request:',
        """\
      - uses: actions/cache@v4
        with:
          path: .cache
          key: pip-${{ runner.os }}-${{ hashFiles('requirements.txt') }}
""",
    ) == []
    assert violations_for(
        '  pull_request:',
        """\
      - uses: actions/cache/restore@v4
        with:
          path: .cache
          key: cfbd-precompute-${{ github.run_id }}
          restore-keys: cfbd-precompute-
""",
        extra=files,
    )

    caller = """\
name: Caller
on:
  pull_request:
jobs:
  call:
    uses: ./.github/workflows/callee.yml
"""
    callee = """\
name: Callee
on:
  workflow_call:
jobs:
  restore:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/cache/restore@v4
        if: github.event_name != 'pull_request'
        with:
          path: static_rankings
          key: cfbd-precompute-${{ github.run_id }}
"""
    pair = [('caller.yml', caller), ('callee.yml', callee)]
    assert static_rankings_cache_pr_violations(pair)
    guarded_callee = callee.replace(
        "if: github.event_name != 'pull_request'",
        f'if: {_ALLOW_IF}',
    )
    assert static_rankings_cache_pr_violations([
        ('caller.yml', caller),
        ('callee.yml', guarded_callee),
    ]) == []

    opened = by_name['precompute-rankings.yml'].replace(
        'on:\n  schedule:\n',
        'on:\n  pull_request:\n  pull_request_target:\n  schedule:\n',
        1,
    )
    assert static_rankings_cache_pr_violations([
        ('precompute-rankings.yml', opened),
    ]) == []
    if_block = """\
        if: >-
          github.event_name == 'schedule' ||
          github.event_name == 'workflow_dispatch' ||
          (github.event_name == 'push' && github.ref == 'refs/heads/main')
"""
    assert if_block in opened
    assert static_rankings_cache_pr_violations([
        ('precompute-rankings.yml', opened.replace(if_block, '')),
    ])


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
    assert 'actions/download-artifact@v7' in text
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
