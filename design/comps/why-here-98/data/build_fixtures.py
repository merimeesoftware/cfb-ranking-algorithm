"""Build the #98 why-here comp fixtures (board order per D-20261018-198).

Order = the parts in data/order-config.json: 'elo_heat' (how they look + Heat, 2 parts)
or 'elo_only' (how they look, 1 part; the order if Heat fails the #96 gate, and the
only option when Heat has no 3-week history). Resume, schedule strength and quality of
wins are CONTEXT: shown beside the bar, never part of the gap.

Inputs (all invented; this file does not read a published board)
- data/roster-synthetic.json  seeded teams, records, and ratings
- data/order-config.json      ordering parts + weights; illustrative Heat
- data/games-synthetic.json   invented game list + venue stand-in for #105
Output: data/fixtures.json. Field names are the ones #105/#96 are asked to ship
(prev_rank, resume_rank, sos_rank, sov_rank, heat, parts[], venue, tag).
The season and week numbers are labels for the comp states.
"""
import json, math, pathlib

HERE = pathlib.Path(__file__).resolve().parent
CFG = json.loads((HERE / 'order-config.json').read_text())
WINDOW = CFG['heat_window_weeks']
SYNTHETIC = json.loads((HERE / 'games-synthetic.json').read_text())
ROSTER = json.loads((HERE / 'roster-synthetic.json').read_text())
GAMES = SYNTHETIC['teams']
DEFAULT_GAMES = SYNTHETIC['default']
WEEKS = {int(k): v for k, v in ROSTER['weeks'].items()}


def load(week):
    """Seeded roster for one labeled week. Missing weeks are not a published board."""
    if week not in WEEKS:
        raise FileNotFoundError(week)
    spec = WEEKS[week]
    rows = []
    for team in ROSTER['teams']:
        name = team['team_name']
        wins, losses = spec['records'][name]
        rows.append({
            'team_name': name,
            'conference': team['conference'],
            'conference_type': team['conference_type'],
            'color': team['color'],
            'team_quality_score': spec['quality'][name],
            'record_score': spec['resume'][name],
            'sos_rank': spec['sos'][name],
            'sov_rank': spec['sov'][name],
            'records': {'total_wins': wins, 'total_losses': losses},
        })
    return rows


def pct(values, p):
    v = sorted(values)
    k = (len(v) - 1) * p / 100
    f, c = math.floor(k), math.ceil(k)
    return v[f] if f == c else v[f] + (v[c] - v[f]) * (k - f)


def board(week, variant):
    """Teams for a week ordered by the variant's parts. Heat needs WINDOW weeks of history."""
    teams = [dict(t) for t in load(week)]
    parts = CFG['variants'][variant]['parts']
    if any(p['field'] == 'heat' for p in parts):
        if week <= WINDOW:
            raise ValueError('Heat unavailable this early')
        back = {t['team_name']: t['team_quality_score'] for t in load(week - WINDOW)}
        for t in teams:
            t['heat'] = 1500 + t['team_quality_score'] - back.get(t['team_name'], t['team_quality_score'])
    for t in teams:
        t['_score'] = sum(p['weight'] * t[p['field']] for p in parts)
    teams.sort(key=lambda t: -t['_score'])
    # sos/sov seeds are invented. "#{x} of {N}" re-ranks them on this roster only.
    for f in ('sos_rank', 'sov_rank'):
        order = sorted(teams, key=lambda t: (t.get(f) or 10**6, t['team_name']))
        for i, t in enumerate(order):
            t[f + '_all'] = t.get(f)
            t[f] = i + 1
    by_resume = sorted(teams, key=lambda t: -t['record_score'])
    rr = {t['team_name']: i + 1 for i, t in enumerate(by_resume)}
    for i, t in enumerate(teams):
        t['_rank'] = i + 1
        t['resume_rank'] = rr[t['team_name']]
    return teams


def prev_ranks(week, variant):
    try:
        return {t['team_name']: t['_rank'] for t in board(week - 1, variant)}
    except (ValueError, FileNotFoundError):
        return {}


def row(t, prev):
    r = t['records']
    return {'rank': t['_rank'], 'prev_rank': prev.get(t['team_name']), 'team_name': t['team_name'],
            'conference': t['conference'], 'conference_type': t.get('conference_type'),
            'record': f"{r['total_wins']}-{r['total_losses']}", 'final_ranking_score': t['_score'],
            'resume_rank': t['resume_rank'], 'color': t.get('color')}


def compare(a, b, parts):
    if b is None:
        return None
    ps = [{'key': p['key'], 'name': p['name'], 'weight': p['weight'], 'value_self': a[p['field']],
           'value_other': b[p['field']], 'contribution': p['weight'] * (a[p['field']] - b[p['field']])} for p in parts]
    return {'team_name': b['team_name'], 'rank': b['_rank'], 'final_ranking_score': b['_score'],
            'gap': a['_score'] - b['_score'], 'parts': ps,
            'context': {'resume_rank': b['resume_rank'], 'sos_rank': b.get('sos_rank'), 'sov_rank': b.get('sov_rank')}}


