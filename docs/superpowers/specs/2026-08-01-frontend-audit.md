# CFB Ranking System — Frontend Audit

**Date:** 2026-08-01  
**Scope:** `/workspace/frontend` (SvelteKit 2, Tailwind 3, static adapter, SPA mode)  
**Auditor lens:** Impeccable design principles — distinctive craft over generic AI UI, interaction completeness, accessibility, and performance discipline.

---

## Executive Summary

The frontend is a functional single-page rankings app with a clear component hierarchy, client-side filtering, and rich team/conference detail modals. Type-checking passes (`npm run check`), and mobile/desktop responsive patterns are present.

However, the data layer has **two competing API implementations** (only one is wired), several **store capabilities are implemented but not exposed in UI**, and multiple **navigation/data bugs** reduce trust (broken `/about` link, missing logos, FCS view likely empty). Visually, the app follows a familiar “Tailwind dashboard” pattern—Inter, blue primary, inline Heroicons, gray cards—which reads competent but not distinctive for a sports analytics product.

**Highest-impact fixes:** consolidate API layer, request `all_divisions=true`, map logo fields, fix broken links, add URL state for shareable rankings, and upgrade tab/modal accessibility.

---

## 1. Architecture Summary

### 1.1 Stack & deployment model

| Layer | Technology | Notes |
|-------|------------|-------|
| Framework | SvelteKit 2 + Svelte 4 | `ssr: false`, `prerender: true` → static SPA |
| Styling | Tailwind 3 + `@tailwindcss/forms` | `darkMode: 'class'`, custom `primary` palette |
| Adapter | `@sveltejs/adapter-static` | Output to `build/`, SPA fallback `index.html` |
| State | Svelte writable/derived stores | No external state library |
| API | Native `fetch` | Lives inside store, not separate service module |
| Tooling | ESLint 9, Prettier, svelte-check | No unit/E2E tests in frontend |

### 1.2 Directory & data flow

```
src/
├── app.html / app.css          # Shell, global styles, Inter via Google Fonts
├── routes/
│   ├── +layout.svelte          # Header, Footer, theme bootstrap
│   ├── +layout.ts              # prerender=true, ssr=false
│   ├── +page.svelte            # Main rankings view (orchestrator)
│   └── methodology/+page.svelte
└── lib/
    ├── api.ts                  # ⚠️ UNUSED alternate API client
    ├── types.ts                # Team, Conference, FilterState, etc.
    ├── stores/
    │   ├── rankings.ts         # ✅ Active: fetch, filter, derived lists
    │   └── theme.ts            # light/dark/system + localStorage
    └── components/
        ├── FilterControls.svelte
        ├── RankingsTable.svelte / TeamRow.svelte / TeamDetailModal.svelte
        ├── ConferenceTable.svelte / ConferenceDetailModal.svelte
        ├── Header.svelte / Footer.svelte / LoadingSpinner.svelte
```

**Runtime flow (happy path):**

1. `+page.svelte` `onMount` → `fetchRankings(year, week)` from `rankings.ts`.
2. Store sets `loading`, fetches `${API_BASE}/rankings?year=&week=` (no `all_divisions`).
3. Response mapped to `teams` / `conferences` writables; `filterState` updated.
4. `filteredTeams` / `filteredConferences` derived stores apply view (FBS/P4/G5/FCS), conference, and search filters client-side.
5. UI renders tables; row click opens detail modals with comparison context.

### 1.3 API configuration split (critical)

Two incompatible base-URL strategies exist:

| File | Dev URL | Prod URL | Query params |
|------|---------|----------|--------------|
| `stores/rankings.ts` (active) | `window.location.hostname === 'localhost'` → `:5001` | Hardcoded Render URL | `year`, `week` only |
| `lib/api.ts` (dead) | `import.meta.env.DEV` → `:5001` | `VITE_API_URL` or Render fallback | `all_divisions=true`; includes `/weeks` helper |

**Only `rankings.ts` is imported.** `lib/api.ts` is never referenced. `VITE_API_URL`, `fetchAvailableWeeks`, and `checkApiHealth` are dead code.

### 1.4 State model

**Writables:** `teams`, `conferences`, `loading`, `error`, `filterState`, `availableYears`, `maxWeek`.

**Derived:** `filteredTeams`, `filteredConferences` — filter by `view`, `conferenceFilter`, `searchQuery`.

