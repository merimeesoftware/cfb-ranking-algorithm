"""Tests for static rankings precompute helpers."""
import json
import os
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault('CFBD_API_KEY', 'test-key-for-unit-tests')


def test_static_rankings_path():
    from static_rankings import static_path_for

    p = static_path_for(2024, 10, root='/tmp/rankings')
    assert str(p).endswith('2024/week-10.json')


def test_write_and_read_static_rankings():
    from static_rankings import write_static_rankings, read_static_rankings

    payload = {'year': 2024, 'week': 10, 'team_rankings': [{'team_name': 'A'}]}
    with tempfile.TemporaryDirectory() as tmp:
        path = write_static_rankings(payload, 2024, 10, root=tmp)
        assert path.exists()
        loaded = read_static_rankings(2024, 10, root=tmp)
        assert loaded['team_rankings'][0]['team_name'] == 'A'


def test_read_static_missing_returns_none():
    from static_rankings import read_static_rankings

    with tempfile.TemporaryDirectory() as tmp:
        assert read_static_rankings(1999, 1, root=tmp) is None


def test_static_path_stays_under_root():
    from static_rankings import _root_prefix, static_path_for

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'rankings'
        path = static_path_for(2024, 10, root=root)
        assert path.is_relative_to(root)
        assert path.name == 'week-10.json'
        prefix = _root_prefix(root)
        sibling = os.path.normpath(str(Path(tmp) / 'rankings_evil' / '2024' / 'week-10.json'))
        inside = os.path.normpath(str(path))
        assert inside.startswith(prefix)
        assert not sibling.startswith(prefix)


def test_read_rejects_path_traversal_and_out_of_range():
    from static_rankings import read_static_rankings, static_path_for

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'rankings'
        root.mkdir()
        secret = Path(tmp) / 'secret.json'
        secret.write_text('{"leaked": true}', encoding='utf-8')
        assert read_static_rankings('../secret', 1, root=root) is None
        assert read_static_rankings(2024, 99, root=root) is None
        assert read_static_rankings(2024, -1, root=root) is None
        with pytest.raises(ValueError):
            static_path_for(2024, 21, root=root)
