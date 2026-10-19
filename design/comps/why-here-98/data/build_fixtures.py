"""Build the #98 why-here comp fixtures from data already in the repo.

Inputs
- frontend/static/rankings/2024/week-{1,7,9,10}.json  (published static board)
- ranking_service.py DEFAULT_CONFIG                  (formula weights, read with ast;
                                                      never hard-coded here)
- data/games-2024-espn.json                          (game list + venue stand-in for #105)

Output: data/fixtures.json, one object per comp state. Field names are the ones
#105 is asked to add (prev_rank, sos_rank, sov_rank, parts[], venue, tag) so the
comps assert against the shape the engine will ship.
"""
import ast, json, math, pathlib

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[3]
STATIC = REPO / 'frontend/static/rankings/2024'


def default_config():
    tree = ast.parse((REPO / 'ranking_service.py').read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) == 'DEFAULT_CONFIG' for t in node.targets):
            return ast.literal_eval(node.value)
    raise SystemExit('DEFAULT_CONFIG not found')


CFG = default_config()
# Part order and score field per part. Names are data (engine parts[].name);
# fixture values use PURPOSE.md's locked fan-language terms (Heat named in the
# 2026-10-18 amendment).
PARTS_3 = [
    {'key': 'strength', 'weight_key': 'team_quality_weight', 'field': 'team_quality_score', 'name': 'how they look'},
    {'key': 'resume', 'weight_key': 'record_weight', 'field': 'record_score', 'name': 'who they beat'},
    {'key': 'league', 'weight_key': 'conference_weight', 'field': 'conference_quality_score', 'name': 'league strength'},
]
# Illustrative "Elo plus Heat" config for the 4-part comp only. Michael has not
# picked weights and Heat ships only if the backtest passes (PURPOSE.md); these live in this fixture, not in any renderer.
ILLUSTRATIVE_4 = {'strength': 0.70, 'resume': 0.15, 'league': 0.05, 'heat': 0.10}


def load(week):
    return json.loads((STATIC / f'week-{week}.json').read_text())


def pct(values, p):
    v = sorted(values)
    k = (len(v) - 1) * p / 100
    f, c = math.floor(k), math.ceil(k)
    return v[f] if f == c else v[f] + (v[c] - v[f]) * (k - f)


def board_rows(teams, prev):
    prev_rank = {t['team_name']: i + 1 for i, t in enumerate(prev)} if prev else {}
    rows = []
    for i, t in enumerate(teams):
        r = t['records']
        rows.append({
            'rank': i + 1,
            'prev_rank': prev_rank.get(t['team_name']),
            'team_name': t['team_name'],
            'conference': t['conference'],
            'conference_type': t.get('conference_type'),
            'record': f"{r['total_wins']}-{r['total_losses']}",
            'final_ranking_score': t['final_ranking_score'],
            'color': t.get('color'),
        })
    return rows


def parts_for(team, spec):
    out = []
    for p in spec:
        w = p['weight']
        v = team['_values'][p['key']]
        out.append({'key': p['key'], 'name': p['name'], 'weight': w, 'value': v, 'contribution': w * v})
    return out


def compare(self_t, other, spec, other_rank):
    if other is None:
        return None
    parts = []
    for p in spec:
        w = p['weight']
        a, b = self_t['_values'][p['key']], other['_values'][p['key']]
        parts.append({'key': p['key'], 'name': p['name'], 'weight': w, 'value_self': a,
                      'value_other': b, 'contribution': w * (a - b)})
    return {'team_name': other['team_name'], 'rank': other_rank,
            'final_ranking_score': other['_score'],
            'gap': self_t['_score'] - other['_score'], 'parts': parts}


def games_for(name, week, teams, games_src):
    fbs = {t['team_name']: t for t in teams}
    elos = [t['team_quality_score'] for t in teams]
    p75, p90, p25 = pct(elos, 75), pct(elos, 90), pct(elos, 25)
    p4 = [t['team_quality_score'] for t in teams if t.get('conference_type') == 'Power 4']
    me = fbs[name]
    cupcake = max(pct(p4, 25), p25) if me.get('conference_type') == 'Power 4' else p25
    rank = {t['team_name']: i + 1 for i, t in enumerate(teams)}
    out = []
    for g in games_src.get(name, []):
        if g['week'] > week:
            continue
        opp = fbs.get(g['opponent'])
        elo = opp['team_quality_score'] if opp else None
        is_fcs = opp is None
        tag = None
        if g['result'] == 'W':
            if elo is not None and elo > p75:
                tag = 'quality_win'
            elif is_fcs or elo < cupcake:
                tag = 'cupcake'
        else:
            if is_fcs or elo < cupcake:
                tag = 'bad_loss'
        out.append({'week': g['week'], 'opponent': g['opponent'], 'opponent_rank': rank.get(g['opponent']),
                    'venue': g['venue'], 'result': g['result'], 'tag': tag})
    return out


def prepare(teams, spec_keys, weights, heat=None):
    for t in teams:
        vals = {'strength': t['team_quality_score'], 'resume': t['record_score'], 'league': t['conference_quality_score']}
        if heat is not None:
            vals['heat'] = heat[t['team_name']]
        t['_values'] = vals
        t['_score'] = sum(weights[k] * vals[k] for k in spec_keys)
    return teams


