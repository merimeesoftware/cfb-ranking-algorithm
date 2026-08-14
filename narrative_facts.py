"""Pure narrative fact extraction and stub prose (no I/O, no LLM)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from path_to_climb import compute_path_to_climb
from shareable_blurb import stub_shareable_blurb

CFP_BAND = 12
DEFAULT_TOP_MOVEMENTS = 5


def _rank_map(rankings: Dict[str, Any]) -> Dict[str, int]:
    return {
        t['team_name']: i + 1
        for i, t in enumerate(rankings.get('team_rankings') or [])
    }


def _team_rows(rankings: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for i, t in enumerate(rankings.get('team_rankings') or []):
        rows.append({
            'team_name': t.get('team_name'),
            'rank': i + 1,
            'conference': t.get('conference'),
            'final_ranking_score': t.get('final_ranking_score'),
            'quality_wins': t.get('quality_wins'),
            'quality_losses': t.get('quality_losses'),
            'bad_losses': t.get('bad_losses'),
            'records': t.get('records') or {},
        })
    return rows


def extract_week_facts(
    current_rankings: Dict[str, Any],
    previous_rankings: Optional[Dict[str, Any]] = None,
    *,
    cfp_band: int = CFP_BAND,
    top_n_movements: int = DEFAULT_TOP_MOVEMENTS,
) -> Dict[str, Any]:
    """
    Build structured week-story facts from ranking snapshots.

    team_rankings lists are assumed ordered by rank (index 0 = #1).
    If previous_rankings is None, movers / CFP band / climbs / falls are empty
    and snapshot.has_wow is False.
    """
    teams = current_rankings.get('team_rankings') or []
    year = current_rankings.get('year')
    week = current_rankings.get('week')
    top_teams = _team_rows(current_rankings)[: max(cfp_band, 25)]

    movers: List[Dict[str, Any]] = []
    top_climbs: List[Dict[str, Any]] = []
    top_falls: List[Dict[str, Any]] = []
    entered: List[Dict[str, Any]] = []
    exited: List[Dict[str, Any]] = []
    has_wow = previous_rankings is not None and bool(
        previous_rankings.get('team_rankings')
    )

    if has_wow:
        prev = _rank_map(previous_rankings)
        for i, t in enumerate(teams):
            name = t.get('team_name')
            if not name or name not in prev:
                continue
            rank = i + 1
            previous_rank = prev[name]
            delta = previous_rank - rank  # positive = climbed
            entry = {
                'team_name': name,
                'rank': rank,
                'previous_rank': previous_rank,
                'delta': delta,
                'conference': t.get('conference'),
            }
            if delta != 0:
                movers.append(entry)

            was_in = previous_rank <= cfp_band
            now_in = rank <= cfp_band
            if now_in and not was_in:
                entered.append(entry)
            elif was_in and not now_in:
                exited.append(entry)

        climbs = sorted(
            [m for m in movers if m['delta'] > 0],
            key=lambda m: (-m['delta'], m['rank']),
        )
        falls = sorted(
            [m for m in movers if m['delta'] < 0],
            key=lambda m: (m['delta'], m['rank']),
        )
        top_climbs = climbs[:top_n_movements]
        top_falls = falls[:top_n_movements]

    notable_qw = [
        {
            'team_name': t.get('team_name'),
            'rank': i + 1,
            'quality_wins': t.get('quality_wins'),
        }
        for i, t in enumerate(teams[:25])
        if (t.get('quality_wins') or 0) and int(t.get('quality_wins') or 0) > 0
    ][:10]

    return {
        'snapshot': {
            'year': year,
            'week': week,
            'has_wow': has_wow,
            'team_count': len(teams),
            'cfp_band': cfp_band,
            'previous_week': (
                previous_rankings.get('week') if has_wow and previous_rankings else None
            ),
        },
        'top_teams': top_teams[:cfp_band],
        'movers': movers,
        'top_climbs': top_climbs,
        'top_falls': top_falls,
        'cfp_band_changes': {
            'entered': entered,
            'exited': exited,
        },
        'notable_quality_wins': notable_qw,
    }


def stub_week_story(facts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic week-story prose (StoryBrand conflict voice).

    Headline = biggest jumper vs leader still owning #1.
    Body = risers / taking heat / playoff-band shakeup / top 5 + debate hook.
    Never leaks AI_MODE, stub, or MiniMax into fan-visible copy.
    """
    snap = facts.get('snapshot') or {}
    year = snap.get('year', '?')
    week = snap.get('week', '?')
    top = facts.get('top_teams') or []
    leader = top[0]['team_name'] if top else 'The field'

    paragraphs: List[str] = []
    if snap.get('has_wow'):
        climbs = facts.get('top_climbs') or []
        falls = facts.get('top_falls') or []
        if climbs:
            c = climbs[0]
            spots = c['delta']
            spot_word = 'spot' if spots == 1 else 'spots'
            if c['team_name'] == leader:
                headline = f"{leader} jumps {spots} {spot_word} into #1"
            else:
                headline = (
                    f"{c['team_name']} jumps {spots} {spot_word} — "
                    f"{leader} still owns #1"
                )
            climb_bits = [
                f"{m['team_name']} (+{m['delta']} to #{m['rank']})"
                for m in climbs[:3]
            ]
            paragraphs.append('Risers: ' + '; '.join(climb_bits) + '.')
        else:
            headline = f"{leader} still owns #1 — quiet week on the board"
            paragraphs.append(
                f"The board held steady into week {week} — "
                f"{leader} still owns #1."
            )
        if falls:
            fall_bits = [
                f"{m['team_name']} ({m['delta']} to #{m['rank']})"
                for m in falls[:3]
            ]
            paragraphs.append('Taking heat: ' + '; '.join(fall_bits) + '.')

        band = facts.get('cfp_band_changes') or {}
        entered = band.get('entered') or []
        exited = band.get('exited') or []
        if entered or exited:
            parts = []
            if entered:
                parts.append(
                    'in: '
                    + ', '.join(f"{e['team_name']} (#{e['rank']})" for e in entered[:5])
                )
            if exited:
                parts.append(
                    'out: '
                    + ', '.join(f"{e['team_name']} (#{e['rank']})" for e in exited[:5])
                )
            paragraphs.append('Playoff band shakeup — ' + '; '.join(parts) + '.')
    else:
        headline = f"Week {week} board: {leader} owns #1"
        paragraphs.append(
            f"Fresh snapshot for week {week} {year} — no week-over-week compare yet. "
            f"Top of the board: "
            + ', '.join(
                f"#{t['rank']} {t['team_name']}" for t in top[:5]
            )
            + '.'
        )

    if top:
        n = min(5, len(top))
        top_line = (
            f'Top {n}: '
            + ', '.join(f"#{t['rank']} {t['team_name']}" for t in top[:n])
            + '.'
        )
        if len(top) >= 2:
            second = top[1]['team_name']
            paragraphs.append(
                f"{top_line} Who belongs higher — {leader} or {second}?"
            )
        else:
            paragraphs.append(f'{top_line} Who belongs higher?')

    return {
        'headline': headline,
        'paragraphs': paragraphs,
        'facts': facts,
    }


def stub_why_blurbs(
    rankings: Dict[str, Any],
    top_n: int = 25,
) -> Dict[str, Any]:
    """
    Build Top-N Why blurbs as fan takes via stub_shareable_blurb.
    """
    teams = rankings.get('team_rankings') or []
    blurbs: Dict[str, str] = {}
    limit = min(top_n, len(teams))

    for i in range(limit):
        team = teams[i]
        name = team.get('team_name', f'Team {i + 1}')
        above = teams[i - 1] if i > 0 else None
        below = teams[i + 1] if i + 1 < len(teams) else None
        path = compute_path_to_climb(team, above)
        context = {
            'team_name': name,
            'rank': i + 1,
            'conference': team.get('conference'),
            'records': team.get('records') or {},
            'quality_wins': team.get('quality_wins'),
            'path_to_climb': path,
            'neighbor_ahead': above.get('team_name') if above else None,
            'neighbor_behind': below.get('team_name') if below else None,
        }
        blurbs[name] = stub_shareable_blurb(context)

    return {
        'year': rankings.get('year'),
        'week': rankings.get('week'),
        'top_n': limit,
        'blurbs': blurbs,
    }
