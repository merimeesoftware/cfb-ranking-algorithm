"""Rank and the score shown beside it are the same Elo number."""
from unittest.mock import patch

from ranking_service import get_or_calculate_rankings, publish_order


def _side(name, elo, blend):
    return {
        'team_name': name,
        'team_quality_score': elo,
        'final_ranking_score': blend,
        'record_score': 1000,
        'conference_quality_score': 70,
        'conference': 'SEC',
        'records': {
            'total_wins': 4,
            'total_losses': 1,
            'conf_wins': 2,
            'conf_losses': 1,
            'power_wins': 3,
            'power_losses': 1,
            'group_five_wins': 1,
            'group_five_losses': 0,
        },
        'sos': 1400,
        'sov': 1300,
        'wins_details': [],
        'losses_details': [],
    }


def _board():
    # Blend would put Soft first. Elo puts Sharp first.
    return {
        'year': 2024,
        'week': 9,
        'team_rankings': [
            _side('Soft', 1400.0, 1900.0),
            _side('Sharp', 1600.0, 1500.0),
        ],
        'conference_rankings': [],
    }


def test_adjacent_ranks_cannot_show_a_higher_score_below():
    ordered = publish_order(_board())['team_rankings']
    assert [team['team_name'] for team in ordered] == ['Sharp', 'Soft']
    scores = [team['ordering_score'] for team in ordered]
    assert scores == [1600.0, 1400.0]
    assert scores == sorted(scores, reverse=True)


def test_rankings_route_shows_elo_in_place_order(client):
    with patch('app.read_static_rankings_any', return_value=_board()):
        response = client.get('/rankings?year=2024&week=9')
    assert response.status_code == 200
    teams = response.get_json()['team_rankings']
    assert teams[0]['team_name'] == 'Sharp'
    assert teams[0]['ordering_score'] == 1600.0
    assert teams[0]['ordering_score'] >= teams[1]['ordering_score']


def test_matchup_rating_is_the_ordering_score(client):
    with patch('app.read_static_rankings_any', return_value=publish_order(_board())):
        response = client.get('/matchup?team_a=Soft&team_b=Sharp&year=2024&week=9')
    assert response.status_code == 200
    data = response.get_json()
    sharp = data['team_a'] if data['team_a']['name'] == 'Sharp' else data['team_b']
    soft = data['team_b'] if sharp is data['team_a'] else data['team_a']
    assert sharp['rank'] < soft['rank']
    assert sharp['tr_plus'] == 1600.0
    assert soft['tr_plus'] == 1400.0
    assert sharp['tr_plus'] > soft['tr_plus']
    assert sharp['rating_label'] == 'Elo'


def test_explain_total_matches_the_place(client, monkeypatch):
    monkeypatch.setenv('AI_MODE', 'stub')
    ordered = publish_order(_board())
    with patch('agent_service.get_or_calculate_rankings', return_value=ordered):
        response = client.post('/agent/explain', json={
            'team_name': 'Soft',
            'year': 2024,
            'week': 9,
            'question_id': 'why_here',
        })
    assert response.status_code == 200
    ctx = response.get_json()['context']
    assert ctx['rank'] == 2
    assert ctx['ordering_score'] == 1400.0
    assert ctx['formula_breakdown']['total'] == 1400.0


def test_computed_cache_hit_still_sorts_by_elo():
    class _Cache:
        def _generate_key(self, *args, **kwargs):
            return 'rankings-key'

        def get(self, key):
            return _board()

    with patch('ranking_service.get_cache', return_value=_Cache()):
        out = get_or_calculate_rankings(
            object(), 2030, 3, {}, prefer_static=False, allow_compute=True,
        )
    assert out is not None
    assert [team['team_name'] for team in out['team_rankings']] == ['Sharp', 'Soft']