**FilterState fields vs UI exposure:**

| Field | Store support | UI wired |
|-------|---------------|----------|
| `year` / `week` | ✅ | ✅ FilterControls selects |
| `view` (fbs/p4/g5/fcs) | ✅ | ✅ FilterControls tabs |
| `searchQuery` | ✅ | ❌ No search input |
| `conferenceFilter` | ✅ | ❌ No conference picker |

**Helpers never called from UI:** `setSearchQuery`, `setConferenceFilter`, `clearFilters`.

### 1.5 Routing & pages

| Route | Status |
|-------|--------|
| `/` | Rankings home |
| `/methodology` | Long-form algorithm docs (V5) |
| `/about` | **Missing** — linked from Footer |

### 1.6 Dependencies vs usage

- `@iconify/svelte` — listed in `package.json`, **zero imports** in `src/`.
- Inline SVG icons duplicated across Header, FilterControls, tables, modals (~15+ copies of similar path data).

---

## 2. Known Issues

| ID | Issue | File(s) | Impact |
|----|-------|---------|--------|
| KI-01 | Duplicate API layer; active store bypasses `lib/api.ts` | `lib/api.ts`, `lib/stores/rankings.ts` | **High** — config drift, untested code path, no `VITE_API_URL` in prod |
| KI-02 | Active fetch omits `all_divisions=true` | `lib/stores/rankings.ts:142` | **High** — FCS view and cross-division data likely incomplete/empty |
| KI-03 | Logo/color fields not mapped in active fetch | `lib/stores/rankings.ts:156-195` | **High** — UI always falls back to initials avatars despite backend providing logos |
| KI-04 | `/weeks` endpoint referenced but does not exist on backend | `lib/api.ts:33-43`, `app.py` | **Medium** — dead helper; `maxWeek` stuck at 15 |
| KI-05 | Broken `/about` link | `lib/components/Footer.svelte:14` | **Medium** — 404 in SPA, erodes trust |
| KI-06 | Placeholder GitHub URL (`https://github.com`) | `lib/components/Footer.svelte:16-17` | **Medium** — broken external link |
| KI-07 | Search & conference filter implemented in store, no UI | `rankings.ts`, all components | **Medium** — dead feature surface, confusing for maintainers |
| KI-08 | Year/week change fires fetch immediately *and* redundant “Update Rankings” button | `+page.svelte`, `FilterControls.svelte` | **Medium** — double-fetch UX confusion |
| KI-09 | Conference modal rank uses slice index, not global rank | `ConferenceTable.svelte:83-84`, `+page.svelte:59-62` | **Medium** — wrong rank when “Top 7” collapsed |
| KI-10 | `api.ts` maps fewer Team fields (no resume metrics, game details) | `lib/api.ts:49-73` | **Low** (dead code) — would break modals if switched without merge |
| KI-11 | `parseWinPct` duplicated | `rankings.ts`, `api.ts` | **Low** — maintenance hazard |
| KI-12 | `conferenceColors` map duplicated | `ConferenceTable.svelte`, `ConferenceDetailModal.svelte` | **Low** — drift risk |
| KI-13 | `footerOnly` prop never used | `Footer.svelte` | **Low** — dead API |
| KI-14 | No favicon | `app.html:8` | **Low** — unprofessional tab chrome |
| KI-15 | `@iconify/svelte` unused dependency | `package.json` | **Low** — bundle/install noise |
| KI-16 | No URL query sync for filters | `+page.svelte`, `rankings.ts` | **Medium** — rankings not shareable/bookmarkable |
| KI-17 | `getCurrentSeasonWeek()` client heuristic | `rankings.ts:19-49` | **Medium** — wrong default week in edge months |
| KI-18 | `console.log` in dead API module | `lib/api.ts:15` | **Low** — noise if ever activated |
| KI-19 | Header nav omits Methodology on mobile menu parity | `Header.svelte` vs `Footer.svelte` | **Low** — Footer has About/Methodology; Header only Rankings/Methodology |
| KI-20 | Team modal rank uses `teams.indexOf` on filtered list | `RankingsTable.svelte:173` | **Low** — correct within filtered set; breaks if sort order changes |

---

## 3. UX / A11y / Performance Findings (Impeccable-Style Audit)

### 3.1 Visual identity & anti-patterns

**Finding: Generic “AI dashboard” aesthetic**

