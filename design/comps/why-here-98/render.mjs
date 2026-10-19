/**
 * Renders the #98 why-here HTML comps from data/fixtures.json + copy-slots.json.
 * - Parts come from the fixture's parts[] array (name, weight, value, contribution).
 *   Nothing here knows 0.80 / 0.15 / 0.05 or how many parts there are.
 * - Copy: 'locked' and 'existing' slots render verbatim, 'data' renders the field,
 *   'unlocked' slots are omitted (no element, no placeholder).
 * Output: states/<state>.html (self-contained apart from ../assets).
 */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FIX = JSON.parse(readFileSync(path.join(HERE, 'data/fixtures.json'), 'utf8'));
const SLOTS = new Map(JSON.parse(readFileSync(path.join(HERE, 'copy-slots.json'), 'utf8')).slots.map((s) => [s.id, s]));

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
/** Locked/existing slot → text; unlocked → '' (caller omits the element). */
function slot(id) {
  const s = SLOTS.get(id);
  if (!s) throw new Error(`unknown slot ${id}`);
  if (s.status === 'locked' || s.status === 'existing') return s.text;
  if (s.status === 'unlocked') return '';
  throw new Error(`slot ${id} is data; use the field`);
}
/** Element wrapper that disappears when the slot is unlocked. */
function slotEl(tag, id, cls = '') {
  const t = slot(id);
  return t ? `<${tag} class="${cls}" data-slot="${id}">${esc(t)}</${tag}>` : '';
}
const fmt1 = (n) => (Math.round(n * 10) / 10).toFixed(1);
const signed1 = (n) => {
  const r = Math.round(n * 10) / 10;
  return r > 0 ? `+${r.toFixed(1)}` : r < 0 ? `−${Math.abs(r).toFixed(1)}` : '0.0';
};
const pctOf = (w) => `${Math.round(w * 1000) / 10}%`;
const slug = (n) => n.toLowerCase().replace(/&/g, 'and').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');

function rankClass(r) {
  return r <= 12 ? 'rank-cfp' : r <= 25 ? 'rank-bubble' : 'rank-other';
}
function confClass(t) {
  return t === 'Power 4' ? 'badge-power4' : t === 'Group of 5' ? 'badge-g5' : 'badge-ind';
}
function delta(row) {
  if (row.prev_rank == null) return '<span class="delta-none" data-field="delta">—</span>';
  const d = row.prev_rank - row.rank;
  if (d > 0) return `<span class="delta-up" data-field="delta">+${d}</span>`;
  if (d < 0) return `<span class="delta-down" data-field="delta">${d}</span>`;
  return '<span class="delta-none" data-field="delta">—</span>';
}

const ICON = {
  chevron: '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  up: '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path d="M12 5l7 9H5z" fill="currentColor"/></svg>',
  down: '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path d="M12 19l7-9H5z" fill="currentColor"/></svg>',
  home: '<svg class="venue" viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" data-venue="home"><path d="M4 11l8-7 8 7v9h-5v-6H9v6H4z" fill="currentColor"/></svg>',
  away: '<svg class="venue" viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" data-venue="away"><path d="M5 12h11M12 6l6 6-6 6" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  neutral: '<svg class="venue" viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" data-venue="neutral"><circle cx="12" cy="12" r="7" fill="none" stroke="currentColor" stroke-width="2.5"/></svg>',
  star: '<svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true"><path d="M12 3l2.7 5.8 6.3.7-4.7 4.3 1.3 6.2L12 17l-5.6 3 1.3-6.2L3 9.5l6.3-.7z" fill="currentColor"/></svg>',
  share: '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M12 3v12M7 8l5-5 5 5M5 14v6h14v-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  close: '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round"/></svg>',
  alert: '<svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true"><path d="M12 3l10 18H2z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M12 10v5M12 18v.5" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round"/></svg>',
  retry: '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M20 12a8 8 0 1 1-2.3-5.7M20 4v5h-5" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  calendar: '<svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><path d="M3 10h18M8 3v4M16 3v4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
  schedule: '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M4 18l5-6 4 3 7-9" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  wins: '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M7 4h10v5a5 5 0 0 1-10 0zM12 14v4M8 20h8" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
};

function disc(rank) {
  return `<span class="rank-badge ${rankClass(rank)}" data-field="rank">${rank}</span>`;
}
function teamMark(t, size = 24) {
  // Logo slot: CFBD logo in the app; comps use the team colour disc fallback
  // that TeamRow.svelte already ships (no off-site request).
  return `<span class="team-mark" style="width:${size}px;height:${size}px;background:${t.color || '#6b7280'}" data-team-color aria-hidden="true">${esc(t.team_name.charAt(0))}</span>`;
}

