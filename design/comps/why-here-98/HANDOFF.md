# #98 "why here": design handoff package

Refs #98. CFB design seat (owner:dean-cfb), revised 2026-10-18 (ET) for D-20261018-198, plus Phil's Resume follow-up lock, image-only sharing, the `{SITE_URL}` token and the font licenses (23:4x ET). PR #108 now targets **main**, since #95 merged as `ab6e20a`. Main was merged forward into this branch with GitHub's Update branch (merge `cf628ca`). No rebase, no force-push.

## What changed in this revision (D-20261018-198 + Phil's copy lock)

- **The bar carries only the ordering parts.**
  - With Heat (2 parts): **how they look** (Elo) + **Heat**.
  - Without Heat (1 part): **how they look** alone. This is the order if Heat fails the #96 gate, and the only option before Heat has 3 weeks of history.
  - Parts still come from `parts[]`. Weights live in `data/order-config.json`, never in the renderer.
- **Context sits beside the bar, never inside the gap.** This covers resume ("Resume", "Who they beat, ranked."), schedule strength, quality of wins, and the recent-games line in 2-part states. A structure check fails if any of it appears inside a `[data-gap]`.
- **The board has a new Resume column.** The header reads "Resume", with title and `aria-description` "Who they beat, ranked.". Rows stay ordered by the ordering TR+; resume only sits beside it.
- **The share card keeps the brand name and the locked tagline.** The footer URL is unlocked, so it is omitted. The share-card check no longer requires a URL. It now requires that every visible string is locked copy or data.
- **Parts add up to the ordering-score gap.** Fixtures, checks, `check-targets.json` and this file are all updated.
- **All locked copy renders verbatim.** That is 29 of Phil's strings plus the three names, filled only from data fields.

### Record of D-20261018-198

