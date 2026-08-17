"""TR+ matchup helpers — implied spread from ranking differential."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# ~25 TR+ (FRS) points ≈ 1 point of spread on Elo-scale scores.
TR_PLUS_PER_POINT = 25.0


def implied_spread(favorite_tr: float, underdog_tr: float) -> float:
    raw = (favorite_tr - underdog_tr) / TR_PLUS_PER_POINT
    return round(raw * 2) / 2.0


def find_team(team_rankings: List[Dict[str, Any]], name: str) -> Tuple[Optional[int], Optional[Dict[str, Any]]]:
    needle = name.lower().strip()
    for i, team in enumerate(team_rankings):
        if team.get("team_name", "").lower() == needle:
            return i, team
    return None, None


def build_matchup_payload(
    team_rankings: List[Dict[str, Any]],
    team_a: str,
    team_b: str,
    year: int,
    week: Optional[int],
    market_spread: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    idx_a, a = find_team(team_rankings, team_a)
    idx_b, b = find_team(team_rankings, team_b)
    if a is None or b is None or idx_a is None or idx_b is None:
        return None

    a_score = float(a["final_ranking_score"])
    b_score = float(b["final_ranking_score"])
    a_fav = a_score >= b_score
    favorite = a if a_fav else b
    underdog = b if a_fav else a
    spread = implied_spread(float(favorite["final_ranking_score"]), float(underdog["final_ranking_score"]))
    delta = None if market_spread is None else spread - abs(float(market_spread))

    return {
        "year": year,
        "week": week,
        "team_a": {
            "name": a["team_name"],
            "rank": idx_a + 1,
            "tr_plus": a_score,
            "record": f"{a['records']['total_wins']}-{a['records']['total_losses']}",
        },
        "team_b": {
            "name": b["team_name"],
            "rank": idx_b + 1,
            "tr_plus": b_score,
            "record": f"{b['records']['total_wins']}-{b['records']['total_losses']}",
        },
        "favorite": favorite["team_name"],
        "implied_spread": spread,
        "market_spread": market_spread,
        "delta": delta,
        "note": "Rankings stay free. Sell disagreement with the market, not the list.",
    }
