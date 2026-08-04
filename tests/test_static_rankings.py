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
