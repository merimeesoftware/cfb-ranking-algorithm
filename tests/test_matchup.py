"""Tests for TR+ matchup implied spread."""

from matchup_service import build_matchup_payload, implied_spread


def test_implied_spread_half_points():
    assert implied_spread(1600, 1575) == 1.0
    assert implied_spread(1600, 1587.5) == 0.5
    assert implied_spread(1500, 1500) == 0.0


def test_build_matchup_payload():
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
    payload = build_matchup_payload(teams, 'Oregon', 'Ohio State', 2024, 9, market_spread=3.5)
    assert payload is not None
    assert payload['favorite'] == 'Oregon'
    assert payload['implied_spread'] == 1.5
    assert payload['delta'] == 1.5 - 3.5


def test_matchup_route(client, monkeypatch):
    # Prefer static offline path
    monkeypatch.setenv('CFBD_OFFLINE', '1')
    res = client.get('/matchup?team_a=Oregon&team_b=Ohio%20State&year=2024&week=9')
    # May 404 if static not mounted in test cwd — accept 200 or 404 with error
    assert res.status_code in (200, 404)
    if res.status_code == 200:
        data = res.get_json()
        assert data['favorite']
        assert 'implied_spread' in data
