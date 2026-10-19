/**
 * Comp-side checker for the #98 why-here package (twin of the selectors the
 * #94 stills check will enforce on the built app; see check-targets.json).
 *
 * Guards (ids are stable; HANDOFF.md and the planted fixtures use them):
 *   parts-sum        Σ part contributions == gap (1e-9) and every shown number is the rounded data
 *   part-label       every [data-part] has a visible label; an unlocked label slot is "pending"
 *                    (allowed in comps, a failure with --strict, which is the app setting)
 *   overflow-390     no horizontal overflow at 390 (document and any element outside a scroller)
 *   tap-44           every interactive element is at least 44×44 CSS px
 *   focus-visible    the row toggle shows a visible outline when focused from the keyboard
 *   no-gambling      no bet/odds/market/spread/line/pick/lock/cover/projection in text, attributes or locked copy
 *   copy-slots       unlocked slots are omitted (no text); locked/existing slots are verbatim, templates filled
 *                    only from data (data-vars), attribute slots too (data-aslot); no placeholder text
 *   tokens           every computed colour is an allowed token (tokens.json); team data colours exempt
 *   share-card       share card is exactly 1200×675, PNGs are 1200×675, and it shows no unlocked text: every
 *                    visible string sits in a locked/existing [data-slot] or a [data-field] (the URL is unlocked → absent)
 *   data-driven      no hard-coded formula weights in the renderer; data-weight matches the fixture parts
 *   structure        each state has the selectors its role needs; every comparison renders the state's
 *                    parts_count (2 = how they look + Heat, 1 = how they look); Heat state shows Heat deciding
 *
 * Usage: node check-comps.mjs [--strict] [--json out.json] [file.html ...]
 * Exit 0 all pass, 1 any guard failed, 2 bad input.
 */
