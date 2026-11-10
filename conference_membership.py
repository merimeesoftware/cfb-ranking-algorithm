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


class ConferenceMembership:
    def __init__(self, payload: Dict[str, Any]):
        if payload.get('schema') != SCHEMA:
            raise MembershipError(f"unexpected membership schema {payload.get('schema')!r}")
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

        self._tiers: Dict[int, Dict[str, str]] = {}
        for season, members in self._by_season.items():
            season_tiers: Dict[str, str] = {}
            for conf in set(members.values()):
                tier = None
                for span in payload['tiers'].get(conf, []):
                    if int(span['first']) <= season <= int(span['last']):
                        tier = span['tier']
                if tier not in TIERS:
                    raise MembershipError(f'no tier for {conf!r} in {season}')
                season_tiers[conf] = tier
            self._tiers[season] = season_tiers

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

    def tier_for(self, conference: Optional[str], season: int) -> str:
        """'Power 4' / 'Group of 5' for that season's FBS conferences, else 'FCS'."""
        return self._tiers[self._require(season)].get(conference, 'FCS')


@lru_cache(maxsize=4)
def _load(path: str) -> ConferenceMembership:
    with open(path, encoding='utf-8') as fh:
        return ConferenceMembership(json.load(fh))


def load_membership(path: Optional[Union[str, Path]] = None) -> ConferenceMembership:
    return _load(str(path or MAP_PATH))
