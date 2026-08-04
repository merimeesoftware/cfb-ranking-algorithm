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
    assert result['score_gap'] == 5.0
    assert result['team_above'] == 'Oregon'
