"""G5-G5 games move the same Elo as an otherwise identical P4-P4 game.

Power 4 vs Group of 5 stays 0.8. A request cannot set the weight.
"""
import pytest

from ranking_algorithm import TeamQualityRanker
from ranking_service import DEFAULT_CONFIG, build_config
from public_board import evaluate_public_query


def _game(home, away, home_type, away_type):
    return {
        'home_team_name': home,
        'away_team_name': away,
        'home_score': 31,
        'away_score': 10,
        'home_conference': 'SEC' if home_type == 'Power 4' else 'Sun Belt',
        'away_conference': 'Big Ten' if away_type == 'Power 4' else 'MAC',
        'home_conference_type': home_type,
        'away_conference_type': away_type,
        'notes': '',
        'season_type': 'regular',
        'neutral_site': True,
    }


def _winner_delta(home_type, away_type):
    config = DEFAULT_CONFIG.copy()
    config['power_conf_initial'] = 1500.0
    config['group5_initial'] = 1500.0
    config['fcs_initial'] = 1500.0
    config['prior_strength'] = 0.0
    ranker = TeamQualityRanker(config)
    ranker.update_quality_scores(_game('Home', 'Away', home_type, away_type))
    return ranker.team_stats['Home']['quality_score'] - 1500.0


def test_g5_g5_delta_matches_p4_p4():
    assert DEFAULT_CONFIG['mw_g5_g5'] == 1.0
    assert DEFAULT_CONFIG['mw_p4_g5'] == 0.8
    p4 = _winner_delta('Power 4', 'Power 4')
    g5 = _winner_delta('Group of 5', 'Group of 5')
    cross = _winner_delta('Power 4', 'Group of 5')
    assert g5 == pytest.approx(p4)
    assert cross == pytest.approx(p4 * DEFAULT_CONFIG['mw_p4_g5'])


def test_request_cannot_set_g5_weight():
    config = build_config({'mw_g5_g5': 0.2, 'mw_p4_g5': 1.0})
    assert config['mw_g5_g5'] == DEFAULT_CONFIG['mw_g5_g5']
    assert config['mw_p4_g5'] == DEFAULT_CONFIG['mw_p4_g5']
    parsed, rejected = evaluate_public_query(
        'rankings',
        {'year': '2024', 'week': '10', 'mw_g5_g5': '0.2'},
        {'years': {'2024': [10]}},
    )
    assert parsed is None
    assert rejected[1] == 400
    assert 'mw_g5_g5' in rejected[0]['rejected']