def games_for(name, week, teams):
    fbs = {t['team_name']: t for t in teams}
    elos = [t['team_quality_score'] for t in teams]
    p75, p25 = pct(elos, 75), pct(elos, 25)
    p4 = [t['team_quality_score'] for t in teams if t.get('conference_type') == 'Power 4']
    me = fbs[name]
    cupcake = max(pct(p4, 25), p25) if me.get('conference_type') == 'Power 4' else p25
    out = []
    for g in GAMES.get(name, DEFAULT_GAMES):
        if g['week'] > week:
            continue
        opp = fbs.get(g['opponent'])
        elo = opp['team_quality_score'] if opp else None
        tag = None
        if g['result'] == 'W':
            if elo is not None and elo > p75:
                tag = 'quality_win'
            elif opp is None or elo < cupcake:
                tag = 'cupcake'
        elif opp is None or elo < cupcake:
            tag = 'bad_loss'
        out.append({'week': g['week'], 'opponent': g['opponent'], 'opponent_rank': opp['_rank'] if opp else None,
                    'venue': g['venue'], 'result': g['result'], 'tag': tag})
    return out


def open_state(week, variant, name):
    teams = board(week, variant)
    prev = prev_ranks(week, variant)
    parts = CFG['variants'][variant]['parts']
    idx = next(i for i, t in enumerate(teams) if t['team_name'] == name)
    t = teams[idx]
    games = games_for(name, week, teams)
    last = games[-WINDOW:]
    r = t['records']
    team = {'rank': t['_rank'], 'prev_rank': prev.get(name), 'team_name': name, 'conference': t['conference'],
            'record': f"{r['total_wins']}-{r['total_losses']}", 'games_played': r['total_wins'] + r['total_losses'],
            'final_ranking_score': t['_score'], 'resume_rank': t['resume_rank'], 'sos_rank': t.get('sos_rank'),
            'sov_rank': t.get('sov_rank'), 'sos_rank_all_divisions': t.get('sos_rank_all'),
            'sov_rank_all_divisions': t.get('sov_rank_all'), 'board_size': len(teams), 'color': t.get('color'),
            'url': f"{{SITE_URL}}/teams/{name.lower().replace(' ', '-')}?year=2024&week={week}"}
    if any(p['key'] == 'heat' for p in parts):
        team['heat'] = t['heat']
        team['recent'] = {'k': len(last), 'wins': sum(g['result'] == 'W' for g in last), 'losses': sum(g['result'] == 'L' for g in last)}
    rows = [row(x, prev) for x in teams]
    return {
        'season': 2024, 'week': week, 'variant': variant, 'parts_count': len(parts), 'board_size': len(teams),
        'board': rows[max(0, idx - 2): idx + 3],
        'open': {'team': team,
                 'parts': [{'key': p['key'], 'name': p['name'], 'weight': p['weight'], 'value': t[p['field']],
                            'contribution': p['weight'] * t[p['field']]} for p in parts],
                 'above': compare(t, teams[idx - 1], parts) if idx > 0 else None,
                 'below': compare(t, teams[idx + 1], parts) if idx + 1 < len(teams) else None,
                 'games': games},
    }


def main():
    S = {}
    teams = board(10, 'elo_heat')
    prev = prev_ranks(10, 'elo_heat')
    S['board-closed'] = {'season': 2024, 'week': 10, 'variant': 'elo_heat', 'parts_count': 2, 'board_size': len(teams),
                         'board': [row(x, prev) for x in teams[:25]], 'open': None}
    mid, heat_team = ROSTER['open']['mid'], ROSTER['open']['heat']
    S['row-open-mid'] = open_state(10, 'elo_heat', mid)
    S['row-open-mid-1part'] = open_state(10, 'elo_only', mid)
    S['negative-part'] = {**S['row-open-mid'], 'focus': 'negative'}
    S['negative-part-1part'] = {**S['row-open-mid-1part'], 'focus': 'negative'}
    S['heat'] = {**open_state(10, 'elo_heat', heat_team), 'focus': 'heat'}
    S['row-open-first'] = open_state(10, 'elo_heat', teams[0]['team_name'])
    S['row-open-last'] = open_state(10, 'elo_heat', teams[-1]['team_name'])
    S['early-week'] = open_state(1, 'elo_only', mid)   # Heat unavailable in week 1 → 1 part
    base = S['row-open-mid']
    S['loading'] = {**base, 'open': {'team': base['open']['team'], 'status': 'loading'}}
    S['error'] = {**base, 'open': {'team': base['open']['team'], 'status': 'error'}}
    S['season-unavailable'] = {'season': 2026, 'week': 8, 'board': None, 'open': None, 'status': 'unavailable'}
    S['sheet-390'] = {**base, 'sheet': True}
    S['share-card'] = base
    S['share-card-1part'] = S['row-open-mid-1part']

    # Proofs the comps rely on.
    for k, s in S.items():
        o = s.get('open') or {}
        for side in ('above', 'below'):
            c = o.get(side)
            if c:
                assert abs(sum(p['contribution'] for p in c['parts']) - c['gap']) < 1e-9, (k, side)
    h = S['heat']['open']
    flips = [c for c in (h['above'], h['below']) if c and {p['key']: p['contribution'] for p in c['parts']}['strength'] * c['gap'] < 0]
    assert flips, 'heat state must show Heat deciding a comparison'
    assert any(p['contribution'] < 0 for c in (base['open']['above'], base['open']['below']) for p in c['parts'])
    missing = sorted({g['opponent'] for s in S.values() for g in ((s.get('open') or {}).get('games') or []) if g['opponent_rank'] is None})
    (HERE / 'fixtures.json').write_text(json.dumps(S, indent=1))
    for k, s in S.items():
        o = s.get('open') or {}
        t = o.get('team', {})
        print(f"{k:22} {s.get('variant','-'):9} #{t.get('rank')} {t.get('team_name')} above={bool(o.get('above'))} below={bool(o.get('below'))} games={len(o.get('games', []))}")
    print('unranked opponents (FCS or name mismatch):', missing)


if __name__ == '__main__':
    main()