/* ---------- board (unchanged except the toggle cell) ---------- */
function boardDesktop(state, openName) {
  const rows = state.board;
  const head = `<thead><tr>
    <th class="th w-16">${esc(slot('board.col.rank'))}</th><th class="th">${esc(slot('board.col.team'))}</th>
    <th class="th">${esc(slot('board.col.conference'))}</th><th class="th c">${esc(slot('board.col.record'))}</th>
    <th class="th c">${esc(slot('board.col.delta'))}</th><th class="th r">${esc(slot('brand.rating'))}</th>
    <th class="th toggle-col"><span class="sr-only"></span></th></tr></thead>`;
  const body = rows.map((r) => {
    const open = r.team_name === openName;
    const id = `team-${slug(r.team_name)}`;
    const bg = r.rank <= 12 ? 'row-cfp' : r.rank <= 25 ? 'row-bubble' : '';
    const tr = `<tr class="board-row ${bg} ${open ? 'is-open' : ''}" data-check="board-row">
      <td>${disc(r.rank)}</td>
      <td><div class="team-cell">${teamMark(r)}<a class="team-link" id="${id}" href="#">${esc(r.team_name)}</a></div></td>
      <td><span class="badge ${confClass(r.conference_type)}">${esc(r.conference)}</span></td>
      <td class="c ink-700">${esc(r.record)}</td>
      <td class="c small">${delta(r)}</td>
      <td class="r"><span class="score">${fmt1(r.final_ranking_score)}</span></td>
      <td class="toggle-cell"><button class="row-toggle" data-check="row-toggle" aria-expanded="${open}" aria-controls="why-${slug(r.team_name)}" aria-labelledby="${id}">${ICON.chevron}</button></td>
    </tr>`;
    return open ? tr + `<tr class="panel-row"><td colspan="7">${panel(state, 'desktop')}</td></tr>` : tr;
  }).join('');
  return `<table class="board" data-check="board"><colgroup><col style="width:72px"><col><col style="width:220px"><col style="width:110px"><col style="width:80px"><col style="width:120px"><col style="width:64px"></colgroup>${head}<tbody>${body}</tbody></table>`;
}

function boardMobile(state, openName, sheet) {
  return `<div class="m-board" data-check="board">${state.board.map((r) => {
    const open = r.team_name === openName && !sheet;
    const id = `m-team-${slug(r.team_name)}`;
    const card = `<div class="m-row ${r.rank <= 12 ? 'row-cfp' : ''} ${open ? 'is-open' : ''}" data-check="board-row">
      ${disc(r.rank)}${teamMark(r, 32)}
      <div class="m-info"><a class="team-link" id="${id}" href="#">${esc(r.team_name)}</a>
        <div class="m-meta"><span class="badge ${confClass(r.conference_type)}">${esc(r.conference)}</span><span class="ink-500 small">${esc(r.record)}</span></div></div>
      <div class="m-score"><div class="score lg">${fmt1(r.final_ranking_score)}</div><div class="ink-500 xs">${esc(slot('brand.rating'))}</div></div>
      <button class="row-toggle" data-check="row-toggle" aria-expanded="${r.team_name === openName}" aria-controls="why-${slug(r.team_name)}" aria-labelledby="${id}">${ICON.chevron}</button>
    </div>`;
    return open ? card + `<div class="m-panel">${panel(state, 'mobile')}</div>` : card;
  }).join('')}</div>`;
}

function boardCard(state, layout, openName, sheet = false) {
  const header = `<div class="card-head"><h3 class="card-title">${esc(slot('board.title'))}</h3>
    <div class="legend"><span><i class="sw sw-cfp"></i>${esc(slot('board.legend.cfp'))}</span><span><i class="sw sw-bubble"></i>${esc(slot('board.legend.bubble'))}</span></div></div>`;
  return `<section class="card">${header}${layout === 'desktop' ? boardDesktop(state, openName) : boardMobile(state, openName, sheet)}</section>`;
}

