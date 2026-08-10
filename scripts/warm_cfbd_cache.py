#!/usr/bin/env python3
"""Warm CFBD game/team caches with minimal live calls (full-season fetches)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('FLASK_ENV', 'development')
os.environ['CFBD_OFFLINE'] = '0'
# Allow enough calls for teams + 3 seasons × (regular+postseason)
os.environ.setdefault('CFBD_MAX_CALLS', '40')


def main() -> int:
    years = [int(y) for y in (sys.argv[1:] or ['2022', '2023', '2024'])]
    from data_processor import CFBDataProcessor

    processor = CFBDataProcessor()
    print(f'Teams loaded: {len(processor.team_info_map)}')
    for year in years:
        games = processor.get_games_for_season(year, through_week=None, use_week_scoped_fetch=False)
        print(f'{year}: {len(games)} games cached')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