The app uses Inter (Google Fonts CDN), Tailwind default blue `primary-600`, gray-50 page background, rounded-xl cards, and inline Heroicons— a combination common in generated admin UIs. For a college football rankings product, this undersells the domain: no team textures, no conference identity system beyond a hardcoded color map, no typographic contrast between data-dense tables and narrative content.

| Signal | Location | Impeccable guidance |
|--------|----------|---------------------|
| Inter + blue primary | `app.css:1`, `tailwind.config.js` | Choose a distinctive display/data pairing (e.g., condensed headline + tabular nums body) |
| Generic checkmark logo | `Header.svelte:21-23` | Use mark tied to sport/analytics brand |
| Emoji in methodology (`📊`) | `methodology/+page.svelte` | Prefer SVG diagrams or structured data viz |
| Identical card/button patterns everywhere | All components | Vary elevation and density by information priority |

**Positive:** Dark mode is implemented with class strategy; CFP playoff row highlighting (yellow band 1–12) adds meaningful semantic color.

### 3.2 Interaction states

| Element | Hover | Focus | Active/Selected | Loading | Empty | Error |
|---------|-------|-------|-----------------|---------|-------|-------|
| Primary buttons (`.btn-primary`) | ✅ | ✅ ring | ❌ | ❌ disabled styles unused | — | — |
| Filter view tabs | ✅ | ⚠️ partial | ✅ border | — | — | — |
| Teams/Conferences page tabs | ✅ | ❌ no visible focus ring | ✅ color | — | — | — |
| Table rows (`<tr on:click>`) | ✅ | ❌ not keyboard focusable | — | — | partial empty copy | — |
| Mobile card buttons | ✅ | ⚠️ default only | — | — | — | — |
| Modal close buttons | ✅ | ⚠️ inconsistent | — | — | — | — |
| Accordion sections (TeamDetailModal) | ✅ | ❌ no `aria-expanded` | ✅ rotate chevron | — | ✅ empty states | — |
| Select inputs | ✅ | ✅ ring | — | — | — | — |

**Gaps:**

- Tab groups lack `role="tablist"`, `role="tab"`, `aria-selected`, and roving tabindex — screen readers announce them as generic buttons.
- Desktop table rows are click-only; no `tabindex="0"` or Enter/Space handlers — **keyboard users cannot open team/conference details from tables**.
- “Update Rankings” button duplicates select-on-change behavior without explaining why both exist.
- No `:active` or pressed state on filter tabs; selected state relies only on border color (may fail contrast checks for deuteranopia).

### 3.3 Accessibility (WCAG-oriented)

| Area | Status | Detail |
|------|--------|--------|
| Page language | ✅ | `app.html` `lang="en"` |
| Skip link | ❌ | No skip-to-main |
| Landmarks | ⚠️ | `<main>` in layout ✅; modals inconsistent |
| TeamDetailModal | ❌ | Backdrop uses `role="button"` instead of `role="dialog"`; no `aria-modal`, no `aria-labelledby` |
| ConferenceDetailModal | ✅ | Proper `role="dialog"`, `aria-modal`, labelled title |
| Focus trap | ❌ | Neither modal traps focus; Tab can escape to background |
| Focus restore | ❌ | Opening modal does not save/restore trigger focus |
| Escape key | ✅ | Both modals close on Escape |
| Mobile menu button | ❌ | No `aria-label`, no `aria-expanded` |
| Theme toggle (mobile) | ❌ | Missing `aria-label` (desktop has it) |
| LoadingSpinner | ❌ | No `role="status"` or `aria-live="polite"` |
| Error state | ⚠️ | Message shown but not in live region |
| Images | ✅ | Logo alts present when logos exist |
| Color-only status | ⚠️ | Green/red win % in ConferenceTable — percentage text mitigates |
| Motion | ❌ | `prefers-reduced-motion` not respected for modal fly/fade transitions |
| Touch targets | ✅ | Most buttons ≥44px on mobile tabs |

### 3.4 UX & information architecture

**Strengths**

- Responsive split: card list on mobile, table on desktop.
- Top 25 / Top 7 truncation with expand — good progressive disclosure.
- Team detail modal is information-rich: score breakdown, resume accordions, SoS/SoV, peer comparison.
- Methodology page is thorough and matches V5 weights shown in modals (65/27/8).