/* ---------- open panel ---------- */
function comparison(cmp, dir, scale, few) {
  if (!cmp) {
    const id = dir === 'above' ? 'why.no_above' : 'why.no_below';
    return `<div class="cmp cmp-empty" data-check="cmp-${dir}" data-empty="true">${slotEl('p', id, 'muted')}<span class="edge-mark" aria-hidden="true">${dir === 'above' ? ICON.up : ICON.down}</span></div>`;
  }
  const rows = cmp.parts.map((p) => {
    const w = Math.max(2, (Math.abs(p.contribution) / scale) * 50);
    const neg = p.contribution < 0;
    const label = p.name ? `<span class="part-label" data-part-label>${esc(p.name)}</span>` : `<span class="part-label" data-part-label data-slot-state="unlocked" data-slot="part.name.${p.key}"></span>`;
    return `<div class="part ${neg ? 'neg' : 'pos'} ${few ? 'few' : ''}" data-part="${p.key}" data-contribution="${p.contribution}" data-weight="${p.weight}">
      <div class="part-head">${label}<span class="part-weight" data-field="weight">${pctOf(p.weight)}</span></div>
      <div class="bar-track"><span class="axis"></span><span class="bar" style="${neg ? `right:50%;width:${w}%` : `left:50%;width:${w}%`}"></span></div>
      <span class="part-val ${neg ? 'v-neg' : 'v-pos'}" data-field="contribution">${signed1(p.contribution)}</span></div>`;
  }).join('');
  return `<div class="cmp" data-check="cmp-${dir}" data-gap="${cmp.gap}">
    <div class="cmp-head"><span class="dir ${dir}" aria-hidden="true">${dir === 'above' ? ICON.up : ICON.down}</span>${slotEl('span', dir === 'above' ? 'why.vs_above.caption' : 'why.vs_below.caption', 'muted')}
      ${disc(cmp.rank)}<span class="cmp-team">${esc(cmp.team_name)}</span><span class="cmp-gap ${cmp.gap < 0 ? 'v-neg' : 'v-pos'}" data-field="gap">${signed1(cmp.gap)}</span></div>
    <div class="parts">${rows}</div>
    <div class="sum" data-check="sum">${slotEl('span', 'why.sum.caption', 'muted')}<span class="sum-rule"></span><span class="sum-val ${cmp.gap < 0 ? 'v-neg' : 'v-pos'}" data-field="gap-total">${signed1(cmp.gap)}</span></div>
  </div>`;
}

function chips(games) {
  return `<div class="chips-wrap">${slotEl('h4', 'chips.heading', 'sub')}<ul class="chips" data-check="chips">${games.map((g) => {
    const tag = g.tag || 'none';
    return `<li class="chip chip-${tag} ${g.result === 'L' ? 'chip-loss' : ''}" data-check="chip" data-tag="${tag}" data-venue="${g.venue}">
      ${tag === 'quality_win' ? `<span class="tag-glyph">${ICON.star}</span>` : ''}<span class="res" data-field="result">${g.result}</span>
      ${ICON[g.venue]}<span class="opp">${esc(g.opponent)}</span>${g.opponent_rank != null ? `<span class="opp-rank" data-field="opponent_rank">#${g.opponent_rank}</span>` : ''}</li>`;
  }).join('')}</ul></div>`;
}

function stats(t) {
  return `<div class="stats">
    <div class="stat" data-check="stat-sos">${ICON.schedule}${slotEl('span', 'stat.sos.label', 'muted')}<span class="stat-val" data-field="sos_rank">#${t.sos_rank}</span></div>
    <div class="stat" data-check="stat-sov">${ICON.wins}${slotEl('span', 'stat.sov.label', 'muted')}<span class="stat-val" data-field="sov_rank">#${t.sov_rank}</span></div>
  </div>`;
}

function panelHeader(t, layout) {
  return `<div class="p-head">
    ${disc(t.rank)}<div class="p-title"><h2 class="p-team">${esc(t.team_name)}</h2>${slotEl('span', 'why.heading', 'muted')}</div>
    <div class="p-figs"><div class="fig"><span class="fig-val score" data-field="tr_plus">${fmt1(t.final_ranking_score)}</span><span class="fig-lab">${esc(slot('brand.rating'))}</span></div>
      <div class="fig"><span class="fig-val" data-field="record">${esc(t.record)}</span></div>
      <div class="fig">${delta(t)}${slotEl('span', 'why.delta.caption', 'muted')}</div></div>
    <button class="icon-btn" data-check="share-btn">${ICON.share}</button>
  </div>`;
}

function panel(state, layout) {
  const o = state.open;
  const t = o.team;
  const id = `why-${slug(t.team_name)}`;
  if (o.status === 'loading') {
    return `<div class="panel" id="${id}" data-check="why-panel" data-state="loading" aria-busy="true">${panelHeader(t, layout)}
      <div class="sk-grid">${[0, 1].map(() => `<div class="sk-cmp">${[0, 1, 2].map(() => '<div class="sk-row"><span class="sk sk-lab"></span><span class="sk sk-bar"></span></div>').join('')}</div>`).join('')}</div>
      <div class="sk-chips">${Array.from({ length: 6 }, () => '<span class="sk sk-chip"></span>').join('')}</div>${slotEl('span', 'loading.label', 'sr-only')}</div>`;
  }
  if (o.status === 'error') {
    return `<div class="panel" id="${id}" data-check="why-panel" data-state="error">${panelHeader(t, layout)}
      <div class="err" data-check="error"><span class="err-icon">${ICON.alert}</span>${slotEl('p', 'error.message', '')}
      <button class="icon-btn retry" data-check="retry">${ICON.retry}${slotEl('span', 'error.retry.label', '')}</button></div></div>`;
  }
  const all = [...(o.above?.parts || []), ...(o.below?.parts || [])].map((p) => Math.abs(p.contribution));
  const scale = Math.max(...all, 1);
  const few = t.games_played < 4;
  const focus = state.focus === 'negative';
  return `<div class="panel ${few ? 'is-few' : ''}" id="${id}" data-check="why-panel" data-state="${focus ? 'negative' : 'open'}" data-parts="${o.parts.length}">
    ${panelHeader(t, layout)}
    ${few ? `<div class="few-mark" data-check="few-games"><span class="few-dot"></span><span class="few-n" data-field="games_played">${t.games_played}</span>${slotEl('span', 'early.note', 'muted')}</div>` : ''}
    <div class="cmps">${comparison(o.above, 'above', scale, few)}${comparison(o.below, 'below', scale, few)}</div>
    ${slotEl('p', 'why.weight.caption', 'muted')}
    <div class="p-foot">${chips(o.games)}${stats(t)}</div>
  </div>`;
}

