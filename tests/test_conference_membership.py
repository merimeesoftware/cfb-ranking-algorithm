"""#101: season-aware conference membership, offline only."""
import copy
import json
from collections import Counter
from unittest.mock import MagicMock

import pytest

from algo_lab.backtest import _team_meta_from_games
from conference_membership import (
    MAP_PATH,
    ConferenceMembership,
    MembershipError,
    load_membership,
)
from data_processor import CFBDataProcessor
from ranking_algorithm import TeamQualityRanker
from ranking_service import DEFAULT_CONFIG

# Today's /teams labels (no year parameter): what the old code applied to every season.
TODAY_TEAMS = {
    'USC': {'conference': 'Big Ten', 'logos': []},
    'Oregon': {'conference': 'Big Ten', 'logos': []},
    'Texas': {'conference': 'SEC', 'logos': []},
    'Oklahoma': {'conference': 'SEC', 'logos': []},
    'Boise State': {'conference': 'Pac-12', 'logos': []},
    'Utah State': {'conference': 'Pac-12', 'logos': []},
    'Kansas': {'conference': 'Big 12', 'logos': []},
    'Ohio State': {'conference': 'Big Ten', 'logos': []},
    'Alabama': {'conference': 'SEC', 'logos': []},
}


def _game(week, home, away, home_conf, away_conf, hs=28, as_=21):
    return {
        'week': week,
        'season_type': 'regular',
        'completed': True,
        'home_team_name': home,
        'away_team_name': away,
        'home_score': hs,
        'away_score': as_,
        'home_conference': home_conf,
        'away_conference': away_conf,
    }


def _processor(games):
    client = MagicMock()
    client.get_teams_with_logos.return_value = TODAY_TEAMS
    client.get_games.return_value = games
    return CFBDataProcessor(api_client=client)


def _confs(games):
    out = {}
    for g in games:
        out[g['home_team_name']] = (g['home_conference'], g['home_conference_type'])
        out[g['away_team_name']] = (g['away_conference'], g['away_conference_type'])
    return out


# --- the map itself -------------------------------------------------------

@pytest.mark.parametrize('team,before,after', [
    ('USC', 'Pac-12', 'Big Ten'),
    ('Oregon', 'Pac-12', 'Big Ten'),
    ('Texas', 'Big 12', 'SEC'),
    ('Oklahoma', 'Big 12', 'SEC'),
    ('Utah', 'Pac-12', 'Big 12'),
    ('Stanford', 'Pac-12', 'ACC'),
    ('SMU', 'American Athletic', 'ACC'),
])
def test_realigned_team_gets_each_seasons_conference(team, before, after):
    m = load_membership()
    assert m.conference_for(team, 2023) == before
    assert m.conference_for(team, 2024) == after


def test_pac12_is_power4_only_through_2023():
    m = load_membership()
    assert m.tier_for('Pac-12', 2023) == 'Power 4'
    for season in (2024, 2025, 2026):
        assert m.tier_for('Pac-12', season) == 'Group of 5'
    assert m.conference_for('Boise State', 2025) == 'Mountain West'
    assert m.conference_for('Boise State', 2026) == 'Pac-12'
    assert sorted(t for t, c in m.season_map(2024).items() if c == 'Pac-12') == [
        'Oregon State', 'Washington State']


def test_other_dated_moves():
    m = load_membership()
    assert m.conference_for('Notre Dame', 2020) == 'ACC'
    assert m.conference_for('Notre Dame', 2021) == 'FBS Independents'
    assert m.conference_for('BYU', 2022) == 'FBS Independents'
    assert m.conference_for('BYU', 2023) == 'Big 12'
    assert m.conference_for('Army', 2023) == 'FBS Independents'
    assert m.conference_for('Army', 2024) == 'American Athletic'
    assert m.conference_for('Idaho', 2017) == 'Sun Belt'
    assert m.conference_for('Idaho', 2018) is None
    assert m.conference_for('Liberty', 2017) is None
    assert m.conference_for('Kennesaw State', 2023) is None
    assert m.conference_for('Kennesaw State', 2024) == 'Conference USA'


def test_fbs_counts_per_season():
    m = load_membership()
    sizes = {s: len(m.season_map(s)) for s in range(2017, 2027)}
    assert sizes == {2017: 130, 2018: 130, 2019: 130, 2020: 130, 2021: 130,
                     2022: 131, 2023: 133, 2024: 134, 2025: 136, 2026: 138}
    c2023 = Counter(m.season_map(2023).values())
    assert (c2023['Pac-12'], c2023['Big 12'], c2023['Big Ten'], c2023['SEC']) == (12, 14, 14, 14)
    c2024 = Counter(m.season_map(2024).values())
    assert (c2024['Pac-12'], c2024['Big 12'], c2024['Big Ten'], c2024['SEC'], c2024['ACC']) == (
        2, 16, 18, 16, 17)


def test_every_move_has_a_source_and_base_is_sourced():
    payload = json.loads(MAP_PATH.read_text(encoding='utf-8'))
    assert payload['base']['source']
    assert payload['moves'] and all(m['source'].startswith('https://') for m in payload['moves'])


