"""Pytest configuration."""
import os
import socket
import urllib.request
from unittest.mock import patch

import pytest
import requests

os.environ.setdefault('CFBD_API_KEY', 'test-key-for-unit-tests')
os.environ.setdefault('CACHE_DIR', '/tmp/cfb-test-cache')
os.environ['CFBD_OFFLINE'] = '1'
os.environ.setdefault('AI_MODE', 'stub')
os.environ.setdefault('FLASK_ENV', 'development')

_network_hits = []


def _deny_network(*_args, **_kwargs):
    _network_hits.append(1)
    raise AssertionError('live network is blocked in tests')


@pytest.fixture(autouse=True)
def block_live_network(monkeypatch):
    """No test may open a socket or call CFBD. The session hook asserts zero hits."""
    monkeypatch.setattr(socket, 'create_connection', _deny_network)
    monkeypatch.setattr(requests, 'get', _deny_network)
    monkeypatch.setattr(urllib.request, 'urlopen', _deny_network)


@pytest.fixture(scope='session', autouse=True)
def assert_zero_live_network_calls():
    yield
    assert _network_hits == []


@pytest.fixture
def client():
    with patch('data_processor.CFBDataProcessor._initialize_conference_map'):
        from app import app
        app.config['TESTING'] = True
        with app.test_client() as c:
            yield c
