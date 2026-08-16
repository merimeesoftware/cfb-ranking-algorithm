"""Tests for The Drop subscribe helper and API route."""

from drop_service import subscribe_to_drop, validate_email


def test_validate_email():
    assert validate_email('fan@example.com')
    assert not validate_email('nope')
    assert not validate_email('')


def test_subscribe_accepts_without_webhook(monkeypatch):
    monkeypatch.delenv('DROP_WEBHOOK_URL', raising=False)
    status, body = subscribe_to_drop('fan@example.com', source='test')
    assert status == 200
    assert body['mode'] == 'accepted'
    assert 'Drop' in body['message']


def test_subscribe_rejects_bad_email(monkeypatch):
    monkeypatch.delenv('DROP_WEBHOOK_URL', raising=False)
    status, body = subscribe_to_drop('not-an-email')
    assert status == 400
    assert 'error' in body


def test_drop_subscribe_route(client):
    res = client.post('/drop/subscribe', json={'email': 'fan@example.com'})
    assert res.status_code == 200
    assert res.get_json()['mode'] == 'accepted'


def test_drop_subscribe_route_bad(client):
    res = client.post('/drop/subscribe', json={'email': 'bad'})
    assert res.status_code == 400
