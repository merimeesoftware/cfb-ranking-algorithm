# True Rankings front-end design brief

Proposed for Dean's review and Phil's copy pass. Neither has signed. This is a design comp and a copy table. It does not change the Svelte app, the ranking math, or the live board.

Figures are from the stored files `frontend/static/rankings/2026/week-10.json`, `week-9.json`, and `week-1.json`. The file label is `v5.3`. Auburn and Baylor were only an illustration in the ask. They are not the comp. No live CFBD call and no live AI call.

## What ships in this pull request

- This brief.
- [Phil's copy table](phil-copy-table.md), proposed, not locked.
- A static comp at `design/comps/elo-order-brief/preview.html`, with the faces named in `DESIGN.md` (OFL Oswald and Source Sans 3, files beside the comp).
- Stills at 390 and 1440 in the pull request body.

Open `preview.html` and scroll for every surface. `?shot=board`, `?shot=why`, `?shot=peers`, and `?shot=formula` are the still frames.

## What this leaves alone

[PR #155](https://github.com/merimeesoftware/cfb-ranking-algorithm/pull/155) (`cursor/frontend-story-numbers-d36e`, agent `bc-121fa0a4-6953-5f14-a44f-ef6a3ab1d36e`) corrects the page so it stops saying 65/27/8, K 40, home field 65, and an upset cap of 1.20. Michael said that pull request is the number fix, not the redesign. This branch does not edit those files, does not restyle that diff, and does not put 65/27/8 back.

Accounts, a forum, and guest posting stay proposals. They are not in the comp. Betting, odds, spreads, picks, and The Drop stay off the page.

`DESIGN.md` still says the board sits below the fold. PR #155 already pulls the table into the first viewport and edits that rule on its own branch. This brief does not touch `DESIGN.md`, so the two branches do not fight over that file. The comp agrees with the first-viewport board and goes on: the landing is the week itself.

## The order the comp draws

Two facts sit next to each other. The formula surface says both.

**Approved order.** Sort by how they look, high to low. That column is `team_quality_score` in the week file, the Elo rating in the code. Heat's weight is 0. The gate in the parts report failed for every positive weight. Record, record quality, Heat, and early-season are columns. They do not move the rank.

**Old blend, still what the code publishes.** `0.80 × how they look + 0.15 × résumé score + 0.05 × league strength`. On the 2026 week 10 file that sum matches `final_ranking_score` (largest gap about 10⁻¹²). 127 of 138 teams sit in a different place than how they look. The mean absolute gap is 5.99 places. The parts are not scaled to 0–100 before the weights.

65/27/8 is a stale page. It is neither the code nor the approved order. PR #155's job is to stop the page saying it. This brief's job is to stop the next design from treating 80/15/5 as the new order.

The comp's board is drawn in the approved order so Dean can see that board. It is labeled as the design order. It does not claim the code on main already sorts that way.

Fan language on the board and the team page says "how they look." The formula page, which is the deep dive, says that name is the Elo rating. That split follows `PURPOSE.md`: Elo stays off the primary path.

Locked lines, used verbatim:

- How good they actually are.
- The order you check before you argue — not a poll, not a committee, not the narrative.

## Landing: the current week

The latest stored week is 2026 week 10 (`latestPublishedWeek()` already seeds the home page from that file). The comp opens on it. There is no hero to scroll past and no "Jump to the board."

The masthead is one compact bar: True Rankings, 2026 · Week 10, TR+, the tagline, and the locked positioning line. Gold is only the playoff-band mark on ranks 1–12.

The first screen is a case, then the board.

**This week, from week 9 to week 10 on how they look.**

- Miami was No. 1 at 8-0 (1,794.9) and is No. 6 at 8-1 (1,738.6).
- Utah was No. 2 at 8-0 and is No. 1 at 9-0 (1,820.8).
- Ohio State fell from No. 13 to No. 31, 6-2 to 6-3, 1,643.2 to 1,545.2.
- Michigan State climbed from No. 85 to No. 55, 2-6 to 3-6, 1,275.0 to 1,399.4.

"Fell" and "climbed" are the words for a move in the order. Heat is reserved for the weight-0 column. The current stub's phrase "Taking heat" for a drop would collide with that column. The copy table proposes the change.

## 1. A case, with a line per team

Three cases sit on the board. Each line is filled from stored fields. The template for any other team is in the copy table.

**No. 1.** Utah is No. 1 on how they look at 1,820.8, up from No. 2. They are 9-0 in the Big 12, 8-0 against Power 4, with 2 quality wins and 1 win off the FBS board. Georgia is 20.4 points behind.

**The closest argument above the playoff cut.** Georgia is No. 2 at 1,800.3, 8-1, with 3 quality wins. UCLA is No. 3 at 1,780.8 and 9-0, 19.6 points back. The old blend had UCLA No. 2 and Georgia No. 3.

**A soft 8-1, outside the top 12, so the column has a loud row.** Liberty is 8-1 and No. 58 on how they look (1,389.1). The old blend had them No. 42, 16 places higher. Schedule rank 137 of 138. Quality wins: 0. Wins off the FBS board: 1. Conference USA. The column shows the gap. The rank stays 58.

Per-team text elsewhere uses the same fill, including the old blend's place, so a reader can see when the résumé and the rating disagree. It is deterministic copy from the week file. It is not a live model call. The current stub sentence "The board ranks them on who they beat and how they look" describes the old blend. The proposed line describes the approved order and keeps the old blend as a named comparison.

## 2. Similar strength, different leagues

**Indiana and Wake Forest.** Both 8-1. How they look 1,700.3 and 1,698.3, 1.9 points apart. Schedule ranks 71 and 73 of 138. Indiana, Big Ten, is 5-1 against Power 4 with 0 quality wins. Wake Forest, ACC, is 6-1 against Power 4 with 1 quality win. Each has 1 win off the FBS board. The order is Indiana, then Wake Forest.

**BYU and LSU.** 2.2 points apart. BYU is No. 21, 7-2, Big 12, schedule rank 18, how they look 1,621.3. LSU is No. 22, 6-3, SEC, schedule rank 24, how they look 1,619.1.

**League landscape on the same file.** Average of how they look, and the file's record against Power 4:

| League | Label on the file | Teams | Average | Against Power 4 |
| --- | --- | --- | --- | --- |
| Big 12 | Power 4 | 16 | 1,740.0 | 12-7 |
| SEC | Power 4 | 16 | 1,715.1 | 11-2 |
| Big Ten | Power 4 | 18 | 1,693.2 | 10-10 |
| ACC | Power 4 | 17 | 1,591.8 | 8-12 |
| Pac-12 | Power 4 | 8 | 1,194.6 | 0-12 |

The top four averages sit within 148.2 points. The Pac-12 row on this file is 545.4 points below the Big 12 and is 0-12 against Power 4. The comp plots them on a scale from 1,100 to 1,800 so that cluster and that gap are both visible. The season map and this week file do not always use the same conference name. The comp prints the file's label and does not relabel the row. PR #155's Mixed label on the FBS Independents conference row, when tiers differ, stays that pull request's correction. This comp does not undo it and does not redraw it.

The file's FBS Independents rollup average is 0. Notre Dame's own league number on the team row is 1,552.8 (No. 4, 8-1, 1,763.9). The comp does not draw that 0 as a measured league strength.

## 3. A table of peers, with shareable weights

Fans compare orders. They do not get accounts.

The comp shows three shared tables for this week:

| Table | Weights (how they look / résumé / league / Heat) | First three | What it is |
| --- | --- | --- | --- |
| Official | 100 / 0 / 0 / 0 | Utah, Georgia, UCLA | The board |
| Published blend | 80 / 15 / 5 / 0 | Utah, UCLA, Georgia | The order the code still sorts. A comparison. |
| This what-if | 70 / 30 / 0 / 0 | Utah, UCLA, Alabama | A comparison a link can carry |

A link such as `/2026/week/10?whatif=70-30-0-0` is the share. Anyone with the link sees the same weights. The official board on that page stays the approved order.

## 4. Weight sliders, labeled what-if

The comp freezes one slider state so the still is checkable:

`0.70 × how they look + 0.30 × résumé score + 0 × league strength + 0 × Heat`

At those weights the what-if list is Utah, UCLA, Alabama, Miami, Georgia. Georgia is No. 5 there. The official board still has Georgia No. 2.

Heat's slider is held at 0. The week file has no Heat number, and the gate set the weight to 0. Moving it would invent a term. The label says so.

The sliders in the comp are the control, shown at this state. They do not rewrite the official rows above them. A later build recomputes the what-if list from the stored week file in the browser. It does not call CFBD and it does not write a new official board.

## 5. The board columns

Order is how they look. Display columns:

| Column | What the cell uses | Week 10 |
| --- | --- | --- |
| Record | `total_wins`–`total_losses` | Utah 9-0. The win-loss line, not the résumé score. |
| Record quality | Old blend's place, and `fcs_wins` | South Carolina: old blend No. 20, 8 places lower, 1 win off the board. Liberty: old blend No. 42, 16 places higher. |
| Heat | Nothing stored | An em dash. Weight 0. |
| Early | On when wins + losses < 3 | Off for all 138 teams this week. Each has at least 3 games. |

Record quality is the report's fraud column, under a public name. It is the gap between this order and the old blend, plus wins off the FBS board. It is not a weight. The report's stronger fraud test (wins ahead of the wins Elo expected) needs expected wins, and the week file does not store them. The comp does not invent that remainder.

The top 12 of the design order: Utah, Georgia, UCLA, Notre Dame, Alabama, Miami, Texas, Tennessee, Indiana, Wake Forest, Iowa, South Carolina. Notre Dame's conference string on the file is FBS Independents.

## 6. Team page: why South Carolina is No. 12

South Carolina is the sample because the two orders disagree by 8 places, inside the top 12.

- How they look: 1,662.2. This is the rank.
- Gap to No. 11 Iowa (1,679.5): 17.3 points, all of it how they look.
- Gap to No. 13 Houston (1,657.5): 4.8 points, all of it how they look.
- Record, beside the rank: 6-3, SEC.
- Who they beat, from stored counts: 2 quality wins, 1 quality loss, 1 bad loss, 4-3 against Power 4, 1-0 against Group of 5, 1 win off the FBS board.
- Schedule rank 37 of 138. Victory rank 24 of 138. Those ranks are stored. They do not set the order.
- Old blend: No. 20. The who-they-beat score is 1,308.0. That is why the old order dropped them 8 places.
- Heat: weight 0. No number on the file.
- Early-season: off. 9 games.

The week file has no game list. The page lists the stored counts. It does not invent opponents or scores. When a later build has a stored game list, key wins and losses use that list and still do not invent one.

## 7. Early-season, on the column and on the formula page

2026 week 1: all 138 teams have one game, so the flag is on for the whole board. Indiana leads that file at 1-0, how they look 1,827.4. Week 1 keeps 0.7 of last year's final score in the opening number.

The fade is `max(0, 0.7 × (12 − week) / 11)`. Week 10 keeps 0.127. Week 12 and after keeps 0. The early flag is the three-game test, not the fade. Week 10 can still carry a slice of last year and have the flag off. The formula page says both.

## 8. Formula explainer

Two blocks, in this order, with the code's constants under them.

**Approved order.** Sorted by how they look. Heat weight 0. The four markers are columns.

**Old blend.** `0.80 / 0.15 / 0.05`, named as what the code publishes, with the 127-of-138 and 5.99-place facts from this file.

Constants, matching the ranker, for the deep dive:

| Term | Value in the code |
| --- | --- |
| K | 50, times 0.65 in the postseason (32.5) |
| Margin | ln(margin + 1), no cap |
| Home field | 50 regular, 20 postseason, 0 neutral. Expectation only. |
| Upset | ×1.18 when the winner trailed by more than 150. ×1.12 when a Group of 5 team beats a Power 4 team. They stack. The product is not capped at 1.18. |
| Matchup weights | 1.0, 0.8, 0.65, 0.2, 0.1 |
| Winner ceiling | 1,850. The loser still drops the full step. |
| Tier starts | 1,500 / 1,200 / 900 |
| Prior | 0.70 of last year's final score + 0.30 of the year before |
| Fade | max(0, 0.7 × (12 − week) / 11) |

Home field 65, K 40, upset 1.25 with a 1.20 cap, and "scaled to 0–100 before weighting" stay out. PR #155 already replaces those with the code's numbers. This page keeps those corrected numbers and changes what they are said to order.

## Visual system

Keep the night-field tokens already in `DESIGN.md` and `IDENTITY.md`. Field `#1a3d2e`, deep `#0f241b`, chalk `#eef1ee`, ink `#14241c`, gold `#c9a227` only on the top-12 mark. Oswald for the brand, ranks, and team names. Source Sans 3 for the body. Tabular numbers.

Composition change for Dean: one masthead, then the case, then the board on a wide screen. On a phone the board is the first paint under the week line, and the three cases follow the first rows, so the order is on screen without a scroll past an essay. No second sticky bar. No hero cards. Filters and the conference chart sit with the peers section, not in a "Ranking Controls" bar. The what-if block is a labeled region with a border, not a gold banner, so gold stays on the playoff band.

The table is a real table. At a narrow width it stacks into cards with the column name in front of each value, rank and team as the card header. The official order never becomes a slider output.

## For the next build, after review

1. Draw the official board in the approved order only when the math change lands. Until then, a shipped page has to keep saying that the code sorts by the old blend.
2. Keep PR #155's corrected constants (K 50, home field 50, upset 1.18 and 1.12, matchup weights, no 0–100-before-weighting).
3. Fill per-team lines from the week file with the template in the copy table.
4. Compute what-if ranks in the browser from stored `team_quality_score`, `record_score`, and `conference_quality_score`. Heat stays 0 until a stored Heat number exists and a non-zero weight passes the gate.
5. Leave accounts, forums, and guest posts out.

## Source

Approved read: the parts-and-propositions report (main at `41767f4`). Ordering decision it records: Elo alone once Heat's weight is 0, with the résumé and the other markers as columns. Heat's three candidates all lost to Elo on 2019–2022. Chosen weight 0.
