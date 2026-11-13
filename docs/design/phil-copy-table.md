# Phil copy table — Elo-order redesign

Proposed copy for Phil. Not signed. Dean has not signed the comp.

Locked lines are copied verbatim from `PURPOSE.md` and `frontend/src/lib/brand.ts`. Everything else is a proposal.

"On main today" is `main` at `41767f4`. "PR #155" is the number-fix pull request. Where that pull request corrects a stale number, this table tells Phil to keep the correction. The proposed cell is the redesign's sentence, not a return to 65/27/8.

Public surfaces say "how they look." The formula page adds one deep-dive sentence: how they look is the Elo rating in the code. The board does not say Elo.

Heat is the column with weight 0. A drop in the order is "fell," not "taking heat."

No accounts, no forum, no guest posting, no betting language.

## Locked, do not paraphrase

| Slot | Text |
| --- | --- |
| Tagline | How good they actually are. |
| Positioning | The order you check before you argue — not a poll, not a committee, not the narrative. |
| Brand | True Rankings |
| Rating name | TR+ |

## Landing and board

| Slot | On main today | PR #155 | Proposed |
| --- | --- | --- | --- |
| Home first screen | Brand, week line, tagline, positioning line, then a link "Jump to the board." The board follows a hero. | Pulls the table into the first viewport. Keep that. | The week board is the first paint. No "Jump to the board." |
| Week line | `{year} Week {week} · TR+ · through Saturday` | Unchanged in intent. | `2026 · Week 10` on this file, because it is the latest stored week. |
| Order line | The sort is the published blend, and the page does not say so in one line. | Still the blend, with corrected weights. | Ordered by how they look. Record, record quality, Heat, and early-season are columns. |
| Week movement | Stub prose can say "Taking heat" for a drop. | Not this redesign. | Miami went from No. 1 at 8-0 to No. 6 at 8-1. Utah is No. 1 at 9-0, up from No. 2. Ohio State fell from No. 13 to No. 31. Michigan State climbed from No. 85 to No. 55. |
| Case, No. 1 | No per-team case on the first screen. | Not this redesign. | Utah is No. 1 on how they look at 1,820.8, up from No. 2. They are 9-0 in the Big 12, 8-0 against Power 4, with 2 quality wins and 1 win off the FBS board. Georgia is 20.4 points behind. |
| Case, neighbors | None on the first screen. | Not this redesign. | Georgia is No. 2 at 1,800.3, 8-1, with 3 quality wins. UCLA is No. 3 at 1,780.8 and 9-0, 19.6 points back. The old blend had UCLA No. 2 and Georgia No. 3. |
| Case, record quality | None. | Not this redesign. | Liberty is 8-1 and No. 58 on how they look. The old blend had them No. 42, 16 places higher. Schedule rank 137 of 138. Quality wins: 0. One win is off the FBS board. The column shows that. The rank stays 58. |
| Column: rank | Rank | Keep. | The number of the how-they-look order. |
| Column: team | Team, conference in its own column | Keep the names. | Team, with the conference under the name. |
| Column: record | Record (wins-losses) | Keep the win-loss record. | Record. The win-loss line. Not the résumé score. |
| Column: move | Δ | Keep a move only if it is this order's move. | Not a column. The week line carries the moves. Δ on the old blend would be a second order. |
| Column: score | TR+ (the published blend, shown as the rating) | Keep TR+ as the product name. | TR+ stays the product name in the masthead. It is not a column of the old blend. |
| Column: record quality | Absent. | Absent. | Header: Record quality. Description: The old blend's place, and wins off this FBS board. The column does not change the rank. |
| Column: Heat | Absent. The word Heat is not a column. | Absent. | Header: Heat. Description: Weight 0. No number is stored on this file. Cell: an em dash, and for a screen reader "Not scored. Weight 0." |
| Column: early | Absent. | Absent. | Header: Early. Description: On when a team has fewer than 3 games. Cell this week: an em dash, and for a screen reader "Off. 9 games." |
| Playoff mark | A top-12 treatment already exists in the table component. | Leave the cutoff at 12. | Gold mark on ranks 1 through 12 only. Caption: Gold mark: the top 12 on this order. |
| Table caption | None of this text. | Do not revert the first-viewport table. | 2026 week 10. 138 teams. Ordered by how they look. Record quality is the old blend's place, and wins off this FBS board. Heat is weight 0. Early is on only under 3 games. None of these columns change the order. |

## Per-team line (any team)

Proposed template. Fill only from the week file. Omit a sentence when the field is missing. Do not invent a game.

`{Team} is No. {elo rank} on how they look at {how they look}, {record}, {conference}. {If the previous week exists: They were No. {previous} a week ago.} {quality wins} quality wins. {wins off the FBS board} wins off the FBS board. The old blend had them No. {blend rank}.`

The current stub says: "The board ranks them on who they beat and how they look — not the hype." That sentence describes the blend. Proposed replacement is the template above. PR #155 does not need to keep the stub sentence.