| Where | Found? |
|---|---|
| Issue #98 comment 2026-10-19T03:15:36Z (= 2026-10-18 23:15 ET) | **Yes.** "Decision (Michael, 2026-10-18 23:15 ET, via OS): the board is ordered by Elo plus Heat. Resume is shown as its own column … The 0.15 resume and 0.05 conference weights come out of the ordering blend. Heat ships only if the #96 gate passes … If it fails, the order is Elo alone." The same comment says the bar splits the gap into Elo and Heat, with resume, schedule strength and W/L beside it as context. |
| Issue #96 comments 03:15:34Z and 03:21:09Z (23:15 / 23:21 ET) | **Yes.** Same decision text. The later comment gives the log id: ADR 0002 in the blend PR cites D-20261018-198. |
| `PURPOSE.md` on main | **No D-198 record.** The amendment of 2026-10-18 23:14 ET (`740b9bd`, #106) locks "Heat" and the fan language. It does not record the ordering decision. |
| `IDENTITY.md` on main | **No.** Unchanged. |
| Commits on main (`git log` + `git grep D-20261018-198 origin/main`) | **No.** Main's latest commits are `ab6e20a` (#95), `740b9bd` (#106) and `b921e83` (ADR 0001). ADR 0002 is not on main yet. |

### Phil's lock vs the owner summary

The #98 comment (2026-10-19T03:30:06Z) was taken as the source of truth. It agrees with the summary, with these differences:

1. **Extra locked strings.** Phil also locked value formats for schedule strength ("#{sos_rank} of {N} (1 = hardest)") and quality of wins ("#{sov_rank} of {N} (1 = best)"). These are slots `stat.sos.value` and `stat.sov.value`.
2. **League strength was conditional in Phil's text.** He wrote "confirmed if it's still a bar part … if tonight's order folds it away, drop the slot". The owner note drops it, and so does this package.
3. **Board slot count.** Phil wrote "all seven board.* slots". The board has eight existing slots: the title, 2 legend entries and 5 column headers. All eight are rendered unchanged.
4. **Wider betting check.** Phil's check also names lock, cover, projection and "will". The `no-gambling` regex now also catches lock, cover and projection. "will" stays a manual read: Phil **confirmed it clean** for all locked strings plus the Resume tooltip and accessible name (2026-10-19T03:42:10Z), and every new slot gets that read before it ships.

## Package map

| Item | Path | Count |
|---|---|---|
| Comps at 390 and 1440 | `renders/<state>-390.png`, `renders/<state>-1440.png` (sources in `states/`) | 12 states × 2 widths = 24 PNGs |
| Open row at 390 as a sheet | `renders/sheet-390-390.png` | 1 |
| Share cards 1200×675 | `renders/share-card-1200x675.png` (2-part), `renders/share-card-1part-1200x675.png` (1-part) | 2 |
| Ordering config (illustrative) | `data/order-config.json` | 2 variants |
| Fixtures | `data/fixtures.json` (`data/build_fixtures.py`) | 15 states |
| Copy slots | `copy-slots.json` (source of truth), table below | 66 slots: 41 locked, 8 existing, 16 data, 1 unlocked |
| App assertions (for #94) | `check-targets.json` | 2 routes, 19 targets, 11 guards |
| Comp assertions, proven | `check-comps.mjs`, `test-check-comps.mjs`, `planted/` | 11 guards, 14 planted HTML + 2 planted sources |
| Manifest entries (#95 schema) | `manifest.fragment.json` (unsigned, see below) | 2 routes, 4 entries |
| Tokens | `tokens.json` | 0 new proposals |
| Rebuild | `./build.sh` | — |

Primary renders:
- Open row at 1440: `renders/row-open-mid-1440.png` (2-part) and `renders/row-open-mid-1part-1440.png` (1-part)
- Share card: `renders/share-card-1200x675.png` (2-part) and `renders/share-card-1part-1200x675.png`

## States

The roster, records, ratings, colors, and games are synthetic (`data/roster-synthetic.json` and `data/games-synthetic.json`). Nothing is copied from a published board. Week labels (week 10, week 1) only name the comp states. **Heat values are illustrative** (see "Illustrative numbers").

| State | Parts | Team and data | What it shows |
|---|---|---|---|
| `board-closed` | 2 | All 8 invented teams under the 2-part order | Resume column: cell "#{resume_rank}", tooltip/accessible name "Resume: #… of 8. Who they beat, ranked."; order set by the seeded TR+; toggles closed |
| `row-open-mid` | 2 | #7 Fixture Mesa (4-4). vs #6 Fixture Ridge: gap −90 = how they look −90 + Heat 0. vs #8 Fixture Dale: +270 = +270 + 0 | Heading "Why Fixture Mesa is #7", captions, sum row, context on a board of 8, game chips with tag and venue text |
| `row-open-mid-1part` | 1 | #7 Fixture Mesa under the seeded rating alone. vs #6 Fixture Harbor −85; vs #8 Fixture Dale +300 | Same panel without Heat and without the recent-games line; neighbours change with the order |
| `negative-part` | 2 | Fixture Mesa panel alone | How they look is negative against #6 Fixture Ridge |
| `negative-part-1part` | 1 | Fixture Mesa panel alone, rating-only order | Single red bar (−85 vs #6 Fixture Harbor) |
| `heat` (was `four-part`) | 2 | #5 Fixture Harbor (5-3). vs #6 Fixture Ridge: +5 = how they look −13.5 + Heat +18.5 | **Heat decides the order** (highlighted); a check requires one comparison where Heat flips the sign |
| `row-open-first` | 2 | #1 Fixture North (8-0) | Above slot empty: "No one is ranked above them." |
| `row-open-last` | 2 | #8 Fixture Dale (1-7) | Below slot empty: "No one is ranked below them on this board." |
| `early-week` | 1 | Fixture Mesa week 1 (1-0, #6) | Heat unavailable, so 1 part; few-games note; no previous rank (Δ "—") |
| `loading` | 2 | Fixture Mesa | Skeleton sized to the part count; "Loading the breakdown…" for screen readers |
| `error` | 2 | Fixture Mesa | "Couldn't load the breakdown right now." and a "Try again" button |
| `season-unavailable` | — | 2026 W8 | "2026 rankings aren't published yet." |
| `sheet-390` | 2 | Fixture Mesa | Bottom sheet with a "Close" button |
| `share-card` / `share-card-1part` | 2 / 1 | Fixture Mesa | Headline "Fixture Mesa is #7 on TR+.", TR+, record, both comparisons, brand name, tagline, no URL; `aria-label` = locked alt text |

## How the bar works

- **Parts.** Each comparison lists the ordering parts from `parts[]` ({key, name, weight, value_self, value_other, contribution}).
  - contribution = weight × (value_self − value_other).
  - The contributions add up to the **ordering TR+ gap**, to 1e-9 in fixtures and checks.
- **Labels.** A part's label is the locked slot `part.name.<key>`. The renderer throws if the engine's `parts[].name` differs from it.
- **Weights.** Weight shares show as % under Phil's caption ("The % is how much each part counts in TR+.").
- **Data-driven guard.** No weight literal may appear in `render.mjs` or `comp.css`. That covers the old 0.80/0.15/0.05 and the illustrative 0.9/0.1.
- **Resume ranks.** `resume_rank` = rank by `record_score`.
- **Schedule strength and quality of wins.** `sos_rank` and `sov_rank` are re-ranked among the board's teams, so "#x of N" reads true (see question 6).

### Illustrative numbers (not on screen)

- **Heat weight.** It is 0.10 in the 2-part order, with how they look at 0.90, in `data/order-config.json`. It is **illustrative**: ADR 0002 and the #96 gate set the real weight.
- **Heat value.** It is **illustrative**: 1500 + the change in Elo over the last 3 weeks. Replace it with #96's definition.
- **Recent-games line.** "Last {k} games" uses k = 3, matching that illustrative Heat window.
- **Fixed values.** The 1-part order is the seeded rating alone, at weight 1.0. Resume, schedule, records, colors, and games are the invented roster, not a published week.

## Check results (`check-report.json`)

- **`node check-comps.mjs` and `--strict`:** **276/276** checks pass across 27 files.
  - parts-sum 34
  - part-label 54 (0 pending)
  - overflow-390 13
  - tap-44 23
  - focus-visible 19
  - no-gambling 28
  - copy-slots 27
  - tokens 27
  - share-card 4 (2 cards + 2 PNGs)
  - data-driven 20
  - structure 27
- **`node test-check-comps.mjs`:** **19/19 proofs hold.**
  - Each of the 14 planted HTML fixtures fails exactly its own guard:
    - new: `copy-slots-template.html` (a locked template filled with the wrong data) and `share-card-unlocked-text.html` (a stray URL on the card);
    - updated: `copy-slots-unlocked.html` now plants text in `share.card.url`, which is still unlocked.
  - `base.html` passes.
  - Both planted hard-coded sources (old 3-weight and illustrative 2-weight) trip `data-driven`.
  - 14 gambling words are caught, with 0 false positives on 10 safe phrases, including every new locked string with "locked" or "blockers".
  - The renderer is clean, and the package passes.
- **Capture.** Chrome 155.0.8059.84 on the box. The #94/#95 gate pins Chrome 154, so re-sign from that pin.

## Assertions and the #95 manifest

`manifest.fragment.json` follows #95's schema. It stays **unsigned and is not merged** into `design/comps/manifest.json`. The gate compares stills of the **built** UI, and comps are read from the base ref under `design/comps/renders/`. `_design_ref` hashes `renders/row-open-mid-<w>.png` (2-part), which the built stills should be reviewed against. `check-targets.json` names app routes. The comp fixtures are the invented roster, not those schools.

## Data the view reads (#105 / #96 asks)

| Field | Status | Used by |
|---|---|---|
| ordering `parts[]` {key, name, weight, value} and per-neighbour `parts[]` {contribution}, `gap` | #105 item 5. The keys are `strength` and `heat` only; weights come from ADR 0002 | `part`, `parts-sum`, `data-driven` |
| `team.heat` | #96 | the Heat part |
| `team.resume_rank` | **new ask** (rank by `record_score`) | `resume-cell`, `ctx-resume` |
| `team.sos_rank`, `team.sov_rank` **on this roster**, plus N | seeded, then re-ranked among the 8 invented teams | `stat-sos`, `stat-sov` |
| `team.prev_rank` under the same order | #105 item 2 | `delta` |
| `team.recent` {k, wins, losses} | derivable from `games[]` over the Heat window | `recent` |
| `games[]` {opponent, opponent_rank, venue, result, tag} | #105 item 1 (`venue` and `tag` are new) | `chips` |
| `team.games_played` | derivable | `few-games` |
| season default | #105 item 3 | `season-unavailable` |

Teams, ratings, records, colors, and games are invented (`data/roster-synthetic.json`, `data/games-synthetic.json`). The names are Fixture North, South, East, West, Harbor, Ridge, Mesa, and Dale. That roster is a stand-in until #105 lands. It is not the published 2024 board.

## Assets

- **Fonts:** Oswald and Source Sans 3 in `assets/fonts/`, with upstream SIL OFL 1.1 licenses `OFL-Oswald.txt` (google/fonts `ofl/oswald/OFL.txt`) and `OFL-SourceSans3.txt` (adobe-fonts/source-sans `LICENSE.md`), copied verbatim.
- **Team mark:** a team-colour disc, exempt from the token check via `[data-team-color]`.
- **Glyphs:** 16 inline SVGs (`currentColor`); new this revision: `heat` and `resume`.
- **Share background:** field-haze gradient.

## Copy slots

Locked and existing slots render verbatim, with `{fields}` filled from data only. Unlocked slots are omitted. Data slots render data. **Dropped:**
- `part.name.resume`: "who they beat" is no longer a bar label.
- `part.name.league`: league strength left the order.

| Slot | Status | Text rendered | Where |
|---|---|---|---|
| `brand.name` | locked | "True Rankings" | share card footer (tagline stays per owner steering) |
| `brand.tagline` | locked | "How good they actually are." | share card footer (tagline stays per owner steering) |
| `brand.rating` | locked | "TR+" | board header, panel score, share card |
| `board.title` | existing | "Top 25 Teams" | board card header |
| `board.legend.cfp` | existing | "CFP Playoff (1-12)" | board legend |
| `board.legend.bubble` | existing | "On the Bubble (13-25)" | board legend |
| `board.col.rank` | existing | "Rank" | board header |
| `board.col.team` | existing | "Team" | board header |
| `board.col.conference` | existing | "Conference" | board header |
| `board.col.record` | existing | "Record" | board header |
| `board.col.delta` | existing | "Δ" | board header |
| `board.col.resume` | locked | "Resume" | board header; resume_rank column (context only, does not set the order) |
| `board.col.resume.description` | locked | "Who they beat, ranked." | Resume header tooltip (title) and accessible description (aria-description); also the Resume context item in the panel |
| `board.resume.cell` | locked | "#{resume_rank}" | Resume cell value on every board row (390 and 1440) |
| `board.resume.cell.accessible` | locked | "Resume: #{resume_rank} of {N}. Who they beat, ranked." | Resume cell tooltip (title) and accessible name (aria-label); N = board size |
| `stat.resume.value` | locked | "#{n} of {N} (1 = best)" | panel Resume stat value (context beside the bar); n = resume_rank, N = board size |
| `part.name.strength` | locked | "how they look" | bar label (engine sends parts[].name; must equal this text) |
| `part.name.heat` | locked | "Heat" | bar label, 2-part order only |
| `why.toggle.accessible_name` | locked | "Show why {Team} is #{rank}" | row toggle aria-label |
| `why.heading` | locked | "Why {Team} is #{rank}" | open panel heading |
| `why.vs_above.caption` | locked | "Why they trail #{rank_above} {TeamAbove}" | comparison vs #N-1 caption |
| `why.vs_below.caption` | locked | "Why they lead #{rank_below} {TeamBelow}" | comparison vs #N+1 caption |
| `why.no_above` | locked | "No one is ranked above them." | #1 team, in place of the above comparison |
| `why.no_below` | locked | "No one is ranked below them on this board." | last team, in place of the below comparison |
| `why.sum.caption` | locked | "Add the parts and you get the TR+ gap." | sum row under the parts |
| `why.weight.caption` | locked | "The % is how much each part counts in TR+." | explains the % next to each part |
| `why.delta.caption` | locked | "Move since the last ranking." | explains the move vs previous rank |
| `stat.sos.label` | locked | "Schedule strength" | schedule strength stat (value = sos_rank) |
| `stat.sos.value` | locked | "#{sos_rank} of {N} (1 = hardest)" | schedule strength value (context beside the bar) |
| `stat.sov.label` | locked | "Quality of wins" | quality of wins stat (value = sov_rank) |
| `stat.sov.value` | locked | "#{sov_rank} of {N} (1 = best)" | quality of wins value (context beside the bar) |
| `stat.heat.recent_form_line` | locked | "Last {k} games: {wins}-{losses}." | Heat context, 2-part order only |
| `chips.heading` | locked | "The games" | game strip heading |
| `chip.tag.quality_win` | locked | "Quality win" | chip tag text + legend |
| `chip.tag.cupcake` | locked | "Cupcake" | chip tag text + legend |
| `chip.tag.bad_loss` | locked | "Bad loss" | chip tag text + legend |
| `chip.venue.home` | locked | "Home" | chip venue |
| `chip.venue.away` | locked | "Away" | chip venue |
| `chip.venue.neutral` | locked | "Neutral site" | chip venue |
| `early.note` | locked | "Few games played so far, so this rank rests on thin evidence." | few games / early week marker |
| `loading.label` | locked | "Loading the breakdown…" | screen-reader loading text |
| `error.message` | locked | "Couldn't load the breakdown right now." | error state |
| `error.retry.label` | locked | "Try again" | retry button |
| `unavailable.message` | locked | "{season} rankings aren't published yet." | season data not published |
| `share.button.label` | locked | "Share" | panel share button |
| `share.card.headline` | locked | "{Team} is #{rank} on TR+." | share card |
| `share.card.alt_text` | locked | "{Team} is #{rank} on True Rankings, with a TR+ of {tr_plus} and a {record} record." | share image alt / og:image:alt |
| `share.post_text` | locked | "{Team} is #{rank} on TR+. Here's why. {url}" | UNRENDERED: owner decision 2026-10-18, sharing ships image-only (no URL, no post text) until Michael picks the domain |
| `sheet.close.label` | locked | "Close" | 390 sheet close button |
| `share.card.url` | unlocked | — (omitted) | share card footer; OMITTED (image-only sharing until Michael picks the domain) |
| `data.team_name` | data | field `team.team_name` | everywhere |
| `data.rank` | data | field `team.rank` | disc, header |
| `data.tr_plus` | data | field `team.final_ranking_score (1 dp)` | header, share card |
| `data.record` | data | field `team.record` | header, rows |
| `data.delta` | data | field `team.prev_rank - team.rank (#105)` | header, board Δ |
| `data.resume_rank` | data | field `team.resume_rank (rank by record_score; #105)` | board.resume.cell, board.resume.cell.accessible, stat.resume.value |
| `data.part.weight` | data | field `parts[].weight as %` | bar row |
| `data.part.contribution` | data | field `weight × (value_self − value_other), 1 dp signed` | bar row |
| `data.gap` | data | field `team ordering TR+ − neighbour ordering TR+, 1 dp signed` | comparison header |
| `data.sos_rank` | data | field `team.sos_rank (#105)` | stat |
| `data.sov_rank` | data | field `team.sov_rank (#105)` | stat |
| `data.game` | data | field `games[]: result, opponent, opponent_rank (#105 venue/tag)` | chips |
| `data.url` | data | field `team.url (teamPath + year/week)` | share.post_text {url} only (not on the card) |
| `data.season` | data | field `season` | unavailable state |
| `data.recent` | data | field `team.recent {k,wins,losses} over the Heat window` | stat.heat.recent_form_line |
| `data.board_size` | data | field `board_size = {N}` | stat.sos.value, stat.sov.value |

`share.post_text` is locked but **unrendered** (`"rendered": false` in `copy-slots.json`). Owner decision (2026-10-18): **sharing ships image-only** — the 1200×675 card only, with no URL and no post text — until Michael picks the domain. `share.card.url` stays unlocked and omitted.

## Open questions

1. **Share URL — decided.** Sharing ships image-only (no URL, no post text) until Michael picks the domain. The previously assumed domain belongs to someone else, so every URL in fixtures and planted files is the literal token `{SITE_URL}`; nothing renders it.
2. **Heat weight and definition.** These wait on ADR 0002 and the #96 gate. When they land, update `data/order-config.json` and rebuild. The renderer doesn't change.
3. **Resume value — locked** (Phil, #98 2026-10-19T03:42:10Z). Board cell `board.resume.cell` "#{resume_rank}"; its tooltip and accessible name `board.resume.cell.accessible` "Resume: #{resume_rank} of {N}. Who they beat, ranked." (N = board size, like sos/sov); panel stat `stat.resume.value` "#{n} of {N} (1 = best)". Comps put the accessible name in `title` + `aria-label` on the cell; some screen readers ignore `aria-label` on a plain `td`/`span`, so the app may prefer visually hidden text with the same string.
4. **Fonts in stills.** #95 strips Google Fonts, so built stills fall back unless the frontend self-hosts these faces.
5. **Few-games threshold.** The comps use fewer than 4 games. This needs an engine owner.
6. **Data oddities.**
   - `sos_rank` and `sov_rank` are re-ranked on this 8-team synthetic roster (see the data table above).
   - Conferences are "Synthetic East" and "Synthetic West". They are not school conferences.
7. **CI wiring.** `test-check-comps.mjs` is not in CI yet. Add a step to the #95 workflow; that needs a token with workflow scope.
