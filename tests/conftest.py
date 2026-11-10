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
_original_connect_ex = socket.socket.connect_ex
_original_getaddrinfo = socket.getaddrinfo


def _host_text(host):
    if isinstance(host, bytes):
        return host.decode('ascii', 'replace')
    return host


def _host_from_call(args):
    """Host from socket.connect(self, address) or create_connection(address)."""
    for arg in args:
        if isinstance(arg, tuple) and arg and isinstance(arg[0], (str, bytes)):
            return _host_text(arg[0])
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


def _deny_with(original):
    def deny(*args, **kwargs):
        host = _host_from_call(args)
        if host is not None and _is_loopback(host):
            return original(*args, **kwargs)
        _network_hits.append(1)
        raise AssertionError('live network is blocked in tests')
    return deny


_deny_network = _deny_with(_original_create_connection)
_deny_connect = _deny_with(_original_connect)
_deny_connect_ex = _deny_with(_original_connect_ex)


def _deny_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    """Block DNS for public hosts. Loopback still resolves from the local hosts file."""
    text = _host_text(host)
    if text is None or text == '' or (isinstance(text, str) and _is_loopback(text)):
        return _original_getaddrinfo(host, port, family, type, proto, flags)
    _network_hits.append(1)
    raise AssertionError('live network is blocked in tests')


@pytest.fixture(autouse=True)
def block_live_network(monkeypatch):
    """No test may open a socket or call CFBD. The session hook asserts zero hits."""
    monkeypatch.setattr(socket, 'getaddrinfo', _deny_getaddrinfo)
    monkeypatch.setattr(socket, 'create_connection', _deny_network)
    monkeypatch.setattr(socket.socket, 'connect', _deny_connect)
    monkeypatch.setattr(socket.socket, 'connect_ex', _deny_connect_ex)
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
