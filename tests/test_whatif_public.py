"""A what-if link is not a public rankings query and not an official board."""
from unittest.mock import patch

from ranking_service import ALGO_VERSION, published_snapshot


def test_whatif_query_is_rejected_before_any_board_read(client, monkeypatch):
    monkeypatch.setenv('CFBD_OFFLINE', '1')
    monkeypatch.setenv('AI_MODE', 'stub')
    with patch('app.read_static_rankings_any', side_effect=AssertionError('static')):
        with patch('ranking_service.calculate_rankings_logic', side_effect=AssertionError('recompute')):
            with patch('api_integration.requests.get', side_effect=AssertionError('cfbd')):
                response = client.get('/rankings?year=2026&week=10&whatif=70-30-0-0')
    assert response.status_code == 400
    body = response.get_json()
    assert body['code'] == 'formula_params'
    assert 'whatif' in body['rejected']
    assert 'algo' not in body


def test_slider_board_is_not_a_published_snapshot():
    slider = {
        'official': False,
        'cached': False,
        'algo': None,
        'team_rankings': [{'team_name': 'Utah'}],
    }
    assert published_snapshot(slider) is None
    assert slider['algo'] != ALGO_VERSION
    assert published_snapshot({'team_rankings': slider['team_rankings']}) is None
