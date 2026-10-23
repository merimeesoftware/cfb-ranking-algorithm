"""Cron precompute uses one bulk games call and skips unchanged weeks."""
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import precompute_rankings as pre
from static_rankings import rebuild_rankings_manifest, write_static_rankings


class FakeClient:
    def __init__(self, games):
        self.games = games
        self.calls = []

    def get_games(self, year, week=None, season_type='regular', refresh=False):
        self.calls.append({'year': year, 'week': week, 'season_type': season_type})
        if season_type == 'both' and week is None:
            rows = []
            for week_num, items in self.games.items():
                for item in items:
                    row = dict(item)
                    row.setdefault('week', week_num)
                    row.setdefault('season_type', 'regular')
                    rows.append(row)
            return rows
        return self.games[week]


class FakeProcessor:
    def __init__(self, games):
        self.api_client = FakeClient(games)


def test_plan_skips_published_weeks_except_a_changed_latest():
    assert pre.weeks_to_fetch([1, 2, 3], {1, 2, 3}, {1, 2, 3}) == [3]
    assert pre.weeks_to_compute([1, 2, 3], {1, 2, 3}, False) == []
    assert pre.weeks_to_compute([1, 2, 3], {1, 2, 3}, True) == [3]
    assert pre.weeks_to_fetch([1, 2, 3], {1, 2}, {1, 2}) == [3]
    assert pre.weeks_to_compute([1, 2, 3], set(), True) == [1, 2, 3]


def test_repeat_run_fetches_only_the_latest_week(tmp_path, monkeypatch):
    games = {1: [{'id': 1, 'week': 1}], 2: [{'id': 2, 'week': 2}]}
    processor = FakeProcessor(games)
    computed = []

    def fake_precompute(year, week, _processor):
        computed.append(week)
        return write_static_rankings(
            {'year': year, 'week': week, 'team_rankings': [{'team_name': 'A'}]},
            year,
            week,
            root=tmp_path,
        )

    monkeypatch.setattr(pre, 'precompute', fake_precompute)
    first = pre.publish_year(2024, [1, 2], processor, static_root=tmp_path)
    assert first['bulk_calls'] == 1
    assert first['computed'] == [1, 2]
    assert processor.api_client.calls == [
        {'year': 2024, 'week': None, 'season_type': 'both'},
    ]

    processor.api_client.calls.clear()
    computed.clear()
    second = pre.publish_year(2024, [1, 2], processor, static_root=tmp_path)
    assert second['bulk_calls'] == 1
    assert second['computed'] == []
    assert computed == []
    assert processor.api_client.calls == [
        {'year': 2024, 'week': None, 'season_type': 'both'},
    ]


def test_changed_latest_week_is_the_only_recompute(tmp_path, monkeypatch):
    games = {1: [{'id': 1}], 2: [{'id': 2}]}
    processor = FakeProcessor(games)
    monkeypatch.setattr(
        pre,
        'precompute',
        lambda year, week, _processor: write_static_rankings(
            {'year': year, 'week': week, 'team_rankings': [{'team_name': 'A'}]},
            year,
            week,
            root=tmp_path,
        ),
    )
    pre.publish_year(2024, [1, 2], processor, static_root=tmp_path)
    processor.api_client.games[2] = [{'id': 2, 'score': 9}]
    processor.api_client.calls.clear()
    again = pre.publish_year(2024, [1, 2], processor, static_root=tmp_path)
    assert again['bulk_calls'] == 1
    assert again['computed'] == [2]


def test_seeded_week_makes_no_live_call():
    from api_integration import CFBDApiClient
    from cache import get_cache

    games = [{'id': 'seed', 'week': 1}]
    pre.seed_week_games(2099, 3, games)
    client = CFBDApiClient(api_key='test')
    calls = []

    def live(*_args, **_kwargs):
        calls.append(1)
        return []

    client._make_request = live
    assert client.get_games(2099, week=3) == games
    assert calls == []
    get_cache().invalidate(get_cache()._generate_key('games', 2099, 3, 'regular'))


def _completed(week):
    return {
        'id': week,
        'week': week,
        'season_type': 'regular',
        'completed': True,
        'home_score': 21,
        'away_score': 14,
        'home_team_name': 'A',
        'away_team_name': 'B',
    }


def test_latest_completed_week_skips_a_partial_week():
    games = [_completed(week) for week in range(1, 9)]
    games.append({
        'id': 9,
        'week': 9,
        'season_type': 'regular',
        'completed': False,
        'home_score': None,
        'away_score': None,
        'home_team_name': 'A',
        'away_team_name': 'B',
    })
    assert pre.latest_completed_regular_week(games) == 8


def test_offseason_current_makes_no_cfbd_call(monkeypatch):
    monkeypatch.setattr(pre, 'now_utc', lambda: datetime(2026, 3, 1))
    monkeypatch.setenv('CFBD_OFFLINE', '0')
    monkeypatch.setenv('CFBD_API_KEY', 'test-key')
    monkeypatch.setenv('CFBD_KILL', '0')
    published = []

    def explode(*_args, **_kwargs):
        raise AssertionError('off-season constructed a processor')

    monkeypatch.setattr(pre, 'CFBDataProcessor', explode)
    monkeypatch.setattr(pre, 'publish_stored_manifests', lambda: published.append('manifest'))
    assert pre.main(['--current']) == 0
    assert published == ['manifest']