**Weaknesses**

1. **No shareable state** — Users cannot link to “2024 Week 10 Power 4 rankings.”
2. **Filter confusion** — Changing year/week immediately refetches; “Update Rankings” suggests batching but isn’t necessary.
3. **FCS tab likely broken** — Without `all_divisions=true`, selecting FCS may show empty table with no explanation.
4. **No search** — 130+ teams require scroll expand; store already supports search.
5. **No stale-data indicator** — `generated_at` returned by API (in dead `api.ts` transform) not surfaced in active path.
6. **Rank context loss** — Conference modal rank wrong when list truncated (KI-09).
7. **About page promised, missing** — Footer advertises content that doesn’t exist.

### 3.5 Performance

| Topic | Assessment |
|-------|------------|
| Initial load | SPA + prerendered shell; data fetch only after hydration — acceptable |
| First `/rankings` request | Backend-heavy (3 prior seasons + solver); frontend shows spinner but no progress/subtext |
| Re-fetch strategy | Full replace on every year/week change; no SWR, no client cache, no request dedup |
| Font loading | Render-blocking Google Fonts `@import` in CSS — FOUT/FOIT risk, privacy |
| Images | `loading="lazy"` on logos ✅; but logos never arrive (KI-03) |
| Modal bundle | TeamDetailModal ~520 lines inline — candidate for `{#await import()}` lazy load |
| Derived stores | Re-filter on every keystroke would be fine; search unused |
| Animations | Modal transitions run on every open — should honor reduced motion |
| Dependency bloat | Unused `@iconify/svelte` |
| Build output | Static adapter, no SSR data — correct for CF Pages deployment |

**Estimated quick wins:** self-host fonts or use `font-display: swap` via link preload; lazy-load modals; add client-side memoization keyed by `year-week`.

### 3.6 Mobile & responsive

- FilterControls view tabs scroll horizontally — good.
- Sticky header — good for long methodology page.
- TeamDetailModal slides from bottom on mobile (`items-end`) — good pattern.
- Tables hidden below `sm` — cards readable.
- **Gap:** No safe-area padding for notched devices beyond `viewport-fit=cover` on meta tag.

---

## 4. Prioritized Backlog

### P0 — Ship blockers / data correctness

| ID | Task | Rationale |
|----|------|-----------|
| P0-1 | Consolidate API into single module; delete or merge duplicate | Eliminates config drift |
| P0-2 | Add `all_divisions=true` to rankings fetch | FCS view and full team pool |
| P0-3 | Map `logo`, `logo_dark`, `color`, `alt_color` in active transform | Visual identity, user recognition |
| P0-4 | Fix Footer links: create `/about` or remove; set real GitHub repo URL | Broken navigation |
| P0-5 | Use `VITE_API_URL` via `import.meta.env` (not hostname sniffing) | Staging/preview deploys break with localhost check |

### P1 — Accessibility & core UX

| ID | Task | Rationale |
|----|------|-----------|
| P1-1 | Implement proper tab semantics on Teams/Conferences and filter view tabs | WCAG 2.2 tab pattern |
| P1-2 | Fix TeamDetailModal a11y: `role="dialog"`, label, focus trap, restore focus | Modal parity with ConferenceDetailModal |
| P1-3 | Make table rows keyboard-operable (`tabindex`, keydown) | Keyboard-only users |
| P1-4 | Add `role="status"` + `aria-live` to LoadingSpinner and error banner | Screen reader feedback |
| P1-5 | Sync `year`, `week`, `view` to URL search params | Shareable rankings |
| P1-6 | Fix conference rank index when list truncated | Data accuracy |
| P1-7 | Resolve year/week UX: either debounced auto-fetch OR explicit Update button, not both | Cognitive load |
| P1-8 | Wire search input to `setSearchQuery` | Existing store capability |
| P1-9 | Mobile menu: `aria-label`, `aria-expanded` | a11y |
| P1-10 | Add `prefers-reduced-motion` CSS to disable modal transitions | Vestibular accessibility |

### P2 — Polish, performance, design craft

