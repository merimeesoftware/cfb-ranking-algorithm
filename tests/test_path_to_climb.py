"""Unit tests for path_to_climb pure math."""
import json
from pathlib import Path

from path_to_climb import compute_path_to_climb

FIXTURES = Path(__file__).parent / 'fixtures'


def _teams():
    data = json.loads((FIXTURES / 'sample_rankings_slim.json').read_text())
    return data['team_rankings']


def test_at_top_has_no_climb():
    teams = _teams()
    result = compute_path_to_climb(teams[0], None)
    assert result['at_top'] is True
    assert result['team_above'] is None
    assert 'Oregon' in result['summary'] or '#1' in result['summary']


def test_mid_table_gap_to_team_above():
    teams = _teams()
    result = compute_path_to_climb(teams[2], teams[1])
    assert result['at_top'] is False
    assert result['team_above'] == 'Ohio State'
    assert result['score_gap'] > 0
    assert 'gaps' in result
    assert result['primary_lever']
    assert 'Ohio State' in result['summary']


def test_ohio_state_chasing_oregon():
    teams = _teams()
    result = compute_path_to_climb(teams[1], teams[0])
    assert result['score_gap'] == 50.0
    assert result['team_above'] == 'Oregon'
    assert result['primary_lever'] == 'Elo'
    assert result['summary'] == (
        'Ohio State trails Oregon by 50 points on TR+. '
        'Beating better teams closes the gap.'
    )


def test_gap_that_rounds_below_one_point_is_less_than_a_point():
    above = {
        'team_name': 'Sharp',
        'team_quality_score': 1900.4,
    }
    below = {
        'team_name': 'Soft',
        'team_quality_score': 1900.0,
    }
    result = compute_path_to_climb(below, above)
    assert result['summary'] == (
        'Soft trails Sharp by less than a point on TR+. '
        'Beating better teams closes the gap.'
    )


def test_climb_follows_elo_when_resume_gap_is_larger():
    above = {
        'team_name': 'Sharp',
        'team_quality_score': 1600.0,
        'record_score': 800.0,
        'conference_quality_score': 70.0,
    }
    below = {
        'team_name': 'Soft',
        'team_quality_score': 1590.0,
        'record_score': 4000.0,
        'conference_quality_score': 70.0,
    }
    result = compute_path_to_climb(below, above)
    assert result['primary_lever'] == 'Elo'
    assert result['score_gap'] == 10.0
    assert 'resume' not in result['primary_lever'].lower()
    assert result['summary'] == (
        'Soft trails Sharp by 10 points on TR+. '
        'Beating better teams closes the gap.'
    )
