"""Writes the planted fixtures for check-comps.mjs. Each file breaks exactly one
guard; base.html breaks none. Re-run after editing; the HTML files are committed."""
import pathlib
HERE = pathlib.Path(__file__).parent
CHEV = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2"/></svg>'

def page(extra_body='', extra_head='', comp='planted', parts=None, gap='-1.5'):
    parts = parts if parts is not None else [
        ('strength', 'how they look', '1', '+1.0', '<span class="part-label" data-part-label data-slot="part.name.strength">how they look</span>'),
        ('heat', 'Heat', '-2.5', '−2.5', '<span class="part-label" data-part-label data-slot="part.name.heat">Heat</span>'),
    ]
    rows = ''.join(f'<div class="part {"neg" if c.startswith("-") else "pos"}" data-part="{k}" data-contribution="{c}" data-weight="0.5"><div class="part-head">{label}</div><div class="bar-track"><span class="axis"></span></div><span class="part-val" data-field="contribution">{shown}</span></div>' for k, n, c, shown, label in parts)
    cmp = f'<div class="cmp" data-gap="{gap}"><div class="cmp-head"><span class="cmp-team">Ole Miss</span><span class="cmp-gap v-neg" data-field="gap">−1.5</span></div><div class="parts">{rows}</div><div class="sum"><span class="sum-val v-neg" data-field="gap-total">−1.5</span></div></div>' if parts else ''
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>planted</title>
<link rel="stylesheet" href="../assets/fonts/fonts.css"><link rel="stylesheet" href="../comp.css">{extra_head}</head>
<body data-comp="{comp}" data-layout="mobile"><main class="wrap"><div class="panel">
<div class="p-head"><button class="row-toggle" data-check="row-toggle" aria-expanded="true" aria-labelledby="t">{CHEV}</button><a id="t" class="team-link" href="#">Iowa State</a></div>
{cmp}{extra_body}</div></main></body></html>
'''

base_parts = None
SC = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>planted</title>
<link rel="stylesheet" href="../comp.css"></head><body class="share-body" data-comp="planted" data-layout="share">
<div class="share" data-check="share-card"{style}><div class="sc-foot"><span class="sc-brand" data-slot="brand.name">True Rankings</span><span class="sc-tag" data-slot="brand.tagline">How good they actually are.</span>{extra}</div></div></body></html>
'''
files = {
    'base.html': page(),
    'parts-sum.html': page(parts=[
        ('a', '', '1', '+1.0', '<span class="part-label" data-part-label>how they look</span>'),
        ('b', '', '-2.4', '−2.4', '<span class="part-label" data-part-label>Heat</span>')]),
    'part-label.html': page(parts=[
        ('a', '', '1', '+1.0', '<span class="part-label" data-part-label></span>'),
        ('b', '', '-2.5', '−2.5', '<span class="part-label" data-part-label>Heat</span>')]),
    'overflow-390.html': page('<div style="width:600px;height:8px;background:#1a3d2e"></div>'),
    'tap-44.html': page(f'<button class="icon-btn" style="min-width:30px;width:30px;height:30px;padding:0">{CHEV}</button>'),
    'focus-visible.html': page(extra_head='<style>.row-toggle:focus-visible{outline:none}</style>'),
    'no-gambling.html': page('<p class="muted">Best bet</p>'),
    'copy-slots-unlocked.html': page('<span class="muted" data-slot="share.card.url">{SITE_URL}/teams/iowa-state</span>'),
    'copy-slots-template.html': page('<h2 class="p-team" data-slot="why.heading" data-vars=\'{"Team":"Iowa State","rank":19}\'>Why Iowa State is #1</h2>'),
    'copy-slots-placeholder.html': page('<p class="muted">Lorem ipsum</p>'),
    'tokens.html': page('<div style="height:8px;background:#3b82f6"></div>'),
    'structure.html': page(comp='row-open-first', parts=[]),
    'share-card-wrong-size.html': SC.format(style=' style="height:630px"', extra=''),
    'share-card-unlocked-text.html': SC.format(style='', extra='<span class="sc-brand">{SITE_URL}</span>'),
}
for name, html in files.items():
    (HERE / name).write_text(html)
(HERE / 'hardcoded-weight.mjs').write_text("// planted: a renderer that hard-codes the formula weights\nexport const parts = [{ key: 'strength', weight: 0.80 }, { key: 'resume', weight: 0.15 }, { key: 'league', weight: 0.05 }];\n")
print('\n'.join(files) + '\nhardcoded-weight.mjs')
(HERE / 'hardcoded-weight-2part.mjs').write_text("// planted: a renderer that hard-codes the illustrative ordering weights\nexport const parts = [{ key: 'strength', weight: 0.9 }, { key: 'heat', weight: 0.1 }];\n")
print('hardcoded-weight-2part.mjs')
