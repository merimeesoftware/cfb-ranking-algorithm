# #98 "why here": design handoff package

Refs #98. Built by the CFB design seat (owner:dean-cfb) on 2026-10-18 (ET), branched from the head of PR #95 (`cursor/preview-stills-gate-380c` @ `5378550`). PR #95 is **not merged** (Minicon REVISE). This branch only merges forward from #95, with no rebase and no force-push.

The board table stays primary and **unchanged**. There are two exceptions. First, a 44 px row toggle cell. Second, a larger hit area on the team-name link: padding and an equal negative margin, so it looks the same, to meet the 44 px rule.

## Package map (Autobot list → files)

| Item | Path | Count |
|---|---|---|
| Comps at 390 and 1440 | `renders/<state>-390.png`, `renders/<state>-1440.png` (HTML sources in `states/`) | 10 states × 2 widths = 20 PNGs |
| Open row at 390 as a full-width sheet | `renders/sheet-390-390.png` | 1 |
| Share card 1200×675 | `renders/share-card-1200x675.png` | 1 |
| States | table below; `data/fixtures.json` (one object per state) | 12 |
| Assets | "Assets" below; `assets/fonts/`, inline SVG glyphs in `render.mjs` (`ICON`) | 2 fonts, 14 glyphs |
| Copy slots | `copy-slots.json` (source of truth), table below | 57 slots: 30 unlocked, 16 data, 8 existing, 3 locked |
| Assertions (app side, for #94) | `check-targets.json`: routes, 16 selector targets, 11 guards | — |
| Assertions (comp side, proven) | `check-comps.mjs`, `test-check-comps.mjs`, `planted/` | 11 guards, 12 planted fixtures + 1 planted source |
| Manifest entries (PR #95 schema) | `manifest.fragment.json` (not merged into `design/comps/manifest.json`, see below) | 2 routes, 4 comp entries |
| Tokens | `tokens.json`: IDENTITY.md + the main tailwind scale + hexes the board already ships | 0 new token proposals |
| Rebuild | `./build.sh` (fixtures → states → renders → fragment → checks) | — |

Primary renders:
- Open row at 1440: `renders/row-open-mid-1440.png`
- Open row at 390: `renders/row-open-mid-390.png`, and as a sheet, `renders/sheet-390-390.png`
- Share card: `renders/share-card-1200x675.png`

## States

| State | Team / data | What it proves |
|---|---|---|
| `board-closed` | 2024 W10 top 25 | Board unchanged, toggle on every row, `aria-expanded=false` |
| `row-open-mid` | #15 Iowa State (7-1) vs #14 Ole Miss (gap −1.3) and #16 Boise State (+7.0) | Header (rank, TR+, record, Δ −5), two diverging-bar comparisons, game chips, `sos_rank` #45, `sov_rank` #12 |
| `row-open-first` | #1 Oregon | No team above: the above slot is empty (`data-empty=true`) and its copy slot is omitted |
| `row-open-last` | #136 UTEP (1-8) | No team below. Three bad-loss chips, including a loss to an FCS team (Southern Utah) |
| `three-part` | every 3-part state above | Parts come from `DEFAULT_CONFIG` weights (80 / 15 / 5 %, read from `ranking_service.py` with ast) |
| `four-part` | Iowa State under illustrative Elo-plus-form weights (Michael pending) | 4 parts; the Heat label is omitted because the slot is unlocked; re-ranked neighbours |
| `negative-part` | Iowa State panel alone | Red bars run left of the axis (strength −54.4 vs Ole Miss) |
| `early-week` | Iowa State, 2024 W1 (1-0, rank 38) | Few-games marker (dashed bars, `games_played` = 1), no previous rank (Δ shows "—") |
| `loading` | Iowa State | Skeleton, `aria-busy`, no text |
| `error` | Iowa State | Alert glyph and a 44 px retry button; message slot omitted |
| `season-unavailable` | 2026 W8 (no static detail yet, #105) | Empty state that shows only the season |
| `sheet-390` | Iowa State | Full-width bottom sheet, `role=dialog`, close button 44 px |
| `share-card` | Iowa State | 1200×675, brand plus locked tagline, URL baked in |

`three-part` is not a separate file. Every 3-part state is a 3-part comp, and `four-part` is the 4-part comp.

## How the bar works (data, not constants)

Each comparison lists the parts from `parts[]`. Each part has `key`, `name`, `weight`, `value_self`, `value_other` and `contribution`, where contribution = weight × (value_self − value_other). The contributions add up to the TR+ gap with the neighbour. The renderer does not know how many parts there are or what their weights are. The `data-driven` guard fails if a weight literal appears in `render.mjs` or `comp.css`. Positive (green, `#2d5a45`) means a part works for the open team; negative (red, `#C41E3A`) means it works against. Bars are scaled to the largest |contribution| in the panel. Measured on 2024 W10, all 136 teams: TR+ equals Σ weight × value to 2.3e-13.

## Check results (`check-report.json`)

- `node check-comps.mjs`: **253/253 checks pass** across 22 files.
  - parts-sum 24
  - part-label 76 (4 pending: the Heat label in `four-part`, allowed in comps)
  - overflow-390 11
  - tap-44 19
  - focus-visible 17
  - no-gambling 23
  - copy-slots 22
  - tokens 22
  - share-card 2
  - data-driven 15
  - structure 22
- `node check-comps.mjs --strict` (the app setting): **249/253**. The 4 failures are the pending Heat label, which shows that the view cannot ship until Michael names Heat and Phil locks it.
- `node test-check-comps.mjs`: **16/16 proofs hold**.
  - Each of the 12 planted fixtures fails exactly its own guard and nothing else.
  - `base.html` passes everything.
  - The planted hard-coded-weight source trips `data-driven`.
  - 10 gambling words are caught with 0 false positives on 9 safe phrases.
  - The real package passes.

Captured with Chrome 155.0.8059.84 on the box. The #94 gate pins Chrome 154, so re-sign from that pin.

## Assertions and the PR #95 format

PR #95 defines `design/comps/manifest.json` (`route`, `width`, `file`, `sha256`, `signed_by`, `signoff`, `masks`) and a pixel gate. It has **no selector-assertion format**. The assertions therefore live in two places:
- `check-targets.json` (app side: routes, selectors, guard ids). It follows the marriages-of-grace `check-targets.json` convention that #94 ports from.
- `check-comps.mjs` (comp side, proven by `planted/`).

`manifest.fragment.json` uses #95's schema exactly but stays **unsigned and unmerged**, for two reasons:
1. The gate compares stills of the **built** UI at a 0.2% pixel diff. A signed comp has to be captured from the #98 implementation (`visual-check.mjs --capture-only`), not taken from these HTML design renders. `_design_ref` gives the hash of the design render that the built still is reviewed against.
2. The Minicon REVISE on #95 moves comp lookup to the base ref. A comp counts only once it is on main, under `design/comps/renders/`, which is why the fragment's `file` paths point there.

## Data the view reads (the #105 fields named in the assertions)

| Field | Status | Used by |
|---|---|---|
| `team.prev_rank` | #105 item 2 | `delta` |
| `team.sos_rank`, `team.sov_rank` | in static JSON today; #105 item 4 makes them required | `stat-sos`, `stat-sov` |
| `parts[]` {key, name, weight, value, contribution} and per-neighbour `parts[]` with `contribution` and `gap` | #105 item 5 (parts-add-up test); names are a copy slot | `part`, `parts-sum`, `data-driven` |
| `games[]` {opponent, opponent_rank, venue, result, tag} | #105 item 1 (win/loss lists). `venue` (home/away/neutral) and `tag` are new: today `wins_details` only has `is_road` | `chips` |
| `team.games_played` | derivable from `records` | `few-games` |
| `team.url` | `teamPath(name, year, week)` | `share-card` |
| season default | #105 item 3 (`/rankings/team` defaults to 2023) | `season-unavailable` |

Game lists in these comps come from ESPN's public schedule API (`data/games-2024-espn.json`), standing in until #105's precompute lands. Opponent ranks and tags are computed from the 2024 W10 static board using the engine's thresholds (quality win above FBS P75; cupcake and bad loss below the tier P25, or against FCS).

## Assets

| Asset | Source | Note |
|---|---|---|
| Oswald (variable 500–700), Source Sans 3 (variable 400–700) | Google Fonts latin subset, SIL OFL; `assets/fonts/` | IDENTITY.md faces. See open question 4 |
| Team logo | CFBD logo URL in the app; comps use the team-colour disc that `TeamRow.svelte` already ships | Colours exempt from the token guard via `[data-team-color]` |
| Glyphs (inline SVG, `currentColor`) | chevron, up, down, home, away, neutral, star, share, close, alert, retry, calendar, schedule, wins | Venue glyphs stand in while `chip.venue.*` is unlocked |
| Share card background | existing `field-haze` gradient (tailwind config on main) | — |

## Copy slots (all need Phil's lock or confirmation; unlocked slots are omitted from every render)

**Locked (render verbatim):**
- `brand.name`: "True Rankings"
- `brand.tagline`: "How good they actually are."
- `brand.rating`: "TR+"

**Existing on main, unchanged:** `board.title`, `board.legend.cfp`, `board.legend.bubble`, `board.col.rank|team|conference|record|delta`.

**Data:**
- `part.name.strength`, `part.name.resume`, `part.name.league` (fixture values come from the PURPOSE.md fan-language list: "how they look", "who they beat", "league strength")
- `data.team_name`, `data.rank`, `data.tr_plus`, `data.record`, `data.delta`, `data.part.weight`, `data.part.contribution`, `data.gap`, `data.sos_rank`, `data.sov_rank`, `data.game`, `data.url`, `data.season`

**Unlocked (omitted):**
- `part.name.heat` (waiting on Michael)
- Panel and comparisons: `why.toggle.accessible_name`, `why.heading`, `why.vs_above.caption`, `why.vs_below.caption`, `why.no_above`, `why.no_below`, `why.sum.caption`, `why.weight.caption`, `why.delta.caption`
- Stats: `stat.sos.label`, `stat.sov.label`, `stat.heat.recent_form_line`
- Chips: `chips.heading`, `chip.tag.quality_win`, `chip.tag.cupcake`, `chip.tag.bad_loss`, `chip.venue.home`, `chip.venue.away`, `chip.venue.neutral`
- States: `early.note`, `loading.label`, `error.message`, `error.retry.label`, `unavailable.message`
- Share and sheet: `share.button.label`, `share.card.headline`, `share.card.alt_text`, `share.post_text`, `sheet.close.label`

## Open questions

1. **Heat**: the name (Michael), its weights, and whether resume moves to its own board column. The 4-part comp uses illustrative weights (70/10/15/5) and an illustrative value (1500 + change in Elo over 3 weeks). Swap both for the engine's numbers when they exist.
2. **PURPOSE.md vs the no-gambling rule.** PURPOSE.md's locked lines include "…before you argue or bet" and "Sell disagreement with the market", and the live hero still says "before you argue or bet". Neither is used in this package. Michael and Phil need to re-lock PURPOSE.md.
3. **Accessible names.** The share, retry and close buttons are icon-only until their label slots are locked. The row toggle uses `aria-labelledby` pointing at the team name in the meantime.
4. **Fonts in stills.** #95 strips Google Fonts from captured pages, so built stills render fallback faces unless the frontend self-hosts Oswald and Source Sans 3 (these files could be reused). Decide this before signing any comp.
5. **Few-games threshold.** The comps use fewer than 4 games. Archie or the engine should own the number.
6. **Data oddities seen in the fixtures.**
   - Membership is #101: UTEP is "Mountain West" and Boise State is "Pac-12" in 2024, and the comps render these as-is.
   - 2024 W1 `sos_rank` is 191 on a 135-team board.
7. **Wiring.** `test-check-comps.mjs` isn't in CI yet, so the #95 workflow under review isn't touched. Add a step after #95 lands.
