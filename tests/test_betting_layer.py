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

    week2 = by_key[('Alpha', 'Delta')]
    assert week2['signal'] == 'PASS'
    assert 'early_week' in week2['vetoes']

    fcs = by_key[('Alpha', 'FCS State')]
    assert fcs['signal'] == 'PASS'
    assert 'fcs' in fcs['vetoes'] or 'landmine' in fcs['vetoes']

    steam_game = by_key[('Charlie', 'Bravo')]
    assert steam_game['signal'] == 'PASS'
    assert 'steam_against' in steam_game['vetoes']

    green = score_ats(rows, signals=['GREEN'])
    assert green.graded >= 1
    assert green.ats_pct == 1.0