| ID | Task | Rationale |
|----|------|-----------|
| P2-1 | Visual rebrand: typography, color, logo mark — move off generic Inter/blue | Impeccable distinctiveness |
| P2-2 | Extract shared `conferenceColors` + icon components | DRY |
| P2-3 | Lazy-load TeamDetailModal and ConferenceDetailModal | Initial JS reduction |
| P2-4 | Self-host fonts or use system stack with optional webfont | Performance/privacy |
| P2-5 | Add favicon + OG meta tags | Sharing polish |
| P2-6 | Surface `generated_at` / “Last updated” timestamp | Data transparency |
| P2-7 | Fetch available weeks from backend when endpoint exists; until then derive from response | Accurate week picker |
| P2-8 | Remove unused `@iconify/svelte` or adopt it to replace inline SVGs | Dependency hygiene |
| P2-9 | Client cache (Map keyed by year-week) with stale-while-revalidate | Repeat navigation speed |
| P2-10 | Add frontend tests (component + store unit tests) | Regression safety |
| P2-11 | Dark-mode logo variant (`logo_dark`) when `isDarkMode` | Contrast on dark backgrounds |
| P2-12 | `:focus-visible` rings on all interactive elements consistently | Keyboard wayfinding |

---

## 5. Recommended Fixes

### 5.1 Consolidate API layer (P0-1, P0-2, P0-3, P0-5)

**Target architecture:**

```
lib/api/
  client.ts      # API_BASE from import.meta.env.VITE_API_URL
  rankings.ts    # fetchRankings, transformRankingsResponse
  types.ts       # re-export or colocate transforms
stores/rankings.ts  # stores + filter logic only; calls lib/api
```

**Unified fetch URL:**

```typescript
const url = `${API_BASE}/rankings?year=${year}&week=${week}&all_divisions=true`;
```

**Extend active team mapping** (`rankings.ts` transform) with fields already in types:

```typescript
logo: t.logo ?? null,
logo_dark: t.logo_dark ?? null,
color: t.color ?? null,
alt_color: t.alt_color ?? null,
// keep existing resume + wins_details/losses_details fields
```

Delete duplicate logic from old `lib/api.ts` or make it a thin re-export.

### 5.2 Fix Footer & navigation (P0-4)

**Option A (minimal):** Remove `/about` link until page exists; set GitHub `href` to actual repository URL.

**Option B (better):** Add `routes/about/+page.svelte` with project description, disclaimer, contact — content already partially in Footer disclaimer.

Align Header nav with Footer: Rankings, Methodology, About.

### 5.3 URL state for filters (P1-5)

Use SvelteKit `$page.url.searchParams` or `goto` with replaceState:

```
/?year=2024&week=10&view=p4
```

On mount: read params → set filterState → fetch. On filter change: update URL. Enables share links and back-button support.

### 5.4 Tab accessibility pattern (P1-1)

For Teams/Conferences tabs in `+page.svelte`:

```svelte
<div role="tablist" aria-label="Rankings view">
  <button
    role="tab"
    aria-selected={activeTab === 'teams'}
    tabindex={activeTab === 'teams' ? 0 : -1}
    ...
  >
```

Implement roving `tabindex` and ArrowLeft/ArrowRight handlers per WAI-ARIA APG.

Apply same pattern to FilterControls view tabs (`National`, `G5`, `P4`, `FCS`).

### 5.5 TeamDetailModal a11y parity (P1-2)

Align with `ConferenceDetailModal.svelte`:

- Change backdrop to `role="dialog"` + `aria-modal="true"`.
- Add `id="team-modal-title"` on `<h2>`.
- Use `aria-labelledby="team-modal-title"`.
- On open: `focus()` close button or first focusable; trap Tab cycle.
- On close: restore focus to triggering row/button.
- Remove incorrect `role="button"` on backdrop container.

### 5.6 Keyboard-accessible tables (P1-3)

For `TeamRow.svelte` and conference `<tr>`:

```svelte
<tr
  tabindex="0"
  on:click={handleClick}
  on:keydown={(e) => (e.key === 'Enter' || e.key === ' ') && handleClick()}
>
```

Or use `<button class="sr-only">View details</button>` inside first cell for simpler a11y.

### 5.7 Simplify fetch UX (P1-7)

**Recommended:** Auto-fetch on year/week change (current behavior) and **remove** “Update Rankings” button — OR keep button and remove `@change` fetch handlers. Document choice in FilterControls header.

Add subtle loading overlay on table (preserve layout) instead of replacing entire content with spinner to reduce layout shift.

### 5.8 Wire search (P1-8)

Add to `FilterControls.svelte` or above tables:

