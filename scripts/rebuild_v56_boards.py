#!/usr/bin/env python3
"""Rebuild 2024 weeks 1-15 and 2026 weeks 1-10 under the current algo.

Offline. Does not call CFBD. Does not read 2025 games. Does not write prior files.
2024 rows: TR_GAMES_DIR/games-2024-both.json.
2026 rows: a CSV with the sportsdataverse 2026 schedule columns. Not 2025.

Logos and colors are copied from the boards already on disk so a missing
/teams payload does not blank them.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('CFBD_OFFLINE', '1')
os.environ.setdefault('AI_MODE', 'stub')
os.environ.setdefault('FLASK_ENV', 'development')

from api_integration import CFBDApiClient
from data_processor import CFBDataProcessor
from ranking_service import calculate_rankings_logic, slim_rankings_for_list
from static_rankings import write_static_rankings

BOARDS = ROOT / 'frontend' / 'static' / 'rankings'
LOGO_KEYS = ('logo', 'logo_dark', 'color', 'alt_color')


class LocalGames:
    def __init__(self, games, logos):
        self._games = games
        self.team_info_map = logos

    def get_games_for_season(self, year, through_week=None, use_week_scoped_fetch=True):
        del use_week_scoped_fetch
        if int(year) == 2025:
            raise SystemExit('2025 games are not read.')
        selected = []
        for game in self._games:
            if int(game.get('year') or 0) != int(year):
                continue
            season_type = game.get('season_type') or 'regular'
            week = game.get('week')
            if season_type == 'postseason':
                if through_week is None or int(through_week) >= 15:
                    selected.append(game)
                continue
            if through_week is not None and (week is None or int(week) > int(through_week)):
                continue
            selected.append(game)
        return selected

    def organize_games_by_week(self, games):
        return CFBDataProcessor.organize_games_by_week(self, games)


class _Args(dict):
    def get(self, key, default=None):
        return dict.get(self, key, default)


def _blank(value):
    return value is None or value == '' or value == 'NA'


def _number(value):
    if _blank(value):
        return None
    return int(float(value))


def rows_from_cfbd_json(path):
    raw = json.loads(Path(path).read_text(encoding='utf-8'))
    client = CFBDApiClient(api_key='offline-placeholder')
    proc = CFBDataProcessor(api_client=client)
    return proc._process_raw_games([client._transform_game(game) for game in raw], season=int(raw[0]['season']))


def rows_from_schedule_csv(path):
    client = CFBDApiClient(api_key='offline-placeholder')
    proc = CFBDataProcessor(api_client=client)
    raw = []
    with open(path, newline='', encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            if int(row['season']) == 2025:
                raise SystemExit('Refusing a 2025 schedule row.')
            raw.append({
                'id': _number(row.get('game_id')),
                'completed': row.get('completed') == 'TRUE',
                'week': _number(row.get('week')),
                'season': _number(row.get('season')),
                'homeTeam': row.get('home_team'),
                'awayTeam': row.get('away_team'),
                'homePoints': _number(row.get('home_points')),
                'awayPoints': _number(row.get('away_points')),
                'homeConference': None if _blank(row.get('home_conference')) else row.get('home_conference'),
                'awayConference': None if _blank(row.get('away_conference')) else row.get('away_conference'),
                'seasonType': row.get('season_type') or 'regular',
                'neutralSite': row.get('neutral_site') == 'TRUE',
                'notes': None if _blank(row.get('notes')) else row.get('notes'),
                'startDate': None if _blank(row.get('start_date')) else row.get('start_date'),
            })
    season = raw[0]['season']
    return proc._process_raw_games([client._transform_game(game) for game in raw], season=season)


def logo_map(year):
    logos = {}
    folder = BOARDS / str(year)
    for path in sorted(folder.glob('week-*.json')):
        if path.name.count('.') != 1:
            continue
        payload = json.loads(path.read_text(encoding='utf-8'))
        for team in payload.get('team_rankings') or []:
            name = team.get('team_name')
            if not name or name in logos:
                continue
            info = {key: team.get(key) for key in LOGO_KEYS}
            info['logos'] = [value for value in (info.get('logo'), info.get('logo_dark')) if value]
            logos[name] = info
    return logos


def rebuild(year, weeks, games):
    logos = logo_map(year)
    processor = LocalGames(games, logos)
    for week in weeks:
        data = calculate_rankings_logic(processor, year, week, _Args())
        if not data:
            raise SystemExit(f'No board for {year} week {week}')
        slim = slim_rankings_for_list(data)
        # calculate_rankings_logic already copied logos from team_info_map.
        path = write_static_rankings(slim, year, week, root=BOARDS)
        print(f'wrote {path} teams={len(slim["team_rankings"])} algo={slim.get("algo")}', flush=True)


def main():
    games_dir = os.environ.get('TR_GAMES_DIR', '')
    csv_2026 = os.environ.get('TR_2026_SCHEDULE', '')
    if not games_dir or not csv_2026:
        raise SystemExit('Set TR_GAMES_DIR and TR_2026_SCHEDULE. 2025 is not read.')
    games_2024 = rows_from_cfbd_json(Path(games_dir) / 'games-2024-both.json')
    games_2026 = rows_from_schedule_csv(csv_2026)
    rebuild(2024, list(range(1, 16)), games_2024)
    rebuild(2026, list(range(1, 11)), games_2026)


if __name__ == '__main__':
    main()