/* ---------- pages ---------- */
function page(title, body, opts = {}) {
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(title)}</title><link rel="stylesheet" href="../assets/fonts/fonts.css"><link rel="stylesheet" href="../comp.css"></head>
<body class="${opts.bodyClass || ''}" data-comp="${opts.state}" data-layout="${opts.layout}">${body}</body></html>`;
}

function stateBody(name, state, layout) {
  const openName = state.open?.team?.team_name || null;
  if (name === 'season-unavailable') {
    return `<main class="wrap"><section class="card"><div class="card-head"><h3 class="card-title">${esc(slot('board.title'))}</h3></div>
      <div class="empty" data-check="unavailable"><span class="empty-icon">${ICON.calendar}</span><span class="empty-season" data-field="season">${state.season}</span>${slotEl('p', 'unavailable.message', '')}</div></section></main>`;
  }
  if (name === 'negative-part') {
    return `<main class="wrap"><section class="card solo">${panel(state, layout)}</section></main>`;
  }
  if (name === 'sheet-390') {
    return `<main class="wrap">${boardCard(state, 'mobile', openName, true)}</main>
      <div class="scrim" aria-hidden="true"></div>
      <div class="sheet" role="dialog" aria-modal="true" aria-labelledby="sheet-team" data-check="sheet"><div class="grab"></div>
        <button class="icon-btn sheet-close" data-check="sheet-close">${ICON.close}${slotEl('span', 'sheet.close.label', 'sr-only')}</button>
        <span id="sheet-team" class="sr-only">${esc(openName)}</span>${panel(state, 'mobile')}</div>`;
  }
  return `<main class="wrap">${boardCard(state, layout, openName)}</main>`;
}

function shareCard(state) {
  const o = state.open;
  const t = o.team;
  const all = [...(o.above?.parts || []), ...(o.below?.parts || [])].map((p) => Math.abs(p.contribution));
  const scale = Math.max(...all, 1);
  const body = `<div class="share" data-check="share-card" data-url="${esc(t.url)}">
    <div class="sc-left">
      <div class="sc-rankline">${disc(t.rank)}${delta(t)}</div>
      <div class="sc-team" data-field="team_name">${esc(t.team_name)}</div>
      <div class="sc-figs"><span class="sc-score" data-field="tr_plus">${fmt1(t.final_ranking_score)}</span><span class="sc-lab">${esc(slot('brand.rating'))}</span><span class="sc-rec" data-field="record">${esc(t.record)}</span></div>
      ${slotEl('div', 'share.card.headline', 'sc-headline')}
    </div>
    <div class="sc-right">${comparison(o.above, 'above', scale, false)}${comparison(o.below, 'below', scale, false)}</div>
    <div class="sc-foot"><span class="sc-brand">${esc(slot('brand.name'))}</span><span class="sc-tag">${esc(slot('brand.tagline'))}</span><span class="sc-url" data-field="url">${esc(t.url.replace(/^https:\/\//, ''))}</span></div>
  </div>`;
  return page('share card', body, { bodyClass: 'share-body', state: 'share-card', layout: 'share' });
}

mkdirSync(path.join(HERE, 'states'), { recursive: true });
const written = [];
for (const [name, state] of Object.entries(FIX)) {
  if (name === 'share-card') {
    writeFileSync(path.join(HERE, 'states/share-card.html'), shareCard(state));
    written.push('share-card');
    continue;
  }
  for (const layout of ['desktop', 'mobile']) {
    if (name === 'sheet-390' && layout === 'desktop') continue;
    const file = `${name}-${layout === 'desktop' ? '1440' : '390'}.html`;
    writeFileSync(path.join(HERE, 'states', file), page(`#98 why here — ${name}`, stateBody(name, state, layout), { state: name, layout }));
    written.push(file);
  }
}
console.log(written.join('\n'));
