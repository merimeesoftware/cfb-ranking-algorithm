"""Stale unscored games do not freeze the latest completed week.

Network stays stubbed. Rankings land under a tmp output root and static root.
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import precompute_rankings as pre
from cache import get_cache
from static_rankings import write_static_rankings

NOW = datetime(2026, 11, 1, 15, 0)
STALE_KICKOFF = '2026-10-18T19:00:00Z'
STALE_ID = 7007


class _Client:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def get_games(self, year, week=None, season_type='regular', refresh=False):
        self.calls.append({'year': year, 'week': week, 'season_type': season_type})
        return [dict(row) for row in self.rows]


class _Processor:
    def __init__(self, rows):
        self.api_client = _Client(rows)


def _stamp(moment):
    return moment.strftime('%Y-%m-%dT%H:%M:%SZ')


def _played(week, kickoff=None):
    if kickoff is None:
        kickoff = _stamp(datetime(2026, 8, 29) + timedelta(weeks=week - 1))
    return {
        'id': week,
        'week': week,
        'season_type': 'regular',
        'completed': True,
        'home_score': 21,
        'away_score': 14,
        'home_team_name': 'Home',
        'away_team_name': 'Away',
        'date': kickoff,
    }


def _open(week, game_id, kickoff, **extra):
    row = {
        'id': game_id,
        'week': week,
        'season_type': 'regular',
        'completed': False,
        'home_score': None,
        'away_score': None,
        'home_team_name': 'Home',
        'away_team_name': 'Away',
    }
    if kickoff is not None:
        row['date'] = kickoff
    row.update(extra)
    return row


def _install_precompute(monkeypatch):
    def fake(year, week, _processor, output_root=None, static_root=None):
        body = {'year': year, 'week': week, 'team_rankings': [{'team_name': 'A'}]}
        path = write_static_rankings(body, year, week, root=output_root)
        if static_root is not None:
            write_static_rankings(body, year, week, root=static_root)
        return path

    monkeypatch.setattr(pre, 'precompute', fake)


def _ingest(monkeypatch, rows, output, static):
    monkeypatch.setattr(pre, 'now_utc', lambda: NOW)
    _install_precompute(monkeypatch)
    return pre.ingest_season(
        _Processor(rows),
        2026,
        [],
        refresh_games=True,
        static_root=static,
        output_root=output,
    )


def _source_ids(static, week):
    path = static / '_sources' / '2026' / f'week-{week}.json'
    payload = json.loads(path.read_text(encoding='utf-8'))
    return [game['id'] for game in payload['games']]


def _seed_ids(week):
    cache = get_cache()
    key = cache._generate_key('games', 2026, week, 'regular')
    seeded = cache.get(key)
    assert seeded is not None
    return [game['id'] for game in seeded]


def test_stale_unscored_game_does_not_freeze_later_weeks(tmp_path, monkeypatch, capsys):
    """Week 7 has one never-played game from two weeks ago.

    Weeks 7-9 are otherwise complete, so the latest week is 9. Clipped to
    weeks 1-7, the same row used to stop the board at week 6.
    """
    monkeypatch.setattr(pre, 'now_utc', lambda: NOW)
    games = [_played(week) for week in range(1, 10)]
    games.append(_open(7, STALE_ID, STALE_KICKOFF))
    assert pre.latest_completed_regular_week(games) == 9
    through_week_7 = [game for game in games if game['week'] <= 7]
    assert pre.latest_completed_regular_week(through_week_7) == 7

    output = tmp_path / 'output'
    static = tmp_path / 'static'
    try:
        first = _ingest(monkeypatch, games, output, static)
        logged = capsys.readouterr().out
        assert first['computed'] == list(range(1, 10))
        assert _source_ids(static, 7) == [7]
        assert _seed_ids(7) == [7]
        assert (output / '2026' / 'week-9.json').is_file()
        assert (static / '2026' / 'week-9.json').is_file()
        assert (
            'regular week 7: rows=2 completed=1 '
            f'incomplete={STALE_ID}@{STALE_KICKOFF}'
        ) in logged
        assert (
            f'excluding stale game {STALE_ID} week 7 '
            f'kickoff {STALE_KICKOFF} from ranking inputs'
        ) in logged
        assert 'home_team_name' not in logged

        second = _ingest(monkeypatch, games, output, static)
        assert second['computed'] == []
        assert _source_ids(static, 7) == [7]
    finally:
        get_cache().invalidate_prefix('games')


def test_future_or_in_progress_week_is_not_done(tmp_path, monkeypatch, capsys):
    played = [_played(week) for week in range(1, 9)]
    future_scored = _played(9, kickoff=_stamp(NOW + timedelta(days=1)))
    future_scored['id'] = 9004
    cases = {
        'future': _open(9, 9001, _stamp(NOW + timedelta(days=2))),
        'within 36h': _open(9, 9002, _stamp(NOW - timedelta(hours=10))),
        'exactly 36h': _open(9, 9003, _stamp(NOW - timedelta(hours=36))),
        'future scored': future_scored,
    }
    try:
        for name, live in cases.items():
            capsys.readouterr()
            output = tmp_path / name / 'output'
            static = tmp_path / name / 'static'
            result = _ingest(monkeypatch, played + [live], output, static)
            logged = capsys.readouterr().out
            assert result['computed'] == list(range(1, 9)), name
            assert not (output / '2026' / 'week-9.json').exists(), name
            if pre.row_complete(live):
                assert 'regular week 9: rows=1 completed=1 incomplete=none' in logged, name
            else:
                assert f'incomplete={live["id"]}@' in logged, name
    finally:
        get_cache().invalidate_prefix('games')


def test_scored_games_publish_through_the_latest_week(tmp_path, monkeypatch, capsys):
    """All-complete weeks stay publishable, including one that just finished."""
    games = [_played(week) for week in range(1, 10)]
    games[-1]['date'] = _stamp(NOW - timedelta(hours=2))
    games.append({
        'id': 900,
        'week': 1,
        'season_type': 'postseason',
        'completed': True,
        'home_score': 30,
        'away_score': 20,
        'date': '2026-01-01T00:00:00Z',
    })
    output = tmp_path / 'output'
    static = tmp_path / 'static'
    try:
        monkeypatch.setattr(pre, 'now_utc', lambda: NOW)
        assert pre.latest_completed_regular_week(games) == 9
        first = _ingest(monkeypatch, games, output, static)
        logged = capsys.readouterr().out
        assert first['computed'] == list(range(1, 10))
        lines = [line for line in logged.splitlines() if line.startswith('regular week ')]
        assert lines == [
            f'regular week {week}: rows=1 completed=1 incomplete=none'
            for week in range(1, 10)
        ]
        assert 'excluding ' not in logged
        assert _source_ids(static, 9) == [9]
        second = _ingest(monkeypatch, games, output, static)
        assert second['computed'] == []
    finally:
        get_cache().invalidate_prefix('games')


def test_cancelled_and_postponed_rows_do_not_block(tmp_path, monkeypatch, capsys):
    games = [_played(week) for week in range(1, 4)]
    games.extend([
        _open(3, 3001, STALE_KICKOFF, notes='Canceled'),
        _open(3, 3002, _stamp(NOW + timedelta(days=14)), postponed=True),
        _open(3, 3003, STALE_KICKOFF, status='postponed'),
    ])
    output = tmp_path / 'output'
    static = tmp_path / 'static'
    try:
        result = _ingest(monkeypatch, games, output, static)
        logged = capsys.readouterr().out
        assert result['computed'] == [1, 2, 3]
        assert _source_ids(static, 3) == [3]
        assert 'excluding cancelled game 3001 week 3 ' in logged
        assert 'excluding postponed game 3002 week 3 ' in logged
        assert 'excluding postponed game 3003 week 3 ' in logged
        assert 'regular week 3: rows=4 completed=1 incomplete=' in logged
    finally:
        get_cache().invalidate_prefix('games')


def test_week_log_lists_at_most_five_incomplete_ids(tmp_path, monkeypatch, capsys):
    games = [_open(1, game_id, None) for game_id in range(1, 7)]
    output = tmp_path / 'output'
    static = tmp_path / 'static'
    try:
        result = _ingest(monkeypatch, games, output, static)
        logged = capsys.readouterr().out
        assert result['computed'] == []
        assert 'No completed week for 2026.' in logged
        assert (
            'regular week 1: rows=6 completed=0 '
            'incomplete=1@none,2@none,3@none,4@none,5@none'
        ) in logged
        assert '6@none' not in logged
        assert not output.exists() or not any(output.rglob('*.json'))
    finally:
        get_cache().invalidate_prefix('games')