def open_state(teams, prev, name, spec, games_src, week, season=2024):
    idx = next(i for i, t in enumerate(teams) if t['team_name'] == name)
    t = teams[idx]
    prev_rank = {x['team_name']: i + 1 for i, x in enumerate(prev)} if prev else {}
    r = t['records']
    return {
        'team': {'rank': idx + 1, 'prev_rank': prev_rank.get(name), 'team_name': name,
                 'conference': t['conference'], 'record': f"{r['total_wins']}-{r['total_losses']}",
                 'games_played': r['total_wins'] + r['total_losses'],
                 'final_ranking_score': t['_score'], 'sos_rank': t.get('sos_rank'), 'sov_rank': t.get('sov_rank'),
                 'color': t.get('color'),
                 'url': f"https://truerankings.com/teams/{name.lower().replace(' ', '-')}?year={season}&week={week}"},
        'parts': parts_for(t, spec),
        'above': compare(t, teams[idx - 1], spec, idx) if idx > 0 else None,
        'below': compare(t, teams[idx + 1], spec, idx + 2) if idx + 1 < len(teams) else None,
        'games': games_for(name, week, teams, games_src),
    }


def main():
    games_src = json.loads((HERE / 'games-2024-espn.json').read_text())['teams']
    spec3 = [{**p, 'weight': CFG[p['weight_key']]} for p in PARTS_3]
    w3 = {p['key']: p['weight'] for p in spec3}
    keys3 = [p['key'] for p in spec3]

    w10, w9, w7, w1 = load(10)['team_rankings'], load(9)['team_rankings'], load(7)['team_rankings'], load(1)['team_rankings']
    prepare(w10, keys3, w3)
    prepare(w1, keys3, w3)
    # Published order must equal the parts order (table correctness first).
    assert all(abs(t['_score'] - t['final_ranking_score']) < 1e-9 for t in w10), 'parts do not add up to TR+'

    states = {}
    base = {'season': 2024, 'week': 10, 'formula': {'source': 'ranking_service.DEFAULT_CONFIG', 'parts': len(spec3)}}
    board = board_rows(w10, w9)
    states['board-closed'] = {**base, 'board': board[:25], 'open': None}
    for key, name in [('row-open-mid', 'Iowa State'), ('row-open-first', 'Oregon'), ('row-open-last', 'UTEP')]:
        o = open_state(w10, w9, name, spec3, games_src, 10)
        idx = o['team']['rank'] - 1
        win = board[max(0, idx - 2): idx + 3]
        states[key] = {**base, 'board': win, 'open': o}

    # Negative-part state: the comparison against the team above, where at
    # least one part runs against the open team, isolated for the comp.
    neg = states['row-open-mid']['open']
    assert any(p['contribution'] < 0 for p in (neg['above'] or {}).get('parts', [])) or \
           any(p['contribution'] < 0 for p in (neg['below'] or {}).get('parts', []))
    states['negative-part'] = {**base, 'board': states['row-open-mid']['board'], 'open': neg, 'focus': 'negative'}

    # Early week: same team, week 1, one game, no previous week.
    o = open_state(w1, None, 'Iowa State', spec3, games_src, 1)
    idx = o['team']['rank'] - 1
    states['early-week'] = {**base, 'week': 1, 'board': board_rows(w1, None)[max(0, idx - 2): idx + 3], 'open': o}

    # 4-part (illustrative): heat value = TQ now minus TQ three weeks ago, on the
    # Elo scale (1500 + change). Re-ranked under the illustrative weights so the
    # neighbours are the real neighbours under that config.
    tq7 = {t['team_name']: t['team_quality_score'] for t in w7}
    w10_4 = json.loads(json.dumps([{k: v for k, v in t.items() if not k.startswith('_')} for t in w10]))
    heat = {t['team_name']: 1500 + t['team_quality_score'] - tq7.get(t['team_name'], t['team_quality_score']) for t in w10_4}
    spec4 = spec3[:1] + [{'key': 'heat', 'name': 'Heat', 'weight': ILLUSTRATIVE_4['heat']}] + spec3[1:]
    spec4 = [{**p, 'weight': ILLUSTRATIVE_4[p['key']]} for p in spec4]
    prepare(w10_4, [p['key'] for p in spec4], ILLUSTRATIVE_4, heat)
    w10_4.sort(key=lambda t: -t['_score'])
    o = open_state(w10_4, None, 'Iowa State', spec4, games_src, 10)
    for i, t in enumerate(w10_4):
        t['final_ranking_score'] = t['_score']
    idx = o['team']['rank'] - 1
    states['four-part'] = {**base, 'formula': {'source': 'fixture: illustrative Elo-plus-form weights (Michael pending)', 'parts': 4},
                           'board': board_rows(w10_4, None)[max(0, idx - 2): idx + 3], 'open': o, 'illustrative': True}

    states['loading'] = {**base, 'board': states['row-open-mid']['board'], 'open': {'team': neg['team'], 'status': 'loading'}}
    states['error'] = {**base, 'board': states['row-open-mid']['board'], 'open': {'team': neg['team'], 'status': 'error'}}
    states['season-unavailable'] = {**base, 'season': 2026, 'week': 8, 'board': None, 'open': None, 'status': 'unavailable'}
    states['sheet-390'] = {**states['row-open-mid'], 'sheet': True}
    states['share-card'] = {**base, 'open': neg}

    (HERE / 'fixtures.json').write_text(json.dumps(states, indent=1))
    for k, s in states.items():
        o = s.get('open') or {}
        t = o.get('team', {})
        print(k, t.get('rank'), t.get('team_name'), 'above' if o.get('above') else '-', 'below' if o.get('below') else '-', len(o.get('games', [])))


if __name__ == '__main__':
    main()
