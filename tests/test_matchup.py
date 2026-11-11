"""Head-to-head matchup returns ratings only."""

from matchup_service import build_matchup_payload


def test_build_matchup_payload_is_a_rating_comparison():
    teams = [
        {
            'team_name': 'Oregon',
            'final_ranking_score': 1840.0,
            'records': {'total_wins': 8, 'total_losses': 0},
        },
        {
            'team_name': 'Ohio State',
            'final_ranking_score': 1800.0,
            'records': {'total_wins': 7, 'total_losses': 1},
        },
    ]
    payload = build_matchup_payload(teams, 'Oregon', 'Ohio State', 2024, 9)
    assert payload is not None
    assert payload['team_a']['tr_plus'] == 1840.0
    assert payload['team_b']['rank'] == 2
    assert payload['team_a']['record'] == '8-0'
    for banned in ('implied_spread', 'market_spread', 'favorite', 'delta', 'odds'):
        assert banned not in payload


def test_matchup_route_rejects_market_spread(client):
    res = client.get('/matchup?team_a=Oregon&team_b=Ohio%20State&year=2024&week=9&market_spread=3.5')
    assert res.status_code == 400
    assert 'market_spread' in res.get_json()['error']


def test_matchup_route_has_no_spread_fields(client, monkeypatch):
    monkeypatch.setenv('CFBD_OFFLINE', '1')
    res = client.get('/matchup?team_a=Oregon&team_b=Ohio%20State&year=2024&week=9')
    assert res.status_code in (200, 404)
    if res.status_code == 200:
        data = res.get_json()
        assert 'team_a' in data and 'team_b' in data
        for banned in ('implied_spread', 'market_spread', 'favorite', 'delta'):
            assert banned not in data
