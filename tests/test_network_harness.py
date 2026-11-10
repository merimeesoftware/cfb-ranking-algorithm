"""Session and post calls hit the socket deny, not a live CFBD host."""
import pytest
import requests


def _expect_denied(call):
    import conftest

    before = len(conftest._network_hits)
    with pytest.raises(AssertionError, match='live network is blocked in tests'):
        call()
    assert len(conftest._network_hits) > before
    del conftest._network_hits[before:]


def test_requests_session_get_is_denied():
    _expect_denied(
        lambda: requests.Session().get('https://api.collegefootballdata.com/info')
    )


def test_requests_post_is_denied():
    _expect_denied(
        lambda: requests.post('https://api.collegefootballdata.com/info')
    )
