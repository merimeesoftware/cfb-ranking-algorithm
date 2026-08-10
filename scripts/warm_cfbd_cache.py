#!/usr/bin/env python3
"""Warm CFBD game/team caches with minimal live calls (full-season fetches).

Call budget (typical):
  1 × /teams  +  2 × /games per season (regular + postseason)
  → warming 2019–2022 ≈ 1 + 8 = 9 calls if teams miss; fewer on cache hits.

Dual keys (separate 1k/mo quotas):
  CFBD_API_KEY_SLOT=A|B   # default A
  CFBD_API_KEY / CFBD_API_KEY_B
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('FLASK_ENV', 'development')
os.environ['CFBD_OFFLINE'] = '0'
# Allow enough calls for teams + N seasons × (regular+postseason)
os.environ.setdefault('CFBD_MAX_CALLS', '40')


def main() -> int:
    years = [int(y) for y in (sys.argv[1:] or ['2019', '2020', '2021', '2022', '2023', '2024'])]
    from data_processor import CFBDataProcessor
    from spend_guards import cfbd_key_slot_status, get_cfbd_call_count

    slot = cfbd_key_slot_status()
    print(
        f"CFBD key slot={slot['slot']} "
        f"has_a={slot['has_key_a']} has_b={slot['has_key_b']} "
        f"active={slot['active_configured']}"
    )
    if not slot['active_configured']:
        print('No CFBD key configured for active slot.', file=sys.stderr)
        return 1

    processor = CFBDataProcessor()
    print(f'Teams loaded: {len(processor.team_info_map)}')
    for year in years:
        games = processor.get_games_for_season(year, through_week=None, use_week_scoped_fetch=False)
        print(f'{year}: {len(games)} games cached')
    print(f'Live CFBD calls this process: {get_cfbd_call_count()}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
