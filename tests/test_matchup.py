"""Head-to-head matchup returns ratings only."""

from matchup_service import build_matchup_payload


def test_build_matchup_payload_is_a_rating_comparison():
    teams = [
        {
            'team_name': 'Oregon',
            'final_ranking_score': 1840.0,
            'team_quality_score': 1700.0,
            'records': {'total_wins': 8, 'total_losses': 0},
        },
        {
            'team_name': 'Ohio State',
            'final_ranking_score': 1900.0,
            'team_quality_score': 1600.0,
            'records': {'total_wins': 7, 'total_losses': 1},
        },
    ]
    payload = build_matchup_payload(teams, 'Oregon', 'Ohio State', 2024, 9)
    assert payload is not None
    assert payload['team_a']['tr_plus'] == 1700.0
    assert payload['team_a']['rating_label'] == 'TR+'
    assert payload['team_b']['tr_plus'] == 1600.0
    assert payload['team_b']['rank'] == 2
    assert payload['team_a']['record'] == '8-0'
    assert payload['tr_plus_gap'] == 100.0
    assert payload['direct_games'] == []
    assert payload['common_opponents'] == []
    for banned in (
        'implied_spread', 'market_spread', 'favorite', 'delta', 'odds',
        'pick', 'spread', 'line', 'win_probability', 'win_chance', 'expected_winner',
    ):
        assert banned not in payload
    assert 'momentum' not in payload['team_a']
    assert 'record_ahead' not in payload['team_a']


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
        for banned in (
            'implied_spread', 'market_spread', 'favorite', 'delta', 'odds',
            'pick', 'spread', 'win_probability', 'win_chance', 'expected_winner',
        ):
            assert banned not in data
        if data.get('published') is not False:
            assert 'team_a' in data and 'team_b' in data
            assert data['tr_plus_gap'] == data['team_a']['tr_plus'] - data['team_b']['tr_plus']
            assert data['direct_games'] == []
            assert data['common_opponents'] == []
            assert 'momentum' not in data['team_a']
            assert 'record_ahead' not in data['team_a']


def _keys(value):
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            found.append(key)
            found.extend(_keys(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_keys(item))
    return found


def test_matchup_gap_schedule_and_results_use_the_sidecar_only():
    teams = [
        {
            'team_name': 'Oregon',
            'team_quality_score': 1800.0,
            'conference': 'Big Ten',
            'sos': 1600.0,
            'sos_rank': 4,
            'sov': 1700.0,
            'quality_wins': 3,
            'quality_losses': 0,
            'bad_losses': 0,
            'momentum': 0.4,
            'record_ahead': 1.2,
            'records': {'total_wins': 8, 'total_losses': 0},
        },
        {
            'team_name': 'Ohio State',
            'team_quality_score': 1700.0,
            'conference': 'Big Ten',
            'sos': 1580.0,
            'sos_rank': 8,
            'sov': 1650.0,
            'quality_wins': 2,
            'quality_losses': 1,
            'bad_losses': 0,
            'records': {'total_wins': 7, 'total_losses': 1},
        },
        {
            'team_name': 'Miami',
            'team_quality_score': 1550.0,
            'conference': 'ACC',
            'records': {'total_wins': 6, 'total_losses': 2},
        },
    ]
    games = [
        {
            'week': 1,
            'home': 'Oregon',
            'away': 'Ohio State',
            'home_score': 24,
            'away_score': 21,
            'neutral_site': False,
            'season_type': 'regular',
        },
        {
            'week': 8,
            'home': 'Ohio State',
            'away': 'Oregon',
            'home_score': 17,
            'away_score': 14,
            'neutral_site': True,
            'season_type': 'regular',
        },
        {
            'week': 2,
            'home': 'Oregon',
            'away': 'Miami',
            'home_score': 35,
            'away_score': 14,
            'neutral_site': False,
            'season_type': 'regular',
        },
        {
            'week': 3,
            'home': 'Miami',
            'away': 'Ohio State',
            'home_score': 10,
            'away_score': 31,
            'neutral_site': False,
            'season_type': 'regular',
        },
        {
            'week': 4,
            'home': 'Oregon',
            'away': 'Miami (OH)',
            'home_score': 42,
            'away_score': 7,
            'neutral_site': False,
            'season_type': 'regular',
        },
        {
            'week': 5,
            'home': 'Ohio State',
            'away': 'Miami (OH)',
            'home_score': 28,
            'away_score': 3,
            'neutral_site': False,
            'season_type': 'regular',
        },
        {
            'week': 6,
            'home': 'Oregon',
            'away': 'Idaho',
            'home_score': 49,
            'away_score': 0,
            'neutral_site': False,
            'season_type': 'regular',
        },
        {
            'week': 6,
            'home': 'Idaho',
            'away': 'Ohio State',
            'home_score': 0,
            'away_score': 42,
            'neutral_site': False,
            'season_type': 'regular',
        },
    ]
    payload = build_matchup_payload(teams, 'Oregon', 'Ohio State', 2024, 10, games=games)
    assert payload['tr_plus_gap'] == 100.0
    assert payload['team_a']['sos'] == 1600.0
    assert payload['team_a']['sos_rank'] == 4
    assert payload['team_a']['sov'] == 1700.0
    assert payload['team_a']['conference'] == 'Big Ten'
    assert payload['team_a']['quality_wins'] == 3
    assert payload['team_b']['quality_losses'] == 1
    assert payload['team_b']['bad_losses'] == 0
    assert 'momentum' not in payload['team_a']
    assert 'record_ahead' not in payload['team_a']
    assert [row['week'] for row in payload['direct_games']] == [1, 8]
    assert payload['direct_games'][0]['winner'] == 'Oregon'
    assert payload['direct_games'][0]['margin'] == 3
    names = [row['name'] for row in payload['common_opponents']]
    assert names == ['Idaho', 'Miami', 'Miami (OH)']
    miami = payload['common_opponents'][1]
    ohio = payload['common_opponents'][2]
    assert miami['name'] == 'Miami'
    assert miami['off_board'] is False
    assert miami['opponent_tr_plus'] == 1550.0
    assert ohio['name'] == 'Miami (OH)'
    assert ohio['off_board'] is True
    assert ohio['opponent_tr_plus'] is None
    idaho = payload['common_opponents'][0]
    assert idaho['off_board'] is True
    assert idaho['team_a_results'][0]['outcome'] == 'win'
    assert idaho['team_b_results'][0]['outcome'] == 'win'
    banned = {
        'implied_spread', 'market_spread', 'favorite', 'delta', 'odds',
        'pick', 'spread', 'line', 'win_probability', 'win_chance', 'expected_winner',
    }
    assert banned.isdisjoint(_keys(payload))


def test_missing_sidecar_stays_empty():
    teams = [
        {'team_name': 'Oregon', 'team_quality_score': 10.0, 'records': {'total_wins': 1, 'total_losses': 0}},
        {'team_name': 'Ohio State', 'team_quality_score': 9.0, 'records': {'total_wins': 1, 'total_losses': 0}},
    ]
    payload = build_matchup_payload(teams, 'Oregon', 'Ohio State', 2024, 10, games=None)
    assert payload['tr_plus_gap'] == 1.0
    assert payload['direct_games'] == []
    assert payload['common_opponents'] == []
