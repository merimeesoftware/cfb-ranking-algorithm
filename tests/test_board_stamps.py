"""The board-stamp build check fails on a planted stale week."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

from ranking_service import ALGO_VERSION
import check_board_stamps as stamps

FIXTURE = ROOT / 'tests' / 'fixtures' / 'board-stamps' / 'stale'
CI = ROOT / '.github' / 'workflows' / 'ci.yml'


def test_planted_stale_board_trips():
    errors = stamps.board_stamp_errors(FIXTURE)
    assert len(errors) == 1
    assert 'v5.3' in errors[0]
    assert ALGO_VERSION in errors[0]
    assert stamps.main([str(FIXTURE)]) == 1


def test_matching_stamp_passes(tmp_path):
    week = tmp_path / '2024'
    week.mkdir()
    payload = {
        'year': 2024,
        'week': 1,
        'algo': ALGO_VERSION,
        'detail': False,
        'team_rankings': [{'team_name': 'A'}],
    }
    (week / 'week-1.json').write_text(json.dumps(payload), encoding='utf-8')
    (week / 'week-1.story.json').write_text('{"algo": "v5.3"}', encoding='utf-8')
    assert stamps.board_stamp_errors(tmp_path) == []
    assert stamps.main([str(tmp_path)]) == 0


def test_ci_runs_the_board_stamp_check():
    text = CI.read_text(encoding='utf-8')
    assert 'scripts/check_board_stamps.py' in text
