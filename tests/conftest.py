"""Pytest configuration."""
import os
from unittest.mock import patch

import pytest

os.environ.setdefault('CFBD_API_KEY', 'test-key-for-unit-tests')
os.environ.setdefault('CACHE_DIR', '/tmp/cfb-test-cache')
os.environ.setdefault('CFBD_OFFLINE', '1')
os.environ.setdefault('AI_MODE', 'stub')
os.environ.setdefault('FLASK_ENV', 'development')


@pytest.fixture
def client():
    with patch('data_processor.CFBDataProcessor._initialize_conference_map'):
        from app import app
        app.config['TESTING'] = True
        with app.test_client() as c:
            yield c
