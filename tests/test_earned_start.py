"""History offset held all season (issue #202 C). Synthetic teams only."""
import json
from pathlib import Path

import pytest

from algo_lab.runner import rank_through_week
from public_board import evaluate_public_query
from ranking_algorithm import (
    TeamQualityRanker,
    apply_start_offset,
    earned_start_offsets,
)
from ranking_service import DEFAULT_CONFIG, build_config, publish_order


WEIGHTS = [0.70, 0.30]


def _season(scores, tiers):
    return {'scores': scores, 'tiers': tiers}


def test_tier_average_start_matches_the_tier_start():
    """Level fix: demeaned offsets do not move a tier's average start."""
    offsets = earned_start_offsets([
        _season(
            {'Alpha': 1600.0, 'Beta': 1400.0, 'Gamma': 1300.0, 'Delta': 1100.0},
            {
                'Alpha': 'Power 4', 'Beta': 'Power 4',
                'Gamma': 'Group of 5', 'Delta': 'Group of 5',
            },
        ),
    ], WEIGHTS)
    assert offsets['Alpha'] == pytest.approx(-offsets['Beta'])
    assert offsets['Gamma'] == pytest.approx(-offsets['Delta'])
    strength = DEFAULT_CONFIG['prior_offset_strength']
    cap = DEFAULT_CONFIG['prior_offset_cap']
    p4 = [
        apply_start_offset(1500.0, offsets[name], strength, cap)
        for name in ('Alpha', 'Beta')
    ]
    g5 = [
        apply_start_offset(1200.0, offsets[name], strength, cap)
        for name in ('Gamma', 'Delta')
    ]
    assert sum(p4) / 2 == pytest.approx(1500.0)
    assert sum(g5) / 2 == pytest.approx(1200.0)

    zero = TeamQualityRanker({'prior_offset_strength': 0.0})
    for name, tier, start in (
        ('Alpha', 'Power 4', 1500.0),
        ('Gamma', 'Group of 5', 1200.0),
        ('Cup', 'FCS', 900.0),
    ):
        zero._initialize_team(name, 'League', tier)
        assert zero.team_stats[name]['quality_score'] == pytest.approx(start)


def test_offset_gap_does_not_depend_on_week():
    offsets = {'Alpha': 80.0, 'Beta': 20.0}
    ranker = TeamQualityRanker(DEFAULT_CONFIG, start_offsets=offsets)
    ranker._initialize_team('Alpha', 'MAC', 'Group of 5')
    ranker._initialize_team('Beta', 'MAC', 'Group of 5')
    gap = (
        ranker.team_stats['Alpha']['quality_score']
        - ranker.team_stats['Beta']['quality_score']
    )
    strength = DEFAULT_CONFIG['prior_offset_strength']
    assert gap == pytest.approx(strength * 60.0)
    assert 'week' not in apply_start_offset.__code__.co_varnames


def test_tier_changers_use_the_source_season_tier():
    offsets = earned_start_offsets([
        _season(
            {
                'StayHi': 1700.0, 'StayLo': 1300.0, 'Down': 1400.0,
                'GHi': 1300.0, 'GLo': 1100.0, 'Up': 1400.0,
            },
            {
                'StayHi': 'Power 4', 'StayLo': 'Power 4', 'Down': 'Power 4',
                'GHi': 'Group of 5', 'GLo': 'Group of 5', 'Up': 'Group of 5',
            },
        ),
    ], WEIGHTS)
    # P4 mean is 1700/1300/1400 = 1466.666..., so pin Down against that mean.
    p4_mean = (1700.0 + 1300.0 + 1400.0) / 3.0
    g5_mean = (1300.0 + 1100.0 + 1400.0) / 3.0
    assert offsets['Down'] == pytest.approx(1400.0 - p4_mean)
    assert offsets['Up'] == pytest.approx(1400.0 - g5_mean)
    # One season present: the 0.70 weight is renormalized to 1.
    assert offsets['Up'] == pytest.approx(1400.0 - g5_mean)
    assert offsets['Up'] != pytest.approx(0.70 * (1400.0 - g5_mean))