```svelte
<label for="team-search" class="sr-only">Search teams</label>
<input
  id="team-search"
  type="search"
  placeholder="Search teams or conferences"
  on:input={(e) => setSearchQuery(e.currentTarget.value)}
/>
```

Debouncing optional for 130 rows (not required).

### 5.9 Fix conference rank (P1-6)

Pass global rank into click handler:

```typescript
function handleConferenceClick(conf: Conference) {
  const rank = sortedConferences.findIndex(c => c.conference === conf.conference) + 1;
  dispatch('click', { conference: conf, rank });
}
```

Use `sortedConferences` index, not `displayedConferences` loop index.

### 5.10 Impeccable visual refresh (P2-1) — direction sketch

Avoid another purple-gradient-on-white hero. Consider:

- **Typography:** Display face for ranks/scores (e.g., `"Bebas Neue"` or `"Oswald"`) + `"Source Sans 3"` body with `font-variant-numeric: tabular-nums` for tables.
- **Color:** Anchor on field/turf neutrals (deep green `#1a3d2e`, chalk white, accent only for CFP cutoff band). Use conference colors already mapped as secondary accents.
- **Data density:** Tighter table row height on desktop; expand on hover/focus.
- **Brand mark:** Stylized “CFBR” monogram or goal-line stripe motif—not generic checkmark circle.
- **Motion:** Subtle rank change flash only when week changes; respect reduced motion.

### 5.11 Performance quick wins (P2-3, P2-4, P2-9)

```svelte
<!-- Lazy modal -->
{#if showModal && selectedTeam}
  {#await import('./TeamDetailModal.svelte') then { default: TeamDetailModal }}
    <svelte:component this={TeamDetailModal} ... />
  {/await}
{/if}
```

```typescript
// Simple client cache in store
const cache = new Map<string, { teams: Team[]; conferences: Conference[] }>();
const key = `${year}-${week}`;
if (cache.has(key)) { /* hydrate from cache, optional background refresh */ }
```

Replace CSS `@import` fonts with:

```html
<link rel="preload" href="/fonts/..." as="font" crossorigin />
```

### 5.12 Loading & error UX (P1-4)

```svelte
<div role="status" aria-live="polite" class="...">
  <LoadingSpinner message="Loading rankings..." />
</div>

<div role="alert" aria-live="assertive" class="...">
  <p>{$error}</p>
  <button>Try Again</button>
</div>
```

---

## Appendix A — File Reference Matrix

| File | LOC (approx) | Role | Audit notes |
|------|--------------|------|-------------|
| `stores/rankings.ts` | 274 | Active data layer | Duplicate API, missing logos, no all_divisions |
| `lib/api.ts` | 122 | Dead data layer | Has correct params; unused |
| `routes/+page.svelte` | 171 | Page orchestrator | No URL sync; tab a11y gaps |
| `components/FilterControls.svelte` | 133 | Filters | Redundant update button |
| `components/RankingsTable.svelte` | 175 | Team list | Good responsive split |
| `components/TeamDetailModal.svelte` | 519 | Detail view | a11y debt; rich content |
| `components/ConferenceTable.svelte` | 216 | Conf list | Rank index bug |
| `components/ConferenceDetailModal.svelte` | 326 | Conf detail | Better a11y model |
| `components/Header.svelte` | 118 | Nav | Mobile a11y gaps |
| `components/Footer.svelte` | 26 | Footer | Broken links |
| `stores/theme.ts` | 74 | Theme | Solid implementation |
| `app.css` | 101 | Globals | External font import |
| `methodology/+page.svelte` | 758 | Docs | Comprehensive; emoji usage |

## Appendix B — Verification Checklist (post-fix)

- [ ] `npm run check` passes
- [ ] `npm run build` succeeds
- [ ] FCS view shows teams when backend has FCS data
- [ ] Team logos render in table and modals
- [ ] `/about` resolves or link removed
- [ ] GitHub link points to repository
- [ ] Share URL `/?year=2024&week=5&view=p4` restores state on load
- [ ] Keyboard: Tab to row → Enter opens modal → Escape closes → focus restored
- [ ] VoiceOver/NVDA: tabs announced correctly; loading/errors spoken
- [ ] Lighthouse a11y ≥ 90 on `/`
- [ ] `prefers-reduced-motion: reduce` disables modal slide/fade

---

*End of audit.*
