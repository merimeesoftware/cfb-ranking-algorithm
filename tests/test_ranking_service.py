"""Tests for ranking_service optimizations (priors keying, year count, slim payload)."""
import os
from unittest.mock import MagicMock, patch, call

import pytest

os.environ.setdefault('CFBD_API_KEY', 'test-key-for-unit-tests')


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


def test_is_archived_week():
    from ranking_service import is_archived_week
    from datetime import datetime

    # Past season always archived
    assert is_archived_week(2020, 5, now=datetime(2025, 10, 1)) is True
    # Current season, week before current is archived
    assert is_archived_week(2025, 2, now=datetime(2025, 10, 1), current_week=6) is True
    # Current week is live
    assert is_archived_week(2025, 6, now=datetime(2025, 10, 1), current_week=6) is False