import { readFileSync, readdirSync, existsSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(path.join(HERE, '../../../scripts/visual/package.json'));
const { chromium } = require('playwright-core');

const args = process.argv.slice(2);
const STRICT = args.includes('--strict');
const jsonOut = args.includes('--json') ? args[args.indexOf('--json') + 1] : null;
const explicit = args.filter((a, i) => !a.startsWith('--') && args[i - 1] !== '--json');
const files = explicit.length
  ? explicit.map((f) => path.resolve(f))
  : readdirSync(path.join(HERE, 'states')).filter((f) => f.endsWith('.html')).sort().map((f) => path.join(HERE, 'states', f));

const SLOTS = JSON.parse(readFileSync(path.join(HERE, 'copy-slots.json'), 'utf8')).slots;
const SLOT = new Map(SLOTS.map((s) => [s.id, s]));
const TOKENS = JSON.parse(readFileSync(path.join(HERE, 'tokens.json'), 'utf8'));
const ALLOWED = new Set(
  [TOKENS.identity, TOKENS.tailwind_main, TOKENS.board_existing, Object.fromEntries((TOKENS.proposals || []).map((p) => [p.name, p.hex]))]
    .flatMap((o) => Object.values(o))
    .map((h) => h.toLowerCase())
);
const FIXTURES = JSON.parse(readFileSync(path.join(HERE, 'data/fixtures.json'), 'utf8'));
export const GAMBLING_RE = /\b(bet|bets|betting|bettor|bettors|odds|market|markets|spread|spreads|line|lines|pick|picks|lock|locks|lock[\s-]+of[\s-]+the[\s-]+week|cover|covers|covered|projection|projections|projected)\b/i;
export function fillTemplate(text, vars) {
  return text.replace(/\{(\w+)\}/g, (m, k) => (vars && vars[k] !== undefined && vars[k] !== null ? String(vars[k]) : m));
}
const PLACEHOLDER_RE = /\b(lorem|ipsum|placeholder|tbd|todo|xxx)\b|\{\{|\[\[/i;
// Old published weights (0.80/0.15/0.05) and the illustrative ordering weights (0.9/0.1) must come from data.
const WEIGHT_LITERAL_RE = /(?<![\d.])0?\.(80|15|05|9|90|1|10)(?![\w.])|(?<![\d.])(80|15|5)\s*%/;

function hexOf(rgb) {
  const m = rgb.match(/rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)(?:[,\s/]+([\d.]+))?/);
  if (!m) return null;
  const a = m[4] === undefined ? 1 : Number(m[4]);
  return { hex: '#' + [m[1], m[2], m[3]].map((n) => Number(n).toString(16).padStart(2, '0')).join(''), a };
}

function widthsFor(file) {
  const b = path.basename(file);
  if (b.startsWith('share-card')) return [{ w: 1200, h: 675 }];
  if (/-390\.html$/.test(b)) return [{ w: 390, h: 844 }];
  if (/-1440\.html$/.test(b)) return [{ w: 1440, h: 900 }];
  return [{ w: 390, h: 844 }, { w: 1440, h: 900 }];
}

async function checkPage(page, file, vp) {
  const res = [];
  const add = (guard, ok, detail = '', extra = {}) => res.push({ guard, ok, detail, width: vp.w, ...extra });
  const meta = await page.evaluate(() => ({ comp: document.body.dataset.comp || '', layout: document.body.dataset.layout || '' }));

  // parts-sum
  const sums = await page.evaluate(() => [...document.querySelectorAll('[data-gap]')].map((g) => ({
    gap: Number(g.dataset.gap),
    parts: [...g.querySelectorAll('[data-part]')].map((p) => ({
      c: Number(p.dataset.contribution),
      shown: p.querySelector('[data-field=contribution]')?.textContent.trim() || '',
    })),
    shownGap: g.querySelector('[data-field=gap]')?.textContent.trim() || '',
    shownTotal: g.querySelector('[data-field=gap-total]')?.textContent.trim() || '',
  })));
  const num = (s) => Number(s.replace('−', '-').replace('+', ''));
  const r1 = (n) => Math.round(n * 10) / 10;
  for (const s of sums) {
    const total = s.parts.reduce((a, p) => a + p.c, 0);
    const okSum = s.parts.length > 0 && Math.abs(total - s.gap) <= 1e-9;
    const okShown = s.parts.every((p) => Math.abs(num(p.shown) - r1(p.c)) < 1e-9) && Math.abs(num(s.shownGap) - r1(s.gap)) < 1e-9 && Math.abs(num(s.shownTotal) - r1(s.gap)) < 1e-9;
    add('parts-sum', okSum && okShown, okSum ? (okShown ? `${s.parts.length} parts = ${s.gap.toFixed(6)}` : 'shown numbers are not the rounded data') : `Σ parts ${total} ≠ gap ${s.gap}`);
  }

  // part-label
  const labels = await page.evaluate(() => [...document.querySelectorAll('[data-part]')].map((p) => {
    const l = p.querySelector('[data-part-label]');
    return { key: p.dataset.part, text: l ? l.innerText.trim() : null, pending: l?.dataset.slotState === 'unlocked', slot: l?.dataset.slot || null };
  }));
  for (const l of labels) {
    if (l.text) add('part-label', true, `${l.key}: ${l.text}`);
    else if (l.pending && SLOT.get(l.slot)?.status === 'unlocked') add('part-label', !STRICT, `${l.key}: label pending (${l.slot})`, { pending: true });
    else add('part-label', false, `${l.key}: no label`);
  }

  // overflow-390
  if (vp.w === 390) {
    const o = await page.evaluate(() => {
      const vw = document.documentElement.clientWidth;
      const doc = document.documentElement.scrollWidth;
      const clipped = (el) => {
        for (let a = el.parentElement; a && a !== document.body; a = a.parentElement) {
          const ox = getComputedStyle(a).overflowX;
          if (ox === 'auto' || ox === 'scroll' || ox === 'hidden' || ox === 'clip') return true;
        }
        return false;
      };
      const bad = [...document.body.querySelectorAll('*')].filter((el) => {
        const r = el.getBoundingClientRect();
        return r.width > 0 && (r.right > vw + 0.5 || r.left < -0.5) && !clipped(el) && getComputedStyle(el).position !== 'fixed';
      }).slice(0, 3).map((el) => el.tagName.toLowerCase() + (el.className ? '.' + String(el.className).split(' ')[0] : ''));
      return { vw, doc, bad };
    });
    add('overflow-390', o.doc <= o.vw && o.bad.length === 0, o.doc > o.vw ? `scrollWidth ${o.doc} > ${o.vw}` : o.bad.length ? `overflows: ${o.bad.join(', ')}` : `scrollWidth ${o.doc} ≤ ${o.vw}`);
  }

  // tap-44
  const taps = await page.evaluate(() => [...document.querySelectorAll('button, a[href], [role=button], input, select, textarea, [tabindex]:not([tabindex="-1"])')]
    .map((el) => { const r = el.getBoundingClientRect(); return { el: el.tagName.toLowerCase() + (el.dataset.check ? `[${el.dataset.check}]` : el.className ? '.' + String(el.className).split(' ')[0] : ''), w: r.width, h: r.height, vis: r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden' }; })
    .filter((t) => t.vis));
  const small = taps.filter((t) => t.w < 44 - 0.01 || t.h < 44 - 0.01);
  if (taps.length) add('tap-44', small.length === 0, small.length ? small.slice(0, 3).map((t) => `${t.el} ${t.w.toFixed(0)}×${t.h.toFixed(0)}`).join(', ') : `${taps.length} targets ≥ 44`);

  // focus-visible on the row toggle (keyboard focus, not .focus())
  const hasToggle = await page.locator('[data-check=row-toggle]').count();
  if (hasToggle) {
    await page.mouse.click(1, 1);
    let found = null;
    for (let i = 0; i < 80 && !found; i++) {
      await page.keyboard.press('Tab');
      found = await page.evaluate(() => {
        const a = document.activeElement;
        if (!a || a.dataset.check !== 'row-toggle') return null;
        const cs = getComputedStyle(a);
        return { fv: a.matches(':focus-visible'), style: cs.outlineStyle, width: parseFloat(cs.outlineWidth), shadow: cs.boxShadow };
      });
    }
    const ok = !!found && found.fv && ((found.style !== 'none' && found.width >= 2) || (found.shadow && found.shadow !== 'none'));
    add('focus-visible', ok, found ? `outline ${found.style} ${found.width}px` : 'row toggle never received keyboard focus');
    await page.evaluate(() => document.activeElement && document.activeElement.blur());
  }

  // no-gambling (text + attributes + title)
  const text = await page.evaluate(() => {
    const attrs = [...document.querySelectorAll('*')].flatMap((el) => ['alt', 'aria-label', 'aria-description', 'title', 'placeholder', 'content', 'data-url', 'value'].map((a) => el.getAttribute(a)).filter(Boolean));
    return [document.title, document.body.innerText, ...attrs].join('\n');
  });
  const g = text.match(GAMBLING_RE);
  add('no-gambling', !g, g ? `found "${g[0]}"` : 'clean');

  // copy-slots
  const slotEls = await page.evaluate(() => [
    ...[...document.querySelectorAll('[data-slot]')].map((el) => ({ id: el.dataset.slot, text: el.textContent.trim(), vars: el.dataset.vars ? JSON.parse(el.dataset.vars) : null, where: 'text' })),
    ...[...document.querySelectorAll('[data-aslot]')].flatMap((el) => el.dataset.aslot.split(';').map((pair) => {
      const [attr, id] = pair.split(':');
      return { id, text: (el.getAttribute(attr) || '').trim(), vars: el.dataset.avars ? JSON.parse(el.dataset.avars) : null, where: attr };
    })),
  ]);
  const slotProblems = [];
  for (const s of slotEls) {
    const def = SLOT.get(s.id);
    if (!def) { slotProblems.push(`unknown slot ${s.id}`); continue; }
    if (def.status === 'unlocked') { if (s.text) slotProblems.push(`unlocked ${s.id} shows "${s.text}"`); continue; }
    if (def.status !== 'locked' && def.status !== 'existing') continue;
    const want = fillTemplate(def.text, s.vars);
    if (/\{\w+\}/.test(want)) slotProblems.push(`${s.id} (${s.where}) template not filled from data`);
    else if (s.text !== want) slotProblems.push(`${s.id} (${s.where}) not verbatim: "${s.text}" ≠ "${want}"`);
  }
  const ph = text.match(PLACEHOLDER_RE);
  if (ph) slotProblems.push(`placeholder text "${ph[0]}"`);
  add('copy-slots', slotProblems.length === 0, slotProblems.join('; ') || `${slotEls.length} slot elements ok`);

  // tokens
  const colours = await page.evaluate(() => {
    const out = [];
    for (const el of document.querySelectorAll('*')) {
      if (el.closest('[data-team-color]')) continue;
      const cs = getComputedStyle(el);
      const props = ['color', 'backgroundColor', 'borderTopColor', 'borderRightColor', 'borderBottomColor', 'borderLeftColor', 'outlineColor'];
      for (const p of props) {
        if (p.startsWith('border') && cs[p.replace('Color', 'Width')] === '0px') continue;
        if (p === 'outlineColor' && cs.outlineStyle === 'none') continue;
        out.push(cs[p]);
      }
      const bi = cs.backgroundImage;
      if (bi && bi !== 'none') out.push(...(bi.match(/rgba?\([^)]*\)/g) || []));
      if (el instanceof SVGGeometryElement) for (const p of ['fill', 'stroke']) if (cs[p] && cs[p].startsWith('rgb')) out.push(cs[p]);
    }
    return [...new Set(out)];
  });
  const off = colours.map(hexOf).filter((c) => c && c.a > 0 && !ALLOWED.has(c.hex));
  add('tokens', off.length === 0, off.length ? `off-token ${[...new Set(off.map((c) => c.hex))].join(', ')}` : `${colours.length} colours on token`);

  // share-card: exact size + no unlocked text (every visible string is locked/existing copy or data)
  if (meta.comp.startsWith('share-card') || (await page.locator('[data-check=share-card]').count())) {
    const s = await page.evaluate(() => {
      const c = document.querySelector('[data-check=share-card]');
      const r = c.getBoundingClientRect();
      const stray = [];
      const slotsUsed = [];
      const walker = document.createTreeWalker(c, NodeFilter.SHOW_TEXT);
      for (let n = walker.nextNode(); n; n = walker.nextNode()) {
        const t = n.textContent.trim();
        if (!t) continue;
        const el = n.parentElement;
        if (el.closest('.sr-only')) continue;
        const owner = el.closest('[data-slot],[data-field]');
        if (!owner || !c.contains(owner)) stray.push(t);
        else if (owner.dataset.slot) slotsUsed.push({ id: owner.dataset.slot, t });
      }
      return { w: r.width, h: r.height, sw: document.documentElement.scrollWidth, sh: document.documentElement.scrollHeight, stray, slotsUsed };
    });
    const unlocked = s.slotsUsed.filter((u) => SLOT.get(u.id)?.status !== 'locked' && SLOT.get(u.id)?.status !== 'existing');
    const okSize = s.w === 1200 && s.h === 675 && s.sw === 1200 && s.sh === 675;
    const okText = s.stray.length === 0 && unlocked.length === 0;
    add('share-card', okSize && okText, `${s.w}×${s.h} (doc ${s.sw}×${s.sh})` + (okText ? `; ${s.slotsUsed.length} locked strings, no unlocked text` : `; unlocked text: ${[...s.stray, ...unlocked.map((u) => `${u.id}="${u.t}"`)].slice(0, 3).join(' | ')}`));
  }

  // data-driven: rendered weights must equal the fixture's parts for this state
  const state = FIXTURES[meta.comp];
  if (state?.open?.parts) {
    const ws = await page.evaluate(() => [...new Set([...document.querySelectorAll('[data-part]')].map((p) => p.dataset.part + '=' + p.dataset.weight))]);
    const want = state.open.parts.map((p) => `${p.key}=${p.weight}`);
    const ok = ws.length === 0 || ws.every((w) => want.includes(w));
    add('data-driven', ok, ok ? `${want.length} parts from fixture` : `weights ${ws.join(',')} not in fixture ${want.join(',')}`);
  }

  // structure
  const open = ['why-panel', 'cmp-above', 'cmp-below', 'chips', 'context', 'stat-sos', 'stat-sov', 'ctx-resume'];
  const need = {
    'board-closed': ['board', 'board-row', 'row-toggle', 'resume-cell'],
    'row-open-mid': ['board', 'row-toggle', 'resume-cell', 'share-btn', 'recent', ...open],
    'row-open-mid-1part': ['board', 'row-toggle', 'resume-cell', 'share-btn', ...open],
    'row-open-first': open,
    'row-open-last': open,
    'negative-part': ['why-panel', 'cmp-above', 'context'],
    'negative-part-1part': ['why-panel', 'cmp-above', 'context'],
    heat: [...open, 'recent'],
    'early-week': ['why-panel', 'few-games', 'chips', 'context'],
    loading: ['why-panel'],
    error: ['why-panel', 'error', 'retry'],
    'season-unavailable': ['unavailable'],
    'sheet-390': ['sheet', 'sheet-close', 'why-panel', 'context'],
    'share-card': ['share-card'],
    'share-card-1part': ['share-card'],
  }[meta.comp];
  if (need) {
    const missing = [];
    for (const n of need) if (!(await page.locator(`[data-check="${n}"]`).count())) missing.push(n);
    const extra = [];
    if (meta.comp === 'row-open-first' && !(await page.locator('[data-check=cmp-above][data-empty=true]').count())) extra.push('#1 must have an empty above slot');
    if (meta.comp === 'row-open-last' && !(await page.locator('[data-check=cmp-below][data-empty=true]').count())) extra.push('last team must have an empty below slot');
    if (meta.comp.startsWith('negative-part') && !(await page.locator('[data-part].neg').count())) extra.push('no negative part rendered');
    const want = state?.parts_count;
    if (want) {
      const counts = await page.evaluate(() => [...document.querySelectorAll('[data-gap]')].map((g) => g.querySelectorAll('[data-part]').length));
      if (counts.some((n) => n !== want)) extra.push(`comparisons render ${counts.join('/')} parts, state needs ${want}`);
      const ctx = await page.evaluate(() => [...document.querySelectorAll('[data-gap] [data-check^=stat-], [data-gap] [data-check=ctx-resume]')].length);
      if (ctx) extra.push('context (resume/schedule/quality of wins) is inside the gap');
    }
    if (meta.comp === 'heat') {
      const decided = await page.evaluate(() => [...document.querySelectorAll('[data-gap]')].some((g) => {
        const s = g.querySelector('[data-part=strength]');
        return s && Number(s.dataset.contribution) * Number(g.dataset.gap) < 0 && g.querySelector('[data-part=heat]');
      }));
      if (!decided) extra.push('Heat state must show a comparison Heat decides');
    }
    add('structure', missing.length === 0 && !extra.length, missing.length ? `missing ${missing.join(', ')}` : extra.join('; ') || `${need.length} selectors present${want ? `, ${want}-part` : ''}`);
  }
  return res;
}

function pngSize(file) {
  const b = readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}

export function sourceGuard(srcFiles) {
  const hits = [];
  for (const f of srcFiles) {
    readFileSync(f, 'utf8').split('\n').forEach((line, i) => {
      if (/^\s*(\/\/|\*|\/\*)/.test(line)) return; // comments may explain the rule
      if (WEIGHT_LITERAL_RE.test(line)) hits.push(`${path.basename(f)}:${i + 1}`);
    });
  }
  return hits;
}

async function main() {
  for (const f of files) if (!existsSync(f)) { console.error(`missing ${f}`); process.exit(2); }
  const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || '/usr/bin/google-chrome' });
  const results = [];
  for (const file of files) {
    for (const vp of widthsFor(file)) {
      const page = await browser.newPage({ viewport: { width: vp.w, height: vp.h } });
      await page.goto(pathToFileURL(file).href);
      await page.evaluate(() => document.fonts.ready);
      for (const r of await checkPage(page, file, vp)) results.push({ file: path.relative(HERE, file), ...r });
      await page.close();
    }
  }
  await browser.close();

  // package-level guards (only for the real package run)
  if (!explicit.length) {
    const hits = sourceGuard([path.join(HERE, 'render.mjs'), path.join(HERE, 'comp.css')]);
    results.push({ file: 'render.mjs, comp.css', guard: 'data-driven', ok: hits.length === 0, detail: hits.length ? `weight literal at ${hits.join(', ')}` : 'no weight literals' });
    for (const name of ['share-card-1200x675.png', 'share-card-1part-1200x675.png']) {
      const share = path.join(HERE, 'renders', name);
      const s = existsSync(share) ? pngSize(share) : { w: 0, h: 0 };
      results.push({ file: `renders/${name}`, guard: 'share-card', ok: s.w === 1200 && s.h === 675, detail: `png ${s.w}×${s.h}` });
    }
    const locked = SLOTS.filter((s) => s.text).map((s) => s.text).join('\n');
    const g = locked.match(GAMBLING_RE);
    results.push({ file: 'copy-slots.json', guard: 'no-gambling', ok: !g, detail: g ? `found "${g[0]}"` : 'locked/existing copy clean' });
  }

  const failed = results.filter((r) => !r.ok);
  const byGuard = {};
  for (const r of results) {
    byGuard[r.guard] ??= { pass: 0, fail: 0, pending: 0 };
    byGuard[r.guard][r.ok ? 'pass' : 'fail']++;
    if (r.pending) byGuard[r.guard].pending++;
  }
  const report = { strict: STRICT, files: files.length, checks: results.length, passed: results.length - failed.length, failed: failed.length, byGuard, failures: failed, results };
  if (jsonOut) writeFileSync(jsonOut, JSON.stringify(report, null, 1));
  for (const [g, c] of Object.entries(byGuard)) console.log(`${c.fail ? '✗' : '✓'} ${g.padEnd(14)} pass ${c.pass}  fail ${c.fail}${c.pending ? `  (pending labels ${c.pending})` : ''}`);
  for (const f of failed.slice(0, 20)) console.log(`  FAIL ${f.guard} ${f.file}@${f.width ?? ''}: ${f.detail}`);
  console.log(`${report.passed}/${report.checks} checks passed across ${files.length} files${STRICT ? ' (strict)' : ''}`);
  process.exit(failed.length ? 1 : 0);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main();
