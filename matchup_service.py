"""Head-to-head of published TR+ ratings. No spread, market line, or pick."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


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
) -> Optional[Dict[str, Any]]:
    idx_a, a = find_team(team_rankings, team_a)
    idx_b, b = find_team(team_rankings, team_b)
    if a is None or b is None or idx_a is None or idx_b is None:
        return None

    def side(team: Dict[str, Any], rank: int) -> Dict[str, Any]:
        records = team.get("records") or {}
        wins = records.get("total_wins", 0)
        losses = records.get("total_losses", 0)
        return {
            "name": team["team_name"],
            "rank": rank,
            "tr_plus": float(team["final_ranking_score"]),
            "record": f"{wins}-{losses}",
        }

    return {
        "year": year,
        "week": week,
        "team_a": side(a, idx_a + 1),
        "team_b": side(b, idx_b + 1),
    }
