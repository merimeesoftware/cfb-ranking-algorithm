# Phil copy table — Elo-order redesign

Proposed copy for Phil. Not signed. Dean has not signed the comp.

Facts are from the v5.5 week boards on this branch (current main, after #156, #157, and #166). The place is TR+. Curly apostrophes are part of the public sentences.

## Locked, do not paraphrase

| Slot | Text | Source |
| --- | --- | --- |
| Tagline | How good they actually are. | PURPOSE |
| Positioning | The order you check before you argue — not a poll, not a committee, not the narrative. | PURPOSE |
| Brand | True Rankings | PURPOSE |
| Rating name | TR+ | `RATING_NAME` |
| Rating tooltip | How good they look right now. This sets the order. | `RATING_TOOLTIP` |
| Early-season note | In week 1, 70% of a team’s starting rating comes from last season’s final rating (bowl games included) and the season before, weighted 70/30. The other 30% comes from its conference tier. A team with no rating from last season starts from its tier alone. The head start shrinks each week and is gone by week 12. | `EARLY_SEASON_NOTE` |
| Resume header | Resume | #98 |
| Resume description | Who they beat, ranked. | #98 |
| Nav, formula | How the formula works | `NAV.formula` |

## Landing and board

| Slot | Proposed |
| --- | --- |
| Week line | Miami fell from No. 1 at 8-0 to No. 6 at 8-1. Georgia climbed from No. 3 to No. 1 at 8-1. Ohio State fell from No. 11 to No. 27. Michigan State climbed from No. 78 to No. 54. |
| Case, No. 1 | Georgia is No. 1 on TR+ at 1,806.1, 8-1, 6-1 in the SEC. Utah is 9.5 points behind. |
| Case, neighbors | Utah is No. 2 on TR+ at 1,796.6, 9-0, 6-0 in the Big 12. The old blend has Utah No. 1 and Georgia No. 2. The official order does not. |
| Case, record quality | Liberty is No. 53 on TR+ at 1,386.4, 8-1, 5-0 in Conference USA. The record is 2.04 wins ahead of what TR+ expected, and 88% of the wins are soft. The rank stays 53. |
| Caption | 2026 week 10. 138 teams. Ordered by TR+. |
| How to read this | TR+ sets the order. Record quality is wins ahead of what TR+ expected, and the share of wins that are soft. Early is on when a team has fewer than 3 games. None of these columns change the rank. Gold marks ranks 1 through 12. Ranks 13 and below use ink. |
| Column: TR+ | Header `TR+`. Tooltip: How good they look right now. This sets the order. |
| Column: record | The win-loss line, then the conference line. Georgia: 8-1, 6-1 in the SEC. |
| Column: record quality | Wins ahead of what TR+ expected, and the share of wins that are soft. South Carolina: 1.13 wins ahead, 50% soft. |
| Column: early | On when a team has fewer than 3 games. This week the shown rows are off. The screen reader uses that team’s game count. |
| Early, none this week | Early: none this week. |
| Early, week 1 | 2026 week 1. Early is on for every team. Indiana is No. 1 on TR+ at 1,824.5, 1-0. |
| Find your team | Find your team |
| Show more | Show ranks 14–16 |
| Loading | Loading this week’s board. |
| Error | Couldn’t load this week’s board. |
| Empty | This week isn’t published yet. |

## Per-team line

`{Team} is No. {rank} on TR+ at {tr_plus}. {record}, {conference}. They were No. {previous} a week ago. {quality_wins} quality wins.`

Omit the previous-week sentence when that week is missing.

## Cross-conference

| Slot | Proposed |
| --- | --- |
| Pair | Indiana and Wake Forest are both 8-1. TR+ 1,697.7 and 1,694.0, 3.7 points apart. The order is Indiana, then Wake Forest. |
| Second pair | Baylor and SMU are 2.2 points apart. Baylor is No. 19, 6-3, 4-2 in the Big 12, schedule rank 59. SMU is No. 20, 7-2, 5-2 in the ACC, schedule rank 63. |
| Leagues | SEC 1,710.2, 10-2 against Power 4. Big 12 1,702.1, 6-7. Big Ten 1,658.5, 4-10. ACC 1,578.6, 6-12. Pac-12 1,154.3, 0-12. |

## What-if

The frame is labeled `Example only`. The sliders move a comparison list. They do not change the official rows.

| Slot | Proposed |
| --- | --- |
| Frame | Example only |
| Banner | What-if. This does not change the official board. |
| Open math, starting state | 0.70 × how they look + 0.30 × resume + 0 × league strength. |
| Result of that state | At these weights Georgia is No. 4 on the what-if list. The official board still has Georgia No. 1. |
| Reset | Reset to official |
| Old blend | Old blend. Weights 80 / 15 / 5 / 0. A comparison, not the board. |
| Heat | Heat is not in the order. It hasn’t passed its test yet. |

No share line on the page. The board does not read `?whatif=`. When that parameter is read, the share text is `My what-if weights, not the official board: {url}` and the error is `Link weights didn’t load. See the board.`

## Opened row

Sample: South Carolina, 2026 week 10, expanded in place. Gaps are the difference of the TR+ numbers shown to one decimal. The homepage link is “How the formula works.”

| Slot | Proposed |
| --- | --- |
| Heading | Why South Carolina is No. 12 |
| Open control | The team name is a button. It expands the row. It does not open a team page. |
| Rank line | TR+ 1,653.0. This sets the rank. 22.4 behind No. 11 Iowa, 0.1 ahead of No. 13 Duke. |
| Record | 6-3, 4-3 in the SEC. Beside the rank. It does not set the rank. |
| Resume | Who they beat, ranked. 2 quality wins, 1 quality loss, 1 bad loss. 4-3 against Power 4. |
| Schedule | Schedule rank 33 of 138. It does not set the order. |
| Record quality | 1.13 wins ahead of what TR+ expected. 50% of the wins are soft. The old blend has them No. 19. |
| Early | Off. 9 games. |
| Games | Game scores aren’t on this page. |

## Formula page

The page heading is `NAV.formula`, the same string as the top-bar link.

| Slot | Proposed |
| --- | --- |
| Heading | How the formula works |
| Order | How good they look right now. This sets the order. |
| Old blend | For comparison, the old blend: 0.80 × how they look + 0.15 × resume + 0.05 × league strength. The board no longer sorts by it. |
| Scale | The parts are not scaled to 0–100 before weighting. On 2026 week 10, 121 of 138 teams sit in a different place. The average gap is 5.30 places. |
| Deep-dive name | How they look is the Elo rating in the code. |
| Step size | 50. A postseason game multiplies it by 0.65, so 32.5. |
| Margin | The natural log of the margin plus 1. There is no cap. |
| Home field | 50 in the regular season, 20 in the postseason, 0 on a neutral field. It changes the expectation only. |
| Upset | A Group of 5 win over a Power 4 team multiplies the step by 1.12. There is no other upset bonus. |
| Matchups | Power 4 vs Power 4 is 1.0. Power 4 vs Group of 5 is 0.8. Group of 5 vs Group of 5 is 0.65. FBS vs FCS is 0.2. Anything else is 0.1. |
| Ceiling | No winner’s rating goes above 1,850. The loser still drops the full step. |
| Opening | The `EARLY_SEASON_NOTE` sentence, word for word. |
| Fade | max(0, 0.7 × (12 − week) / 11). Week 1 keeps 0.7. Week 10 keeps 0.127. Week 12 keeps 0. |
| Heat | Heat is not in the order. It hasn’t passed its test yet. |

## Words that stay off these surfaces

| Keep off | Why |
| --- | --- |
| bet, odds, spread, pick, lock, cover, projection, The Drop | Removed product direction. |
| Jump to the board | The board is the page. |
| 65%, 27%, 8%, 0.65, 0.27, 0.08 | Stale. PR #155 removes them. This design does not bring them back. |
| Scaled to 0–100 before weighting | The code does not do that. |
| Heat as a board column or a slider, and a made-up Heat value | Heat is the weight-0 column. The why-here-98 fixture is illustrative. It is not this file. |
| Sign in, post, forum, account, guest posts | Still proposals. |
| A share line before `?whatif=` is read | The board does not read that parameter yet. |
| Elo, on the board and the team case | Deep dive only, one sentence on the formula page. |

## Gold-band legend, before a committee column

Legal log D-20261112-15. The committee column is not on the board. Phil writes the new name in the empty cell. The rendered legend stays `CFP Playoff (1-12)` in `frontend/src/lib/components/RankingsTable.svelte` until that cell is filled and the column ships. This slot is the one that rename waits on. The "Playoff mark" proposal higher up is a separate redesign line.

| Slot | Rendered today | New name |
| --- | --- | --- |
| Gold 1-12 legend | CFP Playoff (1-12) | |
