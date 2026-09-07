"""Offline tests for the betting layer (no CFBD)."""
from __future__ import annotations

import json
from pathlib import Path

from algo_lab.betting import (
    classify,
    edge_home,
    home_covers,
    model_home_spread,
    pick_from_edge,
    pick_hit,
    price_game,
    score_ats,
    steam_against_pick,
)

FIXTURE = Path(__file__).parent / 'fixtures' / 'sample_ats_slate.json'


def test_equal_elo_is_home_favorite_by_hfa():
    spread = model_home_spread(1500, 1500, hfa=50, elo_per_point=25)
    assert spread == -2.0


def test_elo_gap_prices_a_number():
    # 200 Elo + 50 HFA = 250 / 25 = 10
    spread = model_home_spread(1600, 1400, hfa=50, elo_per_point=25)
    assert spread == -10.0


def test_edge_sign_picks_the_right_side():
    # Model -7, market -3 → model likes home more
    assert edge_home(-7.0, -3.0) == -4.0
    assert pick_from_edge(-4.0) == 'home'
    # Model -3, market -10 → model likes away vs a fat number
    assert edge_home(-3.0, -10.0) == 7.0
    assert pick_from_edge(7.0) == 'away'


def test_thin_edge_is_no_pick():
    assert pick_from_edge(-1.0) is None


def test_home_covers_and_push():
    assert home_covers(24, 17, -3.5) == 'cover'
    assert home_covers(24, 21, -3.5) == 'fail'
    assert home_covers(24, 17, -7.0) == 'push'
    assert pick_hit('home', 'cover') is True
    assert pick_hit('away', 'cover') is False
    assert pick_hit('home', 'push') is None


def test_traffic_lights():
    assert classify(edge=-4.0, week=6, market_spread=-7.0)['signal'] == 'GREEN'
    assert classify(edge=-2.0, week=6, market_spread=-7.0)['signal'] == 'LEAN'
    assert classify(edge=-0.5, week=6, market_spread=-7.0)['signal'] == 'PASS'


def test_vetoes_early_week_fcs_landmine_missing_line():
    assert 'early_week' in classify(edge=-5.0, week=2, market_spread=-7.0)['vetoes']
    assert 'fcs' in classify(edge=-5.0, week=6, market_spread=-7.0, opponent_tier='FCS')['vetoes']
    assert 'landmine' in classify(edge=-8.0, week=6, market_spread=-35.0)['vetoes']
    assert 'no_line' in classify(edge=None, week=6, market_spread=None)['vetoes']


def test_early_week_does_not_veto_postseason():
    traffic = classify(
        edge=-5.0, week=1, market_spread=-7.0, season_type='postseason'
    )
    assert traffic['signal'] == 'GREEN'
    assert 'early_week' not in traffic['vetoes']


def test_fcs_veto_when_pick_is_fcs_side():
    # Fat FBS-home vs FCS-away number: model sides with FCS, |spread| <= landmine.
    game = {
        'home_team_name': 'G5 U',
        'away_team_name': 'FCS State',
        'week': 6,
        'season_type': 'regular',
        'home_conference_type': 'Group of 5',
        'away_conference_type': 'FCS',
        'market_spread_home': -24.0,
        'open_spread_home': -24.0,
    }
    row = price_game(game, {'G5 U': 1400.0, 'FCS State': 980.0})
    assert row['pick'] == 'away'
    assert abs(row['market_spread_home']) <= 28.0
    assert row['signal'] == 'PASS'
    assert 'fcs' in row['vetoes']
    assert 'landmine' not in row['vetoes']


def test_price_game_postseason_week_1_is_not_early_week():
    game = {
        'home_team_name': 'Alpha',
        'away_team_name': 'Bravo',
        'week': 1,
        'season_type': 'postseason',
        'home_conference_type': 'Power 4',
        'away_conference_type': 'Power 4',
        'market_spread_home': -3.5,
        'notes': 'bowl',
    }
    row = price_game(game, {'Alpha': 1680.0, 'Bravo': 1480.0})
    assert 'early_week' not in row['vetoes']
    assert row['signal'] == 'GREEN'


def test_steam_against_veto():
    # Open home -3, close home +1 → moved 4 pts toward away
    against = steam_against_pick('home', -3.0, 1.0)
    assert against == 4.0
    traffic = classify(edge=-4.0, week=6, market_spread=1.0, steam_against=against)
    assert traffic['signal'] == 'PASS'
    assert 'steam_against' in traffic['vetoes']


def test_steam_with_pick_does_not_veto():
    against = steam_against_pick('home', -3.0, -4.5)
    assert against == -1.5
    traffic = classify(edge=-4.0, week=6, market_spread=-4.5, steam_against=against)
    assert traffic['signal'] == 'GREEN'


def test_fixture_slate_signals_and_ats():
    data = json.loads(FIXTURE.read_text())
    rows = [price_game(g, data['ratings']) for g in data['games']]
    rows = [r for r in rows if r is not None]
    assert len(rows) == 5

    by_key = {(r['home_team'], r['away_team']): r for r in rows}

    alpha_charlie = by_key[('Alpha', 'Charlie')]
    assert alpha_charlie['pick'] == 'home'
    assert alpha_charlie['signal'] == 'GREEN'
    assert alpha_charlie['hit'] is True

    lean = by_key[('Bravo', 'Delta')]
    assert lean['signal'] == 'LEAN'

    week2 = by_key[('Alpha', 'Delta')]
    assert week2['signal'] == 'PASS'
    assert 'early_week' in week2['vetoes']

    fcs = by_key[('Alpha', 'FCS State')]
    assert fcs['signal'] == 'PASS'
    assert 'fcs' in fcs['vetoes']

    steam_game = by_key[('Charlie', 'Bravo')]
    assert steam_game['signal'] == 'PASS'
    assert 'steam_against' in steam_game['vetoes']

    green = score_ats(rows, signals=['GREEN'])
    assert green.graded == 1
    assert green.ats_pct == 1.0
