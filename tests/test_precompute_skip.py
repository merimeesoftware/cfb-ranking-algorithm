"""Cron precompute skips published weeks and refetches only a changed week."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import precompute_rankings as pre
from static_rankings import write_static_rankings


class FakeClient:
    def __init__(self, games):
        self.games = games
        self.calls = []

    def get_games(self, year, week=None, season_type='regular'):
        self.calls.append(week)
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
    assert first['fetched'] == [1, 2]
    assert first['computed'] == [1, 2]

    processor.api_client.calls.clear()
    computed.clear()
    second = pre.publish_year(2024, [1, 2], processor, static_root=tmp_path)
    assert second['fetched'] == [2]
    assert second['computed'] == []
    assert computed == []
    assert processor.api_client.calls == [2]


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
    assert again['fetched'] == [2]
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
