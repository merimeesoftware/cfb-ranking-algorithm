"""Tests for cache module."""
import os
import tempfile
import time

import pytest

from cache import Cache, FileCacheBackend, TTL_RANKINGS


@pytest.fixture
def temp_cache():
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = FileCacheBackend(cache_dir=tmpdir)
        yield Cache(backend=backend)


def test_cache_set_and_get(temp_cache):
    temp_cache.set('key1', {'value': 42}, TTL_RANKINGS, prefix='test')
    result = temp_cache.get('key1')
    assert result == {'value': 42}


def test_cache_expiry(temp_cache):
    temp_cache.set('key2', 'data', 1, prefix='test')
    assert temp_cache.get('key2') == 'data'
    time.sleep(1.1)
    assert temp_cache.get('key2') is None


def test_invalidate_prefix(temp_cache):
    temp_cache.set('a', 1, TTL_RANKINGS, prefix='games')
    temp_cache.set('b', 2, TTL_RANKINGS, prefix='games')
    key_a = temp_cache._generate_key('games', 2024)
    key_b = temp_cache._generate_key('games', 2023)
    temp_cache.set(key_a, 1, TTL_RANKINGS, prefix='games')
    temp_cache.set(key_b, 2, TTL_RANKINGS, prefix='games')
    temp_cache.invalidate_prefix('games')
    assert temp_cache.get(key_a) is None
    assert temp_cache.get(key_b) is None


def test_clear_all(temp_cache):
    temp_cache.set('x', 1, TTL_RANKINGS, prefix='test')
    temp_cache.clear_all()
    assert temp_cache.get('x') is None
    assert temp_cache.get_stats()['memory_entries'] == 0
