# True Rankings front-end design brief

Proposed for Dean’s review and Phil’s copy pass. Neither has signed. This is a design comp and a copy table. It does not change the Svelte app or the ranking math.

Figures are from the stored 2026 week boards on this branch. The label is `v5.5`. The place is TR+, which is `ordering_score` and equals how they look. No live CFBD call and no live AI call.

The comp is `design/comps/elo-order-brief/preview.html`. `?shot=board`, `open`, `peers`, and `formula` are the still frames. Copy is in [phil-copy-table.md](phil-copy-table.md).

## What this leaves alone

[PR #155](https://github.com/merimeesoftware/cfb-ranking-algorithm/pull/155) corrected stale page numbers. This branch does not restyle that work. #156 sorts the board by Elo. #157 sets the upset multiplier that runs to 1.0. The Group of 5 bonus stays 1.12.

Michael signed the homepage order in the True Rankings chat on 2026-11-12 at 8:08 AM EST: “Yes, put this week’s rankings first on the homepage and update IDENTITY.md to match.” Later the same morning, at 8:16 AM EST, he said clicking a team does not go to a team page: the row expands in place, and the homepage is just the rankings, with a link like “How the formula works.” `IDENTITY.md` matches both. The rest of that file is unchanged.

Accounts, a forum, and guest posting stay proposals. Betting stays off the page.

## The order

**TR+.** Header `TR+`. Tooltip, verbatim: How good they look right now. This sets the order. The value is `ordering_score`.

**Beside the rank, not in it.** Record (overall, then conference). Record quality (wins ahead of what TR+ expected, and the share of wins that are soft). Early, on when a team has fewer than 3 games.

**Heat.** Heat is not in the order. It hasn’t passed its test yet. There is no Heat column and no Heat slider.

**Old blend.** For comparison: 0.80 × how they look + 0.15 × resume + 0.05 × league strength. The board no longer sorts by it. On 2026 week 10 that sum matches the stored blend. 121 of 138 teams sit in a different place. The average gap is 5.30 places. The parts are not scaled to 0–100 before weighting.

Fan sentences on the board say TR+. The formula page, the deep dive, may say that how they look is the Elo rating.

Locked lines, used verbatim: the tagline, the positioning line, `RATING_TOOLTIP`, and `EARLY_SEASON_NOTE`. Resume on the team page is “Resume” / “Who they beat, ranked.”

## Landing

The latest stored week is 2026 week 10. The comp opens on it. There is no “Jump to the board.”

The homepage is the rankings board, plus one link: “How the formula works.” At 390×844 at least four rows sit above the fold. The caption is one line. The rest is in “How to read this.” Empty Early cells are hidden under 640px, and one line says “Early: none this week.”

Gold is the band mark on ranks 1–12 only. Rank numerals in that band use `#8a7010` so they clear 4.5:1 on white. Rank 13 and below use ink `#14241c`. Row 13, Duke, is the non-band sample. “Show ranks 14–16” reveals Oregon, Texas Tech, and Houston in that same ink. “Find your team” filters the rows. Neither sits above the first rows.

Choosing a team expands that row. It does not open a team page. The opened row holds why the team is exactly there, the comparison with the teams on either side, and the evidence. South Carolina is the sample.

Week 1 is drawn under the table: Early is on, and Indiana is No. 1 on TR+ at 1,824.5, 1-0.

Other states, drawn under the table:

- Loading this week’s board.
- Couldn’t load this week’s board.
- This week isn’t published yet.

## Opened row

South Carolina’s row expands into a three-rung ladder. Iowa is the smaller rung above. South Carolina is the large rung: field rule, pip, conference, 6-3, and TR+ at the large figure size. Duke is the smaller rung below. The gaps are the difference of the numbers shown to one decimal: 22.4 behind No. 11 Iowa, 0.1 ahead of No. 13 Duke. It stays stacked at 390.

The line under the ladder: TR+ 1,653.0. This sets the rank. 22.4 behind No. 11 Iowa, 0.1 ahead of No. 13 Duke. Resume, schedule, and record quality sit in the same opened row.

## Same strength, and the what-if

Indiana and Wake Forest are both 8-1, 3.7 points apart on TR+. Baylor and SMU are 2.2 points apart. League averages are printed in the row text and on each dot: SEC 1,710.2, Big 12 1,702.1, Big Ten 1,658.5, ACC 1,578.6, Pac-12 1,154.3. The scale runs from 1,100 to 1,800.

The what-if sits under the formula explainer, not on the homepage. The frame is labeled “Example only.” Three sliders (how they look, resume, league strength) are enabled, 44px tall, and show their value. Moving one rebalances the other two so the three sum to 100. One weight at 100 sets the others to 0. Reset returns 100 / 0 / 0, and the what-if list matches the official order. A tie keeps the official order. The official list never changes.

The starting state is 70 / 30 / 0. Georgia is No. 4 on that list and No. 1 on the official board. The old blend list is a comparison: Utah, Georgia, Alabama. There is no second table of the same three orders.

There is no Copy link and no share line. The board does not read `?whatif=`. When #178 reads it, the share text is “My what-if weights, not the official board: {url}” and the error is “Link weights didn’t load. See the board.” On a narrow board, TR+ sits on the team line, right-aligned beside the name, so at least four full rows fit at 390×844.

## Formula

Two blocks. The order is TR+. The old blend is the comparison, with the running constants: K 50, postseason ×0.65, margin ln(margin + 1), home field 50 / 20 / 0, Group of 5 over Power 4 ×1.12 and no other upset bonus, matchup weights 1.0 / 0.8 / 0.65 / 0.2 / 0.1, winner ceiling 1,850. The opening paragraph is `EARLY_SEASON_NOTE` word for word. One deep-dive line gives the fade: max(0, 0.7 × (12 − week) / 11).

## Tokens

Existing identity colors stay: field `#1a3d2e`, deep `#0f241b`, chalk `#eef1ee`, ink `#14241c`, band gold `#c9a227`.

Added for this comp, because the identity gold fails contrast for small numerals on white:

| Token | Value | Use |
| --- | --- | --- |
| Rank gold | `#8a7010` | Rank numerals 1–12 only |
| Muted | `#3d5248` | Secondary ink on chalk |
| Line | `#c9d4cc` | Hairline on chalk |
| Mast soft | `#d5e0d8` | Positioning line on deep green |
| Card | `#ffffff` | Cards and the table ground |
| Read | `42rem` | Prose measure, about 670px |

Team pips are the `color` stored on that team’s week row. They are not a new palette.

Focus ring is 3px field `#1a3d2e`, which is about 12:1 on white. On the dark mast the ring is chalk.

## Checks for a later build

These are the assertions. They are not registered in `design/comps/manifest.json`, because that checker photographs the app, not this comp. Signing them there would fail the app pixel check.

- Order equals `ordering_score`, high to low.
- Gold band only on ranks 1–12. Numerals below 12 are ink.
- The what-if list never rewrites the official rows.
- Slider hit area at least 44px. Buttons at least 44px.
- Focus ring at least 3:1 against the surface behind it.
- No horizontal overflow at 390.
- At 390×844, at least four board rows are above the fold.
- Heat is absent from the board and from the sliders.

## For the next build, after review

The in-browser what-if recompute, reading `?whatif=`, and shipping record quality as a stored column need Archie before a build. A public name other than TR+, or Heat on the board before its test, is a PURPOSE change for Michael.
