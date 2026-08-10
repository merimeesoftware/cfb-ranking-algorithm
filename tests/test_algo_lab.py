"""Offline tests for the algorithm evaluation sandbox (no CFBD)."""
from __future__ import annotations

import math

import pytest

from algo_lab.backtest import aggregate_results, backtest_season
from algo_lab.baselines import baseline_always_home, baseline_coin_flip
from algo_lab.metrics import score_predictions
from algo_lab.predict import elo_home_win_prob, predict_game
from algo_lab.runner import (
    games_through_week,
    preseason_ratings,
    rank_through_week,
    ratings_from_rankings,
)
from algo_lab.sweep import expand_grid, sweep_configs


def _game(week, home, away, hs, as_, year=2024, htype='Power 4', atype='Power 4'):
    return {
        'year': year,
        'week': week,
        'home_team_name': home,
        'away_team_name': away,
        'home_score': hs,
        'away_score': as_,
        'home_conference': 'SEC' if htype == 'Power 4' else 'Sun Belt',
        'away_conference': 'SEC' if atype == 'Power 4' else 'Sun Belt',
        'home_conference_type': htype,
        'away_conference_type': atype,
        'notes': '',
        'season_type': 'regular',
    }


def synthetic_season():
    """Small closed league: Alpha dominates; Delta is weak. Predictable outcomes."""
    # Round-robin-ish over 4 weeks
    return [
        _game(1, 'Alpha', 'Delta', 35, 7),
        _game(1, 'Bravo', 'Charlie', 28, 21),
        _game(2, 'Alpha', 'Charlie', 31, 10),
        _game(2, 'Bravo', 'Delta', 24, 14),
        _game(3, 'Alpha', 'Bravo', 27, 24),
        _game(3, 'Charlie', 'Delta', 21, 17),
        _game(4, 'Alpha', 'Delta', 42, 3),
        _game(4, 'Bravo', 'Charlie', 17, 14),
    ]


class TestPredict:
    def test_elo_home_favored_when_equal(self):
        p = elo_home_win_prob(1500, 1500, hfa=65)
        assert 0.55 < p < 0.65

    def test_elo_stronger_away_can_overcome_hfa(self):
        p = elo_home_win_prob(1400, 1600, hfa=65)
        assert p < 0.5

    def test_predict_game_marks_correct(self):
        game = _game(2, 'Alpha', 'Delta', 30, 10)
        ratings = {'Alpha': 1600, 'Delta': 1200}
        pred = predict_game(game, ratings)
        assert pred is not None
        assert pred['p_home'] > 0.5
        assert pred['correct'] is True
        assert pred['home_won'] is True

    def test_predict_skips_ties(self):
        game = _game(1, 'Alpha', 'Bravo', 14, 14)
        assert predict_game(game, {'Alpha': 1500, 'Bravo': 1500}) is None


class TestMetrics:
    def test_perfect_predictions(self):
        preds = [
            {'p_home': 0.9, 'home_won': True, 'correct': True, 'underdog_won': False, 'week': 1},
            {'p_home': 0.1, 'home_won': False, 'correct': True, 'underdog_won': False, 'week': 1},
        ]
        m = score_predictions(preds)
        assert m.n_games == 2
        assert m.accuracy == 1.0
        assert m.brier < 0.05

    def test_coin_flip_brier_near_quarter(self):
        games = synthetic_season()
        m = score_predictions(baseline_coin_flip(games))
        assert abs(m.brier - 0.25) < 1e-9
        assert abs(m.log_loss - math.log(2)) < 1e-9