## Cross-conference

| Slot | On main today | Proposed |
| --- | --- | --- |
| Pair | No similar-strength pair on the board. | Indiana and Wake Forest are both 8-1. How they look: 1,700.3 and 1,698.3, 1.9 points apart. Schedule ranks 71 and 73 of 138. Indiana, Big Ten, is 5-1 against Power 4 with 0 quality wins. Wake Forest, ACC, is 6-1 against Power 4 with 1 quality win. Each has 1 win off the FBS board. The order is Indiana, then Wake Forest. |
| Second pair | None. | BYU and LSU are 2.2 points apart. BYU is No. 21, 7-2, Big 12, schedule rank 18. LSU is No. 22, 6-3, SEC, schedule rank 24. |
| Leagues | Conference table headers: #, Conference, Avg Rank, Teams, Power 4 W%, G5 W%, FCS W%. | Big 12 averages 1,740.0 and is 12-7 against Power 4. SEC 1,715.1, 11-2. Big Ten 1,693.2, 10-10. ACC 1,591.8, 8-12. The file's Pac-12 row is labeled Power 4, averages 1,194.6, and is 0-12 against Power 4. |
| Independents rollup | The file stores average 0 for FBS Independents. | The FBS Independents rollup on this file is 0. Notre Dame's own league number is 1,552.8. This page does not treat 0 as a measured league strength. |
| Section title | Conferences | Same strength, different leagues |

## Peers and what-if

| Slot | On main today | PR #155 | Proposed |
| --- | --- | --- | --- |
| What-if label | No what-if on main. | An exploratory weight control, labeled so it does not change the official board. Keep that rule. | What-if. This does not change the official board. |
| Open math | The methodology page shows one blend and calls it the board score. | That blend should read 0.80 / 0.15 / 0.05, matching the code. Keep those three numbers when the sentence is about the code. | At the slider state in the comp: 0.70 × how they look + 0.30 × résumé score + 0 × league strength + 0 × Heat. |
| Heat slider | Absent. | Absent. | Heat has no stored number. Its slider stays at 0. |
| Result of this state | Absent. | The explorer must not rewrite the official order. | At these weights Georgia is No. 5 on the what-if list. The official board still has Georgia No. 2. |
| Share | Share of the official top 25. | Keep official share honest. | Share the weights in the link. No account. Example path: /2026/week/10?whatif=70-30-0-0 |
| Peer table, official | Absent. | Absent. | Official. Weights 100 / 0 / 0 / 0. First three: Utah, Georgia, UCLA. This is the board. |
| Peer table, blend | Absent. | The corrected blend is the code's sort. | Published blend. Weights 80 / 15 / 5 / 0. First three: Utah, UCLA, Georgia. The code still sorts by this. It is a comparison. |
| Peer table, what-if | Absent. | Absent. | This what-if. Weights 70 / 30 / 0 / 0. First three: Utah, UCLA, Alabama. A comparison a link can carry. |

## Why this team is here

Sample: South Carolina, 2026 week 10. The same slots fill for every team.

| Slot | On main today | PR #155 | Proposed |
| --- | --- | --- | --- |
| Heading | Why here? opens a generated line. The modal then shows three weighted bars. | The bars become 80 / 15 / 5 and must sum to the published score. Keep that identity for any view of the old blend. | Why South Carolina is No. 12 |
| Ordering bar | How good they look 65%, Who they beat 27%, League strength 8%. | 80 / 15 / 5. Do not restore 65 / 27 / 8. | How they look, 1,662.2. This is the rank. The gap to No. 11 Iowa is 17.3 points. The gap to No. 13 Houston is 4.8 points. Both gaps are how they look. |
| Record | Inside the weighted résumé, not as the win-loss column of the reason. | The breakdown may still show the résumé term of the blend. Label it as the old blend if both stay on the page. | Record, beside the rank: 6-3, SEC. It does not set the rank. |
| Who they beat | "Who they beat (27%)." | Weight 15% if the bar is the blend. | 2 quality wins, 1 quality loss, 1 bad loss, 4-3 against Power 4, 1-0 against Group of 5, 1 win off the FBS board. |
| Schedule | Schedule fields exist on the model; the modal leads with the three weights. | Keep stored ranks. | Schedule rank 37 of 138. Victory rank 24 of 138. Those ranks do not set the order. |
| Game list | The modal tries to load game detail from the API. | No live call in this design pass. | The week file stores these counts. It does not store the game list, so this page does not invent scores. |
| Old blend on the team | Shown as the reason for the rank, at the wrong weights. | Shown as 80 / 15 / 5, which matches the code's score. | The old blend had them No. 20. The who-they-beat score is 1,308.0. That score is why the old order dropped them 8 places. |
| Heat on the team | Not shown. A design fixture under `design/comps/why-here-98/` uses an illustrative Heat number. Do not import it. | Absent. | Heat: weight 0. No number on this file. |
| Early on the team | Absent. | Absent. | Early-season: off. 9 games. |

## Formula page