def test_partial_history_renormalizes_and_caps_both_sides():
    offsets = earned_start_offsets([
        _season(
            {'Golf': 1300.0, 'Peer': 1100.0},
            {'Golf': 'Group of 5', 'Peer': 'Group of 5'},
        ),
        _season(
            {'Hotel': 1280.0, 'Peer2': 1120.0},
            {'Hotel': 'Group of 5', 'Peer2': 'Group of 5'},
        ),
    ], WEIGHTS)
    assert offsets['Golf'] == pytest.approx(100.0)
    assert offsets['Hotel'] == pytest.approx(80.0)
    assert 'India' not in offsets

    cap = DEFAULT_CONFIG['prior_offset_cap']
    high = apply_start_offset(1200.0, 1000.0, 0.5, cap)
    low = apply_start_offset(1200.0, -1000.0, 0.5, cap)
    assert high == pytest.approx(1200.0 + cap)
    assert low == pytest.approx(1200.0 - cap)
    fresh = apply_start_offset(1200.0, 0.0, 0.5, cap)
    assert fresh == pytest.approx(1200.0)


def test_locked_request_does_not_change_the_board():
    plain = build_config({})
    locked = build_config({
        'prior_offset_strength': 0.0,
        'mw_g5_g5': 0.2,
        'tier_override': 'Power 4',
        'start_override': 2000,
        'mw_cross': 1,
    })
    assert locked['prior_offset_strength'] == plain['prior_offset_strength']
    assert locked['mw_g5_g5'] == plain['mw_g5_g5']
    assert 'tier_override' not in locked
    assert 'start_override' not in locked

    def delta(config):
        ranker = TeamQualityRanker(config, start_offsets={'Home': 40.0, 'Away': -10.0})
        ranker.update_quality_scores({
            'home_team_name': 'Home',
            'away_team_name': 'Away',
            'home_score': 24,
            'away_score': 17,
            'home_conference': 'Sun Belt',
            'away_conference': 'MAC',
            'home_conference_type': 'Group of 5',
            'away_conference_type': 'Group of 5',
            'notes': '',
            'season_type': 'regular',
            'neutral_site': True,
        })
        return ranker.team_stats['Home']['quality_score']

    assert delta(locked) == pytest.approx(delta(plain))

    parsed, rejected = evaluate_public_query(
        'rankings',
        {
            'year': '2024',
            'week': '10',
            'prior_offset_strength': '0',
            'mw_g5_g5': '0.2',
            'tier_override': '1',
        },
        {'years': {'2024': [10]}},
    )
    assert parsed is None
    assert rejected[1] == 400
    rejected_names = set(rejected[0]['rejected'])
    assert 'prior_offset_strength' in rejected_names
    assert 'mw_g5_g5' in rejected_names
    assert 'tier_override' in rejected_names


def test_ties_break_by_team_name_and_a_week_is_deterministic():
    ordered = publish_order({
        'team_rankings': [
            {'team_name': 'Zed', 'team_quality_score': 1500.0},
            {'team_name': 'Amy', 'team_quality_score': 1500.0},
            {'team_name': 'Mia', 'team_quality_score': 1600.0},
        ],
    })['team_rankings']
    assert [team['team_name'] for team in ordered] == ['Mia', 'Amy', 'Zed']

    games = [
        {
            'year': 2024, 'week': 1,
            'home_team_name': 'Alpha', 'away_team_name': 'Beta',
            'home_score': 28, 'away_score': 14,
            'home_conference': 'SEC', 'away_conference': 'Big Ten',
            'home_conference_type': 'Power 4', 'away_conference_type': 'Power 4',
            'notes': '', 'season_type': 'regular', 'neutral_site': False,
        },
        {
            'year': 2024, 'week': 1,
            'home_team_name': 'Gamma', 'away_team_name': 'Delta',
            'home_score': 21, 'away_score': 17,
            'home_conference': 'Sun Belt', 'away_conference': 'MAC',
            'home_conference_type': 'Group of 5', 'away_conference_type': 'Group of 5',
            'notes': '', 'season_type': 'regular', 'neutral_site': False,
        },
    ]
    offsets = {'Alpha': 40.0, 'Beta': -40.0, 'Gamma': 80.0, 'Delta': -80.0}
    first, _ = rank_through_week(games, 1, start_offsets=offsets)
    second, _ = rank_through_week(games, 1, start_offsets=offsets)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    by_name = {team['team_name']: team['team_quality_score'] for team in first['team_rankings']}
    frozen = json.loads(
        (Path(__file__).resolve().parent / 'fixtures' / 'earned_start_season.json')
        .read_text(encoding='utf-8')
    )
    for name, elo in frozen['week1_elo'].items():
        assert by_name[name] == pytest.approx(elo)
