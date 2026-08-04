"""Pytest configuration."""
import os

os.environ.setdefault('CFBD_API_KEY', 'test-key-for-unit-tests')
os.environ.setdefault('CACHE_DIR', '/tmp/cfb-test-cache')
