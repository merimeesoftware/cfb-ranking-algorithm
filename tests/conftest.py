"""Pytest configuration."""
import ipaddress
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
_original_create_connection = socket.create_connection
_original_connect = socket.socket.connect


def _host_from_call(args):
    """Host from socket.connect(self, address) or create_connection(address)."""
    for arg in args:
        if isinstance(arg, tuple) and arg and isinstance(arg[0], (str, bytes)):
            host = arg[0]
            if isinstance(host, bytes):
                host = host.decode('ascii', 'replace')
            return host
    return None


def _is_loopback(host: str) -> bool:
    bare = host.lower().split('%', 1)[0].strip('[]')
    if bare in {'localhost', '::1'}:
        return True
    try:
        parsed = ipaddress.ip_address(bare)
    except ValueError:
        return False
    if parsed.is_loopback:
        return True
    mapped = getattr(parsed, 'ipv4_mapped', None)
    return bool(mapped and mapped.is_loopback)


def _deny_network(*args, **kwargs):
    host = _host_from_call(args)
    if host is not None and _is_loopback(host):
        if args and isinstance(args[0], socket.socket):
            return _original_connect(*args, **kwargs)
        return _original_create_connection(*args, **kwargs)
    _network_hits.append(1)
    raise AssertionError('live network is blocked in tests')


@pytest.fixture(autouse=True)
def block_live_network(monkeypatch):
    """No test may open a socket or call CFBD. The session hook asserts zero hits."""
    monkeypatch.setattr(socket, 'create_connection', _deny_network)
    monkeypatch.setattr(socket.socket, 'connect', _deny_network)
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