def test_inconsistent_map_is_rejected():
    payload = json.loads(MAP_PATH.read_text(encoding='utf-8'))
    bad = copy.deepcopy(payload)
    for move in bad['moves']:
        if move['team'] == 'USC':
            move['to'] = 'SEC'  # base says Big Ten
    with pytest.raises(MembershipError):
        ConferenceMembership(bad)
    no_tier = copy.deepcopy(payload)
    del no_tier['tiers']['Pac-12']
    with pytest.raises(MembershipError):
        ConferenceMembership(no_tier)


# --- unknown input is explicit -------------------------------------------

@pytest.mark.parametrize('season', [2016, 2027])
def test_unknown_season_fails_closed(season):
    m = load_membership()
    with pytest.raises(MembershipError, match='outside conference membership coverage'):
        m.conference_for('USC', season)
    proc = _processor([_game(1, 'USC', 'Oregon', 'Pac-12', 'Pac-12')])
    with pytest.raises(MembershipError):
        proc.get_games_for_season(season)


def test_unknown_season_fails_closed_even_without_games():
    with pytest.raises(MembershipError):
        _processor([]).get_games_for_season(2027)


def test_non_fbs_team_keeps_game_label_as_fcs():
    proc = _processor([_game(1, 'Texas', 'Incarnate Word', 'Big 12', 'Southland')])
    confs = _confs(proc.get_games_for_season(2023))
    assert confs['Incarnate Word'] == ('Southland', 'FCS')


def test_unknown_team_claiming_fbs_conference_fails_closed():
    proc = _processor([_game(1, 'Texas', 'Made Up U', 'Big 12', 'Big 12')])
    with pytest.raises(MembershipError, match='Made Up U'):
        proc.get_games_for_season(2023)


# --- wiring: processor, conference quality, conference_rankings, backtest --

def test_processor_ignores_todays_teams_labels():
    games = [
        _game(1, 'USC', 'Oregon', 'Pac-12', 'Pac-12'),
        _game(1, 'Texas', 'Kansas', 'Big 12', 'Big 12'),
        _game(1, 'Boise State', 'Utah State', 'Mountain West', 'Mountain West'),
    ]
    c2023 = _confs(_processor(games).get_games_for_season(2023))
    assert c2023['USC'] == ('Pac-12', 'Power 4')
    assert c2023['Texas'] == ('Big 12', 'Power 4')
    assert c2023['Boise State'] == ('Mountain West', 'Group of 5')
    c2024 = _confs(_processor(games).get_games_for_season(2024))
    assert c2024['USC'] == ('Big Ten', 'Power 4')
    assert c2024['Texas'] == ('SEC', 'Power 4')
    assert c2024['Boise State'] == ('Mountain West', 'Group of 5')
    c2026 = _confs(_processor(games).get_games_for_season(2026))
    assert c2026['Boise State'] == ('Pac-12', 'Group of 5')


def _rank(games):
    ranker = TeamQualityRanker(DEFAULT_CONFIG.copy(), {})
    for g in games:
        ranker.update_quality_scores(g)
    return ranker, ranker.calculate_final_rankings()


def test_conference_quality_and_rankings_use_season_membership():
    games = [
        _game(1, 'USC', 'Alabama', 'Pac-12', 'SEC'),
        _game(2, 'Oregon', 'Ohio State', 'Pac-12', 'Big Ten'),
        _game(3, 'USC', 'Oregon', 'Pac-12', 'Pac-12'),
    ]
    ranker, out = _rank(_processor(games).get_games_for_season(2023))
    cq = ranker.calculate_conference_quality()
    assert 'Pac-12' in cq
    by_conf = {c['conference_name']: c for c in out['conference_rankings']}
    assert by_conf['Pac-12']['number_of_teams'] == 2
    assert by_conf['Pac-12']['conference_type'] == 'Power 4'
    assert by_conf['Big Ten']['number_of_teams'] == 1  # Ohio State only in 2023

    ranker, out = _rank(_processor(games).get_games_for_season(2024))
    by_conf = {c['conference_name']: c for c in out['conference_rankings']}
    assert 'Pac-12' not in by_conf
    assert by_conf['Big Ten']['number_of_teams'] == 3


def test_conference_rankings_tier_follows_season():
    games = [_game(1, 'Boise State', 'Kansas', 'Mountain West', 'Big 12'),
             _game(2, 'Utah State', 'Alabama', 'Mountain West', 'SEC')]
    _, out = _rank(_processor(games).get_games_for_season(2026))
    by_conf = {c['conference_name']: c for c in out['conference_rankings']}
    assert by_conf['Pac-12']['conference_type'] == 'Group of 5'
    team = {t['team_name']: t for t in out['team_rankings']}
    assert team['Boise State']['conference_type'] == 'Group of 5'


def test_backtest_team_meta_uses_season_membership():
    games = [_game(1, 'USC', 'Texas', 'Pac-12', 'Big 12')]
    meta23 = _team_meta_from_games(_processor(games).get_games_for_season(2023))
    meta24 = _team_meta_from_games(_processor(games).get_games_for_season(2024))
    assert meta23['USC']['conference'] == 'Pac-12'
    assert meta23['Texas']['conference'] == 'Big 12'
    assert meta24['USC']['conference'] == 'Big Ten'
    assert meta24['Texas']['conference'] == 'SEC'