def test_offline_publish_makes_no_cfbd_call(monkeypatch):
    monkeypatch.setattr(pre, 'now_utc', lambda: datetime(2026, 10, 23))
    monkeypatch.setenv('CFBD_OFFLINE', '1')
    monkeypatch.delenv('CFBD_API_KEY', raising=False)
    monkeypatch.setenv('CFBD_KILL', '0')

    def explode(*_args, **_kwargs):
        raise AssertionError('offline publish constructed a processor')

    monkeypatch.setattr(pre, 'CFBDataProcessor', explode)
    monkeypatch.setattr(pre, 'publish_stored_manifests', lambda: None)
    assert pre.main(['--current']) == 0


def test_manifest_lists_weeks_through_the_latest_completed(tmp_path, monkeypatch):
    games = [_completed(week) for week in range(1, 9)]
    processor = FakeProcessor({week: [row] for week, row in enumerate(games, start=1)})
    monkeypatch.setattr(
        pre,
        'precompute',
        lambda year, week, _processor: write_static_rankings(
            {'year': year, 'week': week, 'team_rankings': [{'team_name': 'A'}]},
            year,
            week,
            root=tmp_path,
        ),
    )
    result = pre.publish_year(
        2026,
        list(range(1, 9)),
        processor,
        static_root=tmp_path,
        season_games=games,
    )
    assert result['bulk_calls'] == 0
    assert result['computed'] == list(range(1, 9))
    manifest = rebuild_rankings_manifest(tmp_path)
    assert manifest['years']['2026'] == list(range(1, 9))


def _raw_game(week, **extra):
    row = {
        'id': extra.get('id', week),
        'completed': True,
        'week': week,
        'season': 2026,
        'homeTeam': extra.get('homeTeam', 'Home'),
        'awayTeam': extra.get('awayTeam', 'Away'),
        'homePoints': 21,
        'awayPoints': 14,
        'seasonType': extra.get('seasonType', 'regular'),
    }
    row.update(extra)
    return row


def _client(state, calls):
    from api_integration import CFBDApiClient

    client = CFBDApiClient(api_key='test')

    def live(_endpoint, params=None):
        calls.append(dict(params or {}))
        return [dict(row) for row in state['rows']]

    client._make_request = live
    return client


def test_second_sunday_refetches_current_season_and_publishes_the_new_week(tmp_path, monkeypatch):
    from cache import get_cache

    get_cache().invalidate_prefix('games')
    pre.install_batch_cache_ttl()
    state = {'rows': [_raw_game(week) for week in range(1, 9)]}
    calls = []
    client = _client(state, calls)
    written = []

    def fake_precompute(year, week, _processor):
        written.append(week)
        return write_static_rankings(
            {'year': year, 'week': week, 'team_rankings': [{'team_name': 'A'}]},
            year,
            week,
            root=tmp_path,
        )

    monkeypatch.setattr(pre, 'precompute', fake_precompute)
    processor = FakeProcessor({})
    processor.api_client = client

    first = pre.ingest_season(processor, 2026, [], refresh_games=True, static_root=tmp_path)
    assert len(calls) == 1
    assert calls[0]['seasonType'] == 'both'
    assert first['computed'] == list(range(1, 9))
    stale = client.get_games(2026, season_type='both', refresh=False)
    assert len(calls) == 1
    assert all(game.get('week') != 9 for game in stale)

    state['rows'].append(_raw_game(9))
    second = pre.ingest_season(processor, 2026, [], refresh_games=True, static_root=tmp_path)
    assert len(calls) == 2
    assert 9 in second['computed']
    assert 9 in written
    manifest = rebuild_rankings_manifest(tmp_path)
    assert 9 in manifest['years']['2026']
    get_cache().invalidate_prefix('games')


def test_postseason_update_recomputes_week_15(tmp_path, monkeypatch):
    from cache import get_cache

    get_cache().invalidate_prefix('games')
    pre.install_batch_cache_ttl()
    state = {'rows': [_raw_game(week) for week in range(1, 16)]}
    calls = []
    client = _client(state, calls)

    def fake_precompute(year, week, _processor):
        return write_static_rankings(
            {'year': year, 'week': week, 'team_rankings': [{'team_name': 'A'}]},
            year,
            week,
            root=tmp_path,
        )

    monkeypatch.setattr(pre, 'precompute', fake_precompute)
    processor = FakeProcessor({})
    processor.api_client = client
    pre.ingest_season(processor, 2026, [], refresh_games=True, static_root=tmp_path)
    assert len(calls) == 1

    state['rows'].append(_raw_game(
        1,
        id=900,
        seasonType='postseason',
        homeTeam='Bowl',
        awayTeam='Guest',
        homePoints=30,
        awayPoints=20,
    ))
    again = pre.ingest_season(processor, 2026, [], refresh_games=True, static_root=tmp_path)
    assert len(calls) == 2
    assert again['computed'] == [15]
    get_cache().invalidate_prefix('games')
