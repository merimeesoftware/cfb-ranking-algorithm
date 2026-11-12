"""Tests for ranking_service optimizations (priors keying, year count, slim payload)."""
import os
from unittest.mock import MagicMock, patch, call

import pytest

os.environ.setdefault('CFBD_API_KEY', 'test-key-for-unit-tests')


def test_v54_rankings_cache_is_not_read_under_v55():
    import json
    from ranking_service import ALGO_VERSION, get_or_calculate_rankings, rankings_cache_key

    assert ALGO_VERSION == 'v5.5'
    old_board = {
        'algo': 'v5.4',
        'year': 2024,
        'week': 9,
        'team_rankings': [{'team_name': 'Old', 'team_quality_score': 1.0}],
    }
    store = {}
    seen = []

    class _Cache:
        def _generate_key(self, prefix, **kwargs):
            return prefix + '|' + json.dumps(kwargs, sort_keys=True, default=str)

        def get(self, key):
            seen.append(key)
            return store.get(key)

        def set(self, key, data, ttl, prefix=None):
            store[key] = data

    cache = _Cache()
    with patch('ranking_service.get_cache', return_value=cache):
        with patch('ranking_service.ALGO_VERSION', 'v5.4'):
            old_key = rankings_cache_key(2024, 9, {})
        store[old_key] = old_board
        with patch('ranking_service.calculate_rankings_logic', return_value=None):
            out = get_or_calculate_rankings(
                object(), 2024, 9, {}, prefer_static=False, allow_compute=True,
            )
        new_key = rankings_cache_key(2024, 9, {})
    assert new_key != old_key
    assert old_key not in seen
    assert out is None


def test_priors_cache_key_ignores_prior_strength():
    from ranking_service import priors_cache_key, DEFAULT_CONFIG

    config_a = DEFAULT_CONFIG.copy()
    config_a['prior_strength'] = 0.7
    config_b = DEFAULT_CONFIG.copy()
    config_b['prior_strength'] = 0.0

    assert priors_cache_key(2024, config_a) == priors_cache_key(2024, config_b)


def test_priors_cache_key_changes_with_algo_weights():
    from ranking_service import priors_cache_key, DEFAULT_CONFIG

    config_a = DEFAULT_CONFIG.copy()
    config_b = DEFAULT_CONFIG.copy()
    config_b['team_quality_weight'] = 0.5

    assert priors_cache_key(2024, config_a) != priors_cache_key(2024, config_b)


def test_compute_priors_only_fetches_two_prior_years():
    from ranking_service import compute_priors, DEFAULT_CONFIG

    mock_dp = MagicMock()
    mock_dp.get_games_for_season.return_value = []

    with patch('ranking_service.get_cache') as mock_cache:
        cache = MagicMock()
        cache.get.return_value = None
        mock_cache.return_value = cache

        compute_priors(mock_dp, 2024, DEFAULT_CONFIG.copy())

        years = [c.kwargs.get('year') or c.args[0] for c in mock_dp.get_games_for_season.call_args_list]
        # Only Y-1 and Y-2 (2023, 2022) — not Y-3 (2021)
        assert set(years) == {2023, 2022}


def test_compute_priors_reads_published_scores_without_cfbd():
    from ranking_service import compute_priors, DEFAULT_CONFIG

    mock_dp = MagicMock()
    mock_dp.get_games_for_season.side_effect = AssertionError('priors should serve scores')

    def _priors(year, algo=None, membership=None, root=None):
        return {'Georgia': 1800.0}

    with patch('ranking_service.get_cache') as mock_cache:
        cache = MagicMock()
        cache.get.return_value = None
        mock_cache.return_value = cache
        with patch('static_rankings.read_prior_teams', side_effect=_priors):
            compute_priors(mock_dp, 2024, DEFAULT_CONFIG.copy())
    mock_dp.get_games_for_season.assert_not_called()


def test_stale_snapshot_under_the_current_cache_key_is_not_served():
    """A payload planted on the v5.5 key with a different algo is not served.

    Removing the published_snapshot() wrap makes this return the planted board.
    """
    import json
    from ranking_service import ALGO_VERSION, get_or_calculate_rankings, rankings_cache_key

    stale = {
        'algo': 'v5.3',
        'year': 2024,
        'week': 9,
        'team_rankings': [{'team_name': 'Stale', 'team_quality_score': 1.0}],
    }
    fresh = {
        'algo': ALGO_VERSION,
        'year': 2024,
        'week': 9,
        'team_rankings': [{'team_name': 'Fresh', 'team_quality_score': 2.0}],
    }
    store = {}
    calculated = []

    class _Cache:
        def _generate_key(self, prefix, **kwargs):
            return prefix + '|' + json.dumps(kwargs, sort_keys=True, default=str)

        def get(self, key):
            return store.get(key)

        def set(self, key, data, ttl, prefix=None):
            store[key] = data

    cache = _Cache()
    with patch('ranking_service.get_cache', return_value=cache):
        key = rankings_cache_key(2024, 9, {})
        store[key] = stale

        def _calculate(*_args, **_kwargs):
            calculated.append(1)
            return fresh

        with patch('ranking_service.calculate_rankings_logic', side_effect=_calculate):
            out = get_or_calculate_rankings(
                object(), 2024, 9, {}, prefer_static=False, allow_compute=True,
            )
    assert calculated == [1]
    assert out['team_rankings'][0]['team_name'] == 'Fresh'
    assert out['algo'] == ALGO_VERSION
    assert out is not stale


def test_slim_rankings_for_list_strips_heavy_fields():
    from ranking_service import slim_rankings_for_list

    full = {
        'year': 2024,
        'week': 10,
        'team_rankings': [
            {
                'team_name': 'Georgia',
                'final_ranking_score': 100,
                'wins_details': [{'opponent': 'X'}],
                'losses_details': [{'opponent': 'Y'}],
                'records': {'total_wins': 10, 'total_losses': 1},
            }
        ],
        'conference_rankings': [{'conference_name': 'SEC'}],
        'rankings': {'Georgia': {'team_name': 'Georgia', 'wins_details': []}},
    }
    slim = slim_rankings_for_list(full)
    assert 'rankings' not in slim
    assert slim['team_rankings'][0]['team_name'] == 'Georgia'
    assert 'wins_details' not in slim['team_rankings'][0]
    assert 'losses_details' not in slim['team_rankings'][0]
    assert full['team_rankings'][0]['wins_details']  # original untouched
    assert slim['detail'] is False
    assert 'algo' not in slim


def test_slim_rankings_for_list_keeps_the_boards_own_algo():
    from ranking_service import ALGO_VERSION, slim_rankings_for_list

    stored = {
        'year': 2024,
        'week': 10,
        'algo': 'v5.3',
        'team_rankings': [{'team_name': 'Georgia', 'team_quality_score': 1.0}],
        'conference_rankings': [],
    }
    slim = slim_rankings_for_list(stored)
    assert slim['detail'] is False
    assert slim['algo'] == 'v5.3'
    assert stored['algo'] == 'v5.3'

    fresh = dict(stored)
    fresh['algo'] = ALGO_VERSION
    assert slim_rankings_for_list(fresh)['algo'] == ALGO_VERSION


def test_is_archived_week():
    from ranking_service import is_archived_week
    from datetime import datetime

    # Past season always archived
    assert is_archived_week(2020, 5, now=datetime(2025, 10, 1)) is True
    # Current season, week before current is archived
    assert is_archived_week(2025, 2, now=datetime(2025, 10, 1), current_week=6) is True
    # Current week is live
    assert is_archived_week(2025, 6, now=datetime(2025, 10, 1), current_week=6) is False
