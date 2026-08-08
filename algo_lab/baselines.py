"""Naive prediction baselines for measuring lift over chance / home-field."""
from __future__ import annotations

from typing import Any, Dict, List

from algo_lab.predict import DEFAULT_HFA, elo_home_win_prob


def baseline_coin_flip(games: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Always p_home = 0.5."""
    return _baseline_from_p(games, p_home=0.5)


def baseline_always_home(
    games: List[Dict[str, Any]],
    *,
    home_rate: float = 0.55,
) -> List[Dict[str, Any]]:
    """Constant home-win probability (empirical CFB home rate ≈ 0.55–0.60)."""
    return _baseline_from_p(games, p_home=home_rate)


def baseline_equal_elo_hfa(
    games: List[Dict[str, Any]],
    *,
    hfa: float = DEFAULT_HFA,
) -> List[Dict[str, Any]]:
    """All teams equal Elo; only HFA separates them (pure home-field baseline)."""
    p = elo_home_win_prob(1500.0, 1500.0, hfa=hfa)
    return _baseline_from_p(games, p_home=p)


def _baseline_from_p(
    games: List[Dict[str, Any]],
    *,
    p_home: float,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for game in games:
        home_score = game.get('home_score')
        away_score = game.get('away_score')
        if home_score is None or away_score is None or home_score == away_score:
            continue
        home_won = home_score > away_score
        out.append({
            'year': game.get('year'),
            'week': game.get('week'),
            'home_team': game['home_team_name'],
            'away_team': game['away_team_name'],
            'home_rating': None,
            'away_rating': None,
            'hfa': None,
            'p_home': p_home,
            'home_won': home_won,
            'correct': (p_home >= 0.5) == home_won,
            'favorite': game['home_team_name'] if p_home >= 0.5 else game['away_team_name'],
            'underdog_won': (p_home >= 0.5) != home_won,
            'margin': abs(home_score - away_score),
        })
    return out
