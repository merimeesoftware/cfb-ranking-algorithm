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


# --- Fix 1 (Archie #149 review): independents are G5 except Notre Dame ---

@pytest.mark.parametrize('team,season,tier', [
    ('Massachusetts', 2024, 'Group of 5'),
    ('Army', 2023, 'Group of 5'),
    ('Liberty', 2022, 'Group of 5'),
    ('BYU', 2022, 'Group of 5'),
    ('New Mexico State', 2022, 'Group of 5'),
    ('Notre Dame', 2021, 'Power 4'),
    ('Notre Dame', 2026, 'Power 4'),
    ('Notre Dame', 2020, 'Power 4'),  # ACC that season
    ('UConn', 2026, 'Group of 5'),
])
def test_independent_tiers_notre_dame_only_p4(team, season, tier):
    m = load_membership()
    assert m.conference_for(team, season) in ('FBS Independents', 'ACC')
    assert m.tier_for(m.conference_for(team, season), season, team=team) == tier


def test_independents_conference_tier_is_g5_without_team():
    m = load_membership()
    for season in range(2017, 2027):
        assert m.tier_for('FBS Independents', season) == 'Group of 5'


def test_processor_applies_team_tier_override():
    games = [_game(1, 'Notre Dame', 'Massachusetts', 'FBS Independents', 'FBS Independents'),
             _game(2, 'Army', 'UConn', 'FBS Independents', 'FBS Independents')]
    c = _confs(_processor(games).get_games_for_season(2023))
    assert c['Notre Dame'] == ('FBS Independents', 'Power 4')
    assert c['Massachusetts'] == ('FBS Independents', 'Group of 5')
    assert c['Army'] == ('FBS Independents', 'Group of 5')
    assert c['UConn'] == ('FBS Independents', 'Group of 5')


@pytest.mark.parametrize('order', [0, 1])
def test_mixed_tier_conference_row_does_not_depend_on_team_order(order):
    games = [_game(1, 'Notre Dame', 'Alabama', 'FBS Independents', 'SEC'),
             _game(2, 'Massachusetts', 'Kansas', 'FBS Independents', 'Big 12')]
    if order:
        games.reverse()
    _, out = _rank(_processor(games).get_games_for_season(2023))
    by_conf = {c['conference_name']: c for c in out['conference_rankings']}
    assert by_conf['FBS Independents']['conference_type'] == 'Mixed'
    team = {t['team_name']: t for t in out['team_rankings']}
    assert team['Notre Dame']['conference_type'] == 'Power 4'
    assert team['Massachusetts']['conference_type'] == 'Group of 5'


def test_team_tier_override_must_be_fbs_that_season():
    payload = json.loads(MAP_PATH.read_text(encoding='utf-8'))
    bad = copy.deepcopy(payload)
    bad['team_tiers']['Liberty'] = [{'first': 2017, 'last': 2018, 'tier': 'Power 4'}]
    with pytest.raises(MembershipError, match='not FBS'):
        ConferenceMembership(bad)


# --- loader shape (Archie N1) ---------------------------------------------

def _mutated(fn):
    payload = copy.deepcopy(json.loads(MAP_PATH.read_text(encoding='utf-8')))
    fn(payload)
    return payload


@pytest.mark.parametrize('name,fn', [
    ('not-object', None),
    ('no-version', lambda p: p.pop('version')),
    ('coverage-type', lambda p: p.__setitem__('coverage', [2017, 2026])),
    ('no-base', lambda p: p.pop('base')),
    ('base-team-not-str', lambda p: p['base']['conferences']['SEC'].append(7)),
    ('from-equals-to', lambda p: p['moves'][0].__setitem__('from', p['moves'][0]['to'])),
    ('duplicate-move', lambda p: p['moves'].append(dict(p['moves'][0]))),
    ('move-after-coverage', lambda p: p['moves'].append(
        {'team': 'X', 'season': 2027, 'from': None, 'to': 'SEC', 'source': 'https://x'})),
    ('overlapping-spans', lambda p: p['tiers']['SEC'].append(
        {'first': 2020, 'last': 2021, 'tier': 'Group of 5'})),
    ('span-outside-coverage', lambda p: p['tiers']['SEC'].__setitem__(
        0, {'first': 2016, 'last': 2026, 'tier': 'Power 4'})),
    ('bad-tier-name', lambda p: p['tiers']['SEC'].__setitem__(
        0, {'first': 2017, 'last': 2026, 'tier': 'Power 5'})),
    ('tiers-type', lambda p: p.__setitem__('tiers', [])),
    ('team-tiers-type', lambda p: p.__setitem__('team_tiers', [])),
])
def test_malformed_map_raises_membership_error(name, fn):
    payload = 'nope' if fn is None else _mutated(fn)
    with pytest.raises(MembershipError):
        ConferenceMembership(payload)
