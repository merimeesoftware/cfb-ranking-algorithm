"""Head-to-head of published TR+ ratings.

The signed gap is team_a's TR+ minus team_b's TR+. Results come from a
games sidecar when one was passed in. A missing sidecar stays an empty
results list. This module does not call CFBD and does not publish a win
chance, pick, spread, or expected winner.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ranking_algorithm import ordering_score


def find_team(team_rankings: List[Dict[str, Any]], name: str) -> Tuple[Optional[int], Optional[Dict[str, Any]]]:
    needle = name.lower().strip()
    for i, team in enumerate(team_rankings):
        if team.get("team_name", "").lower() == needle:
            return i, team
    return None, None


def _same_team(left: str, right: str) -> bool:
    """Full-string match. Miami and Miami (OH) are not the same team."""
    if left == right:
        return True
    return left.lower() == right.lower()


def _number(team: Dict[str, Any], key: str) -> Optional[float]:
    value = team.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _count(team: Dict[str, Any], key: str) -> Optional[int]:
    value = team.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _side(team: Dict[str, Any], rank: int) -> Dict[str, Any]:
    records = team.get("records") or {}
    wins = records.get("total_wins", 0)
    losses = records.get("total_losses", 0)
    conference = team.get("conference")
    return {
        "name": team["team_name"],
        "rank": rank,
        "tr_plus": ordering_score(team),
        "rating_label": "TR+",
        "record": f"{wins}-{losses}",
        "conference": conference if isinstance(conference, str) else None,
        "sos": _number(team, "sos"),
        "sos_rank": _count(team, "sos_rank"),
        "sov": _number(team, "sov"),
        "quality_wins": _count(team, "quality_wins"),
        "quality_losses": _count(team, "quality_losses"),
        "bad_losses": _count(team, "bad_losses"),
    }


def _board_index(team_rankings: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for team in team_rankings:
        name = team.get("team_name")
        if isinstance(name, str) and name not in index:
            index[name] = team
    return index


def _opponent_on_board(
    name: str,
    index: Dict[str, Dict[str, Any]],
) -> Tuple[bool, Optional[float]]:
    team = index.get(name)
    if team is None:
        for board_name, row in index.items():
            if _same_team(board_name, name):
                team = row
                break
    if team is None:
        return False, None
    return True, ordering_score(team)


def _result_row(game: Dict[str, Any], team: str) -> Optional[Dict[str, Any]]:
    home = game.get("home")
    away = game.get("away")
    if not isinstance(home, str) or not isinstance(away, str):
        return None
    if _same_team(home, team):
        opponent = away
        team_score = game.get("home_score")
        opp_score = game.get("away_score")
    elif _same_team(away, team):
        opponent = home
        team_score = game.get("away_score")
        opp_score = game.get("home_score")
    else:
        return None
    if isinstance(team_score, bool) or isinstance(opp_score, bool):
        return None
    if not isinstance(team_score, (int, float)) or not isinstance(opp_score, (int, float)):
        return None
    if team_score > opp_score:
        outcome = "win"
    elif team_score < opp_score:
        outcome = "loss"
    else:
        outcome = "tie"
    return {
        "opponent": opponent,
        "week": game.get("week"),
        "outcome": outcome,
        "margin": abs(int(team_score) - int(opp_score)),
    }


def _direct_game(game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    home_score = game.get("home_score")
    away_score = game.get("away_score")
    if isinstance(home_score, bool) or isinstance(away_score, bool):
        return None
    if not isinstance(home_score, (int, float)) or not isinstance(away_score, (int, float)):
        return None
    home_score = int(home_score)
    away_score = int(away_score)
    if home_score > away_score:
        winner = game["home"]
    elif away_score > home_score:
        winner = game["away"]
    else:
        winner = None
    return {
        "week": game.get("week"),
        "home": game["home"],
        "away": game["away"],
        "home_score": home_score,
        "away_score": away_score,
        "neutral_site": bool(game.get("neutral_site")),
        "season_type": game.get("season_type") or "regular",
        "winner": winner,
        "margin": abs(home_score - away_score),
    }


def _played(game: Dict[str, Any], team_a: str, team_b: str) -> bool:
    home = game.get("home")
    away = game.get("away")
    if not isinstance(home, str) or not isinstance(away, str):
        return False
    return (
        (_same_team(home, team_a) and _same_team(away, team_b))
        or (_same_team(home, team_b) and _same_team(away, team_a))
    )


def compare_results(
    team_rankings: List[Dict[str, Any]],
    team_a: str,
    team_b: str,
    games: Optional[List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Direct games and common opponents. ``games is None`` means no sidecar."""
    if not games:
        return {"direct_games": [], "common_opponents": []}

    index = _board_index(team_rankings)
    direct = []
    for game in games:
        if not isinstance(game, dict) or not _played(game, team_a, team_b):
            continue
        row = _direct_game(game)
        if row is not None:
            direct.append(row)
    direct.sort(key=lambda row: (row["week"] is None, row["week"] or 0, row["home"], row["away"]))

    appearances: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for game in games:
        if not isinstance(game, dict) or _played(game, team_a, team_b):
            continue
        for team in (team_a, team_b):
            result = _result_row(game, team)
            if result is None:
                continue
            opponent = result.pop("opponent")
            bucket = appearances.setdefault(opponent, {"team_a_results": [], "team_b_results": []})
            key = "team_a_results" if _same_team(team, team_a) else "team_b_results"
            bucket[key].append(result)

    common = []
    for name in sorted(appearances, key=str.lower):
        sides = appearances[name]
        if not sides["team_a_results"] or not sides["team_b_results"]:
            continue
        on_board, tr_plus = _opponent_on_board(name, index)
        common.append({
            "name": name,
            "off_board": not on_board,
            "opponent_tr_plus": tr_plus,
            "team_a_results": sides["team_a_results"],
            "team_b_results": sides["team_b_results"],
        })
    return {"direct_games": direct, "common_opponents": common}


def build_matchup_payload(
    team_rankings: List[Dict[str, Any]],
    team_a: str,
    team_b: str,
    year: int,
    week: Optional[int],
    games: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    idx_a, a = find_team(team_rankings, team_a)
    idx_b, b = find_team(team_rankings, team_b)
    if a is None or b is None or idx_a is None or idx_b is None:
        return None

    side_a = _side(a, idx_a + 1)
    side_b = _side(b, idx_b + 1)
    results = compare_results(team_rankings, side_a["name"], side_b["name"], games)
    return {
        "year": year,
        "week": week,
        "team_a": side_a,
        "team_b": side_b,
        "tr_plus_gap": side_a["tr_plus"] - side_b["tr_plus"],
        "direct_games": results["direct_games"],
        "common_opponents": results["common_opponents"],
    }