class TestRunner:
    def test_rank_through_week_no_leakage(self):
        games = synthetic_season()
        rankings, _ = rank_through_week(games, through_week=2)
        # Only weeks 1–2 should affect state: 4 games
        assert rankings['week'] == 2
        names = {t['team_name'] for t in rankings['team_rankings']}
        assert 'Alpha' in names
        ratings = ratings_from_rankings(rankings)
        # Alpha beat weak and mid; should outrank Delta
        assert ratings['Alpha'] > ratings['Delta']

    def test_games_through_week_filter(self):
        games = synthetic_season()
        assert len(games_through_week(games, 1)) == 2
        assert len(games_through_week(games, 3)) == 6

    def test_preseason_uses_priors(self):
        priors = {'Alpha': 1700.0, 'Delta': 1100.0}
        meta = {
            'Alpha': {'conference': 'SEC', 'conference_type': 'Power 4'},
            'Delta': {'conference': 'SEC', 'conference_type': 'Power 4'},
        }
        ratings = preseason_ratings(
            config={'prior_strength': 1.0},
            priors=priors,
            team_meta=meta,
        )
        assert ratings['Alpha'] == pytest.approx(1700.0)
        assert ratings['Delta'] == pytest.approx(1100.0)


class TestBacktest:
    def test_backtest_runs_and_beats_chaos(self):
        games = synthetic_season()
        result = backtest_season(games, 2024, include_preseason=True)
        assert result.model.n_games >= 4
        # With a clear hierarchy, model should beat coin flip on Brier
        assert result.model.brier < result.baselines['coin_flip'].brier
        assert 'always_home' in result.lifts

    def test_no_future_games_in_rating_week(self):
        """Predictions for week W must use rating_week == W-1 (or 0)."""
        games = synthetic_season()
        result = backtest_season(games, 2024)
        for pred in result.predictions:
            assert pred['rating_week'] == pred['week'] - 1 or (
                pred['week'] == 1 and pred['rating_week'] == 0
            )

    def test_aggregate_multi_season(self):
        games = synthetic_season()
        r1 = backtest_season(games, 2023)
        r2 = backtest_season(games, 2024)
        pooled = aggregate_results([r1, r2])
        assert pooled['pooled']['n_games'] == r1.model.n_games + r2.model.n_games


class TestSweep:
    def test_expand_grid(self):
        grid = expand_grid({'base_factor': [30, 40], 'hfa_elo': [65]})
        assert len(grid) == 2
        assert {'base_factor': 30, 'hfa_elo': 65} in grid

    def test_sweep_orders_by_brier(self):
        games_by_year = {2024: synthetic_season()}
        rows = sweep_configs(
            games_by_year,
            {'base_factor': [20.0, 40.0]},
        )
        assert len(rows) == 2
        assert rows[0]['score'] <= rows[1]['score']


class TestReferenceRanks:
    def test_reference_ranks_change_live_updates(self):
        """With reference_ranks, expectation uses prior-iteration strength."""
        from ranking_algorithm import TeamQualityRanker

        game = _game(1, 'Alpha', 'Delta', 35, 7)
        live = TeamQualityRanker({'use_reference_ranks': True, 'prior_strength': 0.0})
        live.update_quality_scores(game)
        live_alpha = live.team_stats['Alpha']['quality_score']

        ref = TeamQualityRanker({'use_reference_ranks': True, 'prior_strength': 0.0})
        # Pretend prior iteration already knows Alpha is elite and Delta is weak
        ref.update_quality_scores(
            game,
            reference_ranks={'Alpha': 1800.0, 'Delta': 1000.0},
        )
        ref_alpha = ref.team_stats['Alpha']['quality_score']
        # Expected win for Alpha is higher under reference ranks → smaller Elo gain
        assert ref_alpha < live_alpha

    def test_use_reference_ranks_false_ignores_refs(self):
        from ranking_algorithm import TeamQualityRanker

        game = _game(1, 'Alpha', 'Delta', 35, 7)
        a = TeamQualityRanker({'use_reference_ranks': False, 'prior_strength': 0.0})
        a.update_quality_scores(game)
        b = TeamQualityRanker({'use_reference_ranks': False, 'prior_strength': 0.0})
        b.update_quality_scores(game, reference_ranks={'Alpha': 1800.0, 'Delta': 1000.0})
        assert a.team_stats['Alpha']['quality_score'] == pytest.approx(
            b.team_stats['Alpha']['quality_score']
        )