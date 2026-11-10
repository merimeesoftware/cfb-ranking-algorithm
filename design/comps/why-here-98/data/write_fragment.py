"""Writes manifest.fragment.json (PR #95 schema) with the design-render hashes."""
import hashlib, json, pathlib
H = pathlib.Path(__file__).resolve().parents[1]
t = json.loads((H / 'check-targets.json').read_text())
comps = []
for r in t['routes']:
    kind = 'board' if r['path'].startswith('/2024') else 'team'
    for w in r['widths']:
        ref = H / f'renders/row-open-mid-{w}.png'
        comps.append({'route': r['path'], 'width': w, 'file': f'renders/why-here-98-{kind}-{w}.png', 'sha256': '', 'signed_by': '', 'signoff': '', 'masks': [],
                      '_design_ref': {'file': f'why-here-98/renders/row-open-mid-{w}.png', 'sha256': hashlib.sha256(ref.read_bytes()).hexdigest()}})
frag = json.loads((H / 'manifest.fragment.json').read_text())
frag['routes'] = [{'path': r['path'], 'name': r['name']} for r in t['routes']]
frag['comps'] = comps
(H / 'manifest.fragment.json').write_text(json.dumps(frag, indent=1) + '\n')