| Slot | On main today | PR #155, keep | Proposed |
| --- | --- | --- | --- |
| Title | How the board works | Keep a plain title. | How the order works |
| Intro | Meathead version: who they beat + how they look + the league they live in. | The three parts are the code's blend, at 80 / 15 / 5. | Two blocks. The approved order is how they look alone. The old blend is what the code still publishes. |
| Mix | Board score = (0.65 × how they look) + (0.27 × who they beat) + (0.08 × league strength) | 0.80, 0.15, and 0.05. Do not go back to 0.65, 0.27, 0.08. | Approved order: the board is sorted by how they look, high to low. Heat's weight is 0. Record, record quality, Heat, and early-season are columns. |
| Old blend sentence | The 65/27/8 line is presented as the board. | One blend, corrected. | Old blend, still what the code publishes: 0.80 × how they look + 0.15 × résumé score + 0.05 × league strength. |
| Scale sentence | All components are normalized to a 0–100 scale before weighting. | Remove it. The code weights the raw numbers. | The parts are not scaled to 0–100 before weighting. On the 2026 week 10 file the old blend matches the stored score. 127 of 138 teams sit in a different place than how they look. The average gap is 5.99 places. |
| Deep-dive name | The page says Elo inside the nerdy sections and also misstates the constants. | Keep the code's constant values. | How they look is the Elo rating in the code. |
| K | Base volatility = 40. Reduced in postseason (0.6-0.7). | K is 50. Postseason factor is 0.65. | Step size is 50. A postseason game multiplies it by 0.65, so 32.5. |
| Home field | The running value is 50. The page has carried 65. | Home field 50. | Home field, in the expectation only: 50 in the regular season, 20 in the postseason, 0 on a neutral field. |
| Upset | 1.25× major upset, capped at 1.20×, and 1.20× cross-tier. | 1.18 when the gap is over 150, and 1.12 for a Group of 5 win over a Power 4 team. They stack. There is no 1.18 cap on the product. | A win over a team rated more than 150 points higher multiplies the step by 1.18. A Group of 5 win over a Power 4 team multiplies it by 1.12. They stack. The product is not capped at 1.18. |
| Margin | The nerdy section is incomplete relative to the code. | The code has no margin cap. | Margin moves the step by the natural log of the margin plus 1. There is no cap. |
| Matchup weights | The table of 1.0 / 0.8 / 0.65 / 0.2 / 0.1 is the part that already matches. | Keep those five numbers. | Power 4 vs Power 4 is 1.0. Power 4 vs Group of 5 is 0.8. Group of 5 vs Group of 5 is 0.65. FBS vs FCS is 0.2. Anything else is 0.1. |
| Ceiling | Not stated as 1,850 on the fan page. | The cap is 1,850, winner only. | No winner's rating goes above 1,850. The loser still drops the full step. |
| Starts and prior | 1500 / 1200 / 900 are on the page. The fade and the 0.70 / 0.30 prior are easy to miss. | Keep 1,500 / 1,200 / 900. | Before the games, a Power 4 team starts at 1,500, other FBS at 1,200, and FCS at 900, blended with 0.70 of last year's final score and 0.30 of the year before. |
| Fade and early | Not stated as this formula. | Do not invent a different fade. | The opening blend fades by max(0, 0.7 × (12 − week) / 11). Week 1 keeps 0.7. Week 10 keeps 0.127. Week 12 keeps 0. Early is a column, on when a team has fewer than 3 games. On 2026 week 1 every team is early. Indiana led that file at 1-0, how they look 1,827.4. On week 10 the flag is off for all 138 teams. |
| Heat | Not in the mix. | Do not add a Heat weight. | Heat's weight is 0. Three definitions were tested. Every weight above 0 fit worse than how they look alone on 2019–2022. No Heat number is stored, so the column is empty. |

## Words that stay off these surfaces

| Keep off | Why |
| --- | --- |
| bet, odds, spread, pick, lock, cover, projection | Removed product direction. |
| Jump to the board | The board is the page. |
| 65%, 27%, 8%, 0.65, 0.27, 0.08 | Stale. PR #155 removes them. This design does not bring them back. |
| Scaled to 0–100 before weighting | The code does not do that. |
| Taking heat, for a team that fell | Heat is the weight-0 column. |
| A made-up Heat value | The why-here-98 fixture is illustrative. It is not this file. |
| Sign in, post, forum, account | Still proposals. |
| Elo, on the board and the team case | Deep dive only, one sentence on the formula page. |

## Gold-band legend, before a committee column

Legal log D-20261112-15. The committee column is not on the board. Phil writes the new name in the empty cell. The rendered legend stays `CFP Playoff (1-12)` in `frontend/src/lib/components/RankingsTable.svelte` until that cell is filled and the column ships. This slot is the one that rename waits on. The "Playoff mark" proposal higher up is a separate redesign line.

| Slot | Rendered today | New name |
| --- | --- | --- |
| Gold 1-12 legend | CFP Playoff (1-12) | |
