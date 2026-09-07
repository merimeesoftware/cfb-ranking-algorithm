"""Betting layer on V5.3 team-quality Elo.

FRS stays the public board. This module prices a home spread and classifies
GREEN / LEAN / PASS. Momentum is a veto (line steam), not an Elo input.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Optional

from algo_lab.predict import game_hfa

ELO_PER_POINT = 25.0
HFA_REGULAR = 50.0
HFA_POSTSEASON = 20.0
GREEN_EDGE = 3.0
LEAN_EDGE = 1.5
MIN_WEEK = 3
MAX_ABS_MARKET = 28.0
STEAM_VETO = 1.5


def model_home_spread(
    home_elo: float,
    away_elo: float,
    *,
    hfa: float = HFA_REGULAR,
    elo_per_point: float = ELO_PER_POINT,
) -> float:
    """Home spread implied by Elo. Negative = home favored."""
    raw = (away_elo - home_elo - hfa) / elo_per_point
    return round(raw * 2.0) / 2.0


def edge_home(model_spread: float, market_spread: float) -> float:
    """model - market on the home number. Negative → model likes home."""
    return round((model_spread - market_spread) * 2.0) / 2.0


def pick_from_edge(edge: float, threshold: float = LEAN_EDGE) -> Optional[str]:
    if edge <= -threshold:
        return 'home'
    if edge >= threshold:
        return 'away'
    return None


def steam_against_pick(
    pick: Optional[str],
    open_spread: Optional[float],
    close_spread: Optional[float],
) -> Optional[float]:
    """Points the close moved against the pick. Positive = fight."""
    if pick is None or open_spread is None or close_spread is None:
        return None
    move_home = close_spread - open_spread  # more negative = toward home
    if pick == 'home':
        return move_home  # positive means close made home less favored
    return -move_home


def classify(
    *,
    edge: Optional[float],
    week: Optional[int],
    market_spread: Optional[float],
    opponent_tier: Optional[str] = None,
    steam_against: Optional[float] = None,
    season_type: Optional[str] = None,
    green_edge: float = GREEN_EDGE,
    lean_edge: float = LEAN_EDGE,
    min_week: int = MIN_WEEK,
    max_abs_market: float = MAX_ABS_MARKET,
    steam_veto: float = STEAM_VETO,
) -> Dict[str, Any]:
    vetoes: List[str] = []
    if market_spread is None or edge is None:
        vetoes.append('no_line')
    is_postseason = str(season_type or 'regular').lower() == 'postseason'
    if week is not None and week < min_week and not is_postseason:
        vetoes.append('early_week')
    if opponent_tier == 'FCS':
        vetoes.append('fcs')
    if market_spread is not None and abs(market_spread) > max_abs_market:
        vetoes.append('landmine')
    if steam_against is not None and steam_against >= steam_veto:
        vetoes.append('steam_against')

    if vetoes:
        return {'signal': 'PASS', 'vetoes': vetoes}

    abs_edge = abs(edge)  # type: ignore[arg-type]
    if abs_edge >= green_edge:
        return {'signal': 'GREEN', 'vetoes': []}
    if abs_edge >= lean_edge:
        return {'signal': 'LEAN', 'vetoes': []}
    return {'signal': 'PASS', 'vetoes': ['thin_edge']}


def home_covers(home_score: int, away_score: int, market_spread_home: float) -> str:
    """ATS result from the home side of the close. cover / push / fail."""
    margin = (home_score + market_spread_home) - away_score
    if margin > 0:
        return 'cover'
    if margin < 0:
        return 'fail'
    return 'push'


def pick_hit(pick: str, ats_home: str) -> Optional[bool]:
    if ats_home == 'push':
        return None
    if pick == 'home':
        return ats_home == 'cover'
    return ats_home == 'fail'


def price_game(
    game: Dict[str, Any],
    ratings: Dict[str, float],
    *,
    rating_default: float = 1200.0,
    elo_per_point: float = ELO_PER_POINT,
    hfa_regular: float = HFA_REGULAR,
    hfa_postseason: float = HFA_POSTSEASON,
) -> Optional[Dict[str, Any]]:
    home = game['home_team_name']
    away = game['away_team_name']
    market = game.get('market_spread_home')
    if market is None:
        market = game.get('spread_home')
    if market is None:
        return None

    home_elo = float(ratings.get(home, rating_default))
    away_elo = float(ratings.get(away, rating_default))
    hfa = game_hfa(game, hfa_regular=hfa_regular, hfa_postseason=hfa_postseason)
    model = model_home_spread(home_elo, away_elo, hfa=hfa, elo_per_point=elo_per_point)
    edge = edge_home(model, float(market))
    pick = pick_from_edge(edge)
    steam = steam_against_pick(pick, game.get('open_spread_home'), float(market))
    home_ct = game.get('home_conference_type')
    away_ct = game.get('away_conference_type')
    if home_ct == 'FCS' or away_ct == 'FCS':
        opp_tier = 'FCS'
    else:
        opp_tier = away_ct if pick == 'home' else home_ct
    traffic = classify(
        edge=edge,
        week=game.get('week'),
        market_spread=float(market),
        opponent_tier=opp_tier,
        steam_against=steam,
        season_type=game.get('season_type'),
    )

    row: Dict[str, Any] = {
        'year': game.get('year'),
        'week': game.get('week'),
        'home_team': home,
        'away_team': away,
        'home_elo': home_elo,
        'away_elo': away_elo,
        'hfa': hfa,
        'model_spread_home': model,
        'market_spread_home': float(market),
        'open_spread_home': game.get('open_spread_home'),
        'edge_home': edge,
        'pick': pick,
        'signal': traffic['signal'],
        'vetoes': traffic['vetoes'],
        'steam_against': steam,
    }

    hs, aws = game.get('home_score'), game.get('away_score')
    if hs is not None and aws is not None and pick is not None:
        ats = home_covers(int(hs), int(aws), float(market))
        row['ats_home'] = ats
        row['hit'] = pick_hit(pick, ats)
    return row


@dataclass
class AtsSummary:
    n: int = 0
    graded: int = 0
    wins: int = 0
    losses: int = 0
    pushes: int = 0
    ats_pct: float = 0.0
    units: float = 0.0
    green: int = 0
    lean: int = 0
    pass_n: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def score_ats(rows: Iterable[Dict[str, Any]], *, signals: Optional[Iterable[str]] = None) -> AtsSummary:
    """Units at -110. Pushes excluded from ats_pct."""
    wanted = set(signals) if signals is not None else None
    wins = losses = pushes = green = lean = pass_n = 0
    n = 0
    for row in rows:
        if wanted is not None and row.get('signal') not in wanted:
            continue
        n += 1
        sig = row.get('signal')
        if sig == 'GREEN':
            green += 1
        elif sig == 'LEAN':
            lean += 1
        else:
            pass_n += 1
        hit = row.get('hit')
        if hit is True:
            wins += 1
        elif hit is False:
            losses += 1
        elif row.get('ats_home') == 'push':
            pushes += 1
    graded = wins + losses
    ats_pct = (wins / graded) if graded else 0.0
    units = wins * 0.909091 - losses
    return AtsSummary(
        n=n,
        graded=graded,
        wins=wins,
        losses=losses,
        pushes=pushes,
        ats_pct=ats_pct,
        units=round(units, 3),
        green=green,
        lean=lean,
        pass_n=pass_n,
    )
