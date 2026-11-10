"""Season-aware FBS conference membership (#101).

CFBD ``/teams`` has no year parameter, so its labels are today's conferences.
This module reads the checked-in ``data/conference_membership.json``: one base
season snapshot plus dated realignment moves, each with its source. Earlier
seasons are rebuilt by undoing moves newer than the season asked for.

Unknown input is explicit, never a silent current-conference fallback:
- a season outside ``coverage`` raises ``MembershipError``;
- a team absent from a covered season is not FBS that season
  (``conference_for`` returns None). Callers keep the per-game conference and
  use tier FCS, but raise if the game claims an FBS conference of that season.

Tiers come from dated per-conference spans, then optional per-team overrides
(``team_tiers``). "Group of 5" means "non-P4 FBS" (it covers six leagues from
2026). FBS Independents are Group of 5 by conference; Notre Dame alone is
Power 4 by team override, matching main's effective tiers.

The map is validated at load: a malformed map raises ``MembershipError``,
never ``KeyError``/``TypeError``.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Union

MAP_PATH = Path(__file__).resolve().parent / 'data' / 'conference_membership.json'
SCHEMA = 'true-rankings/conference-membership/v1'
TIERS = ('Power 4', 'Group of 5')


class MembershipError(ValueError):
    """The membership map cannot answer, or the map itself is inconsistent."""


def _spans(spans: Any, label: str, first: int, last: int) -> list:
    """Validated, non-overlapping tier spans inside coverage."""
    if not isinstance(spans, list) or not spans:
        raise MembershipError(f'tier spans for {label!r} must be a non-empty list')
    out = []
    for span in spans:
        if not isinstance(span, dict) or not isinstance(span.get('first'), int) \
                or not isinstance(span.get('last'), int) or span.get('tier') not in TIERS:
            raise MembershipError(f'bad tier span for {label!r}: {span!r}')
        if not (first <= span['first'] <= span['last'] <= last):
            raise MembershipError(f'tier span for {label!r} outside coverage: {span!r}')
        out.append((span['first'], span['last'], span['tier']))
    out.sort()
    for (_, a_last, _), (b_first, _, _) in zip(out, out[1:]):
        if b_first <= a_last:
            raise MembershipError(f'overlapping tier spans for {label!r}')
    return out


def _span_tier(spans: list, season: int) -> Optional[str]:
    for first, last, tier in spans:
        if first <= season <= last:
            return tier
    return None


def _check_shape(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise MembershipError('membership map must be a JSON object')
    if payload.get('schema') != SCHEMA:
        raise MembershipError(f"unexpected membership schema {payload.get('schema')!r}")
    if not isinstance(payload.get('version'), str) or not payload['version']:
        raise MembershipError('membership map needs a non-empty string version')
    cov = payload.get('coverage')
    if not isinstance(cov, dict) or not isinstance(cov.get('first_season'), int) \
            or not isinstance(cov.get('last_season'), int) \
            or cov['first_season'] > cov['last_season']:
        raise MembershipError('coverage needs integer first_season <= last_season')
    base = payload.get('base')
    if not isinstance(base, dict) or not isinstance(base.get('season'), int) \
            or not isinstance(base.get('conferences'), dict):
        raise MembershipError('base needs an integer season and a conferences object')
    for conf, teams in base['conferences'].items():
        if not isinstance(teams, list) or not all(isinstance(t, str) and t for t in teams):
            raise MembershipError(f'base conference {conf!r} must list team names')
    moves = payload.get('moves', [])
    if not isinstance(moves, list):
        raise MembershipError('moves must be a list')
    seen = set()
    for m in moves:
        if not isinstance(m, dict) or not isinstance(m.get('team'), str) \
                or not isinstance(m.get('season'), int):
            raise MembershipError(f'bad move {m!r}')
        frm, to = m.get('from'), m.get('to')
        if not all(x is None or isinstance(x, str) for x in (frm, to)) or frm == to:
            raise MembershipError(f"move {m['season']} {m['team']}: bad from/to {frm!r} -> {to!r}")
        if m['season'] > cov['last_season']:
            raise MembershipError(f"move {m['season']} {m['team']} is after coverage")
        if (m['team'], m['season']) in seen:
            raise MembershipError(f"duplicate move {m['season']} {m['team']}")
        seen.add((m['team'], m['season']))
    if not isinstance(payload.get('tiers'), dict):
        raise MembershipError('tiers must be an object')
    if not isinstance(payload.get('team_tiers', {}), dict):
        raise MembershipError('team_tiers must be an object')


class ConferenceMembership:
    def __init__(self, payload: Dict[str, Any]):
        _check_shape(payload)
        self.version = str(payload['version'])
        cov = payload['coverage']
        self.first_season = int(cov['first_season'])
        self.last_season = int(cov['last_season'])
        base = payload['base']
        base_season = int(base['season'])
        if base_season != self.last_season:
            raise MembershipError('base season must be the last covered season')

        current: Dict[str, str] = {}
        for conf, teams in base['conferences'].items():
            for team in teams:
                if team in current:
                    raise MembershipError(f'{team} listed twice in base season')
                current[team] = conf

        moves = sorted(payload.get('moves', []), key=lambda m: -int(m['season']))
        self._by_season: Dict[int, Dict[str, str]] = {base_season: dict(current)}
        idx = 0
        for season in range(base_season, self.first_season - 1, -1):
            # Undo every move that took effect after `season`.
            while idx < len(moves) and int(moves[idx]['season']) > season:
                m = moves[idx]
                team, frm, to = m['team'], m.get('from'), m.get('to')
                if not m.get('source'):
                    raise MembershipError(f'move for {team} has no source')
                if current.get(team) != to:
                    raise MembershipError(
                        f"move {m['season']} {team}: expected {to!r}, map has {current.get(team)!r}"
                    )
                if frm is None:
                    current.pop(team, None)
                else:
                    current[team] = frm
                idx += 1
            self._by_season[season] = dict(current)
        if idx != len(moves):
            raise MembershipError('moves outside coverage')

        conf_spans = {
            conf: _spans(spans, conf, self.first_season, self.last_season)
            for conf, spans in payload['tiers'].items()
        }
        self._tiers: Dict[int, Dict[str, str]] = {}
        for season, members in self._by_season.items():
            season_tiers: Dict[str, str] = {}
            for conf in set(members.values()):
                tier = _span_tier(conf_spans.get(conf, []), season)
                if tier is None:
                    raise MembershipError(f'no tier for {conf!r} in {season}')
                season_tiers[conf] = tier
            self._tiers[season] = season_tiers

        # Per-team overrides win over the conference tier (Notre Dame = P4).
        self._team_tiers: Dict[int, Dict[str, str]] = {s: {} for s in self._by_season}
        for team, spans in payload.get('team_tiers', {}).items():
            for first, last, tier in _spans(spans, team, self.first_season, self.last_season):
                for season in range(first, last + 1):
                    if team not in self._by_season[season]:
                        raise MembershipError(f'tier override for {team} in {season}, not FBS then')
                    self._team_tiers[season][team] = tier

    def covers(self, season: int) -> bool:
        return self.first_season <= int(season) <= self.last_season

    def _require(self, season: int) -> int:
        season = int(season)
        if not self.covers(season):
            raise MembershipError(
                f'season {season} is outside conference membership coverage '
                f'{self.first_season}-{self.last_season} (map {self.version}); '
                'add it to data/conference_membership.json'
            )
        return season

    def season_map(self, season: int) -> Dict[str, str]:
        """FBS team -> conference for that season. Raises outside coverage."""
        return dict(self._by_season[self._require(season)])

    def conference_for(self, team: str, season: int) -> Optional[str]:
        """Conference that season, or None when the team was not FBS then."""
        return self._by_season[self._require(season)].get(team)

    def fbs_conferences(self, season: int) -> set:
        return set(self._tiers[self._require(season)])

    def tier_for(self, conference: Optional[str], season: int, team: Optional[str] = None) -> str:
        """'Power 4' / 'Group of 5' for that season, else 'FCS'.

        With ``team``, a per-team override (``team_tiers``) wins when that team
        is in ``conference`` that season; otherwise the conference span applies.
        """
        season = self._require(season)
        if team is not None and self._by_season[season].get(team) == conference:
            override = self._team_tiers[season].get(team)
            if override is not None:
                return override
        return self._tiers[season].get(conference, 'FCS')


@lru_cache(maxsize=4)
def _load(path: str) -> ConferenceMembership:
    with open(path, encoding='utf-8') as fh:
        return ConferenceMembership(json.load(fh))


def load_membership(path: Optional[Union[str, Path]] = None) -> ConferenceMembership:
    return _load(str(path or MAP_PATH))
