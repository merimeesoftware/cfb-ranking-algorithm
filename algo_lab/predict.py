"""Convert team ratings into next-game win probabilities.

Uses the same logistic Elo scale (400) and HFA conventions as TeamQualityRanker,
so predictions stay calibrated to the rating model we actually run.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Optional


ELO_SCALE = 400.0
DEFAULT_HFA = 65.0
DEFAULT_HFA_POSTSEASON = 20.0


def elo_home_win_prob(
    home_rating: float,
    away_rating: float,
    *,
    hfa: float = DEFAULT_HFA,
    scale: float = ELO_SCALE,
) -> float:
    """P(home wins) under logistic Elo with home-field advantage on expectation only."""
    home_eff = home_rating + hfa
    exponent = (away_rating - home_eff) / scale
    return 1.0 / (1.0 + math.pow(10.0, exponent))


def game_hfa(
    game: Dict[str, Any],
    *,
    hfa_regular: float = DEFAULT_HFA,
    hfa_postseason: float = DEFAULT_HFA_POSTSEASON,
) -> float:
    """Match TeamQualityRanker HFA rules (neutral / postseason / regular)."""
    notes = str(game.get('notes', '')).lower()
    season_type = str(game.get('season_type', 'regular')).lower()
    is_neutral = 'neutral' in notes or 'kickoff' in notes
    is_postseason = (
        season_type == 'postseason'
        or 'bowl' in notes
        or 'playoff' in notes
        or 'championship' in notes
    )
    if is_neutral:
        return 0.0
    if is_postseason:
        return hfa_postseason
    return hfa_regular


def predict_game(
    game: Dict[str, Any],
    ratings: Dict[str, float],
    *,
    rating_key_default: float = 1200.0,
    hfa_regular: float = DEFAULT_HFA,
    hfa_postseason: float = DEFAULT_HFA_POSTSEASON,
    scale: float = ELO_SCALE,
) -> Optional[Dict[str, Any]]:
    """Build one prediction record for a completed game given pre-game ratings.

    Returns None for ties or missing scores (not scored).
    """
    home = game['home_team_name']
    away = game['away_team_name']
    home_score = game.get('home_score')
    away_score = game.get('away_score')
    if home_score is None or away_score is None:
        return None
    if home_score == away_score:
        return None

    home_r = ratings.get(home, rating_key_default)
    away_r = ratings.get(away, rating_key_default)
    hfa = game_hfa(game, hfa_regular=hfa_regular, hfa_postseason=hfa_postseason)
    p_home = elo_home_win_prob(home_r, away_r, hfa=hfa, scale=scale)
    home_won = home_score > away_score

    return {
        'year': game.get('year'),
        'week': game.get('week'),
        'home_team': home,
        'away_team': away,
        'home_rating': home_r,
        'away_rating': away_r,
        'hfa': hfa,
        'p_home': p_home,
        'home_won': home_won,
        'correct': (p_home >= 0.5) == home_won,
        'favorite': home if p_home >= 0.5 else away,
        'underdog_won': (p_home >= 0.5) != home_won,
        'margin': abs(home_score - away_score),
    }
