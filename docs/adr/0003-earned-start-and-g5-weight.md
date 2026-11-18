# ADR 0003: Earned start and G5 weight

- **Status:** Proposed with this change. Michael chose both A and C (TR chat 2026-11-18, t283u). Archie mechanism-review on issue #202 is REVISE; this record is Fixes 1–3. Not accepted until Archie re-checks.
- **Decided by:** Michael Merimee (formula: both A and C). Archie (mechanism). This ADR does not open the 2025 holdout.
- **Related:** Issue #202. Supersedes [ADR 0002](0002-board-order-elo-heat.md) decision 4 only. [ADR 0001](0001-product-direction-2026-10-18.md) still governs a failed gate. D-20261019-335 keeps 2025 sealed. Issue #96 runs after this change, on the new Elo, and was not run here.
- **Algo label:** `v5.6`. Committed prior files stay `v5.3`. They are not regenerated.

## Decision

1. **(A) G5 vs G5 weight is 1.0.** The matchup table lives once in `DEFAULT_CONFIG`: P4–P4 `mw_p4_p4` 1.0, P4–G5 `mw_p4_g5` 0.8, G5–G5 `mw_g5_g5` 1.0, FBS–FCS `mw_fbs_fcs` 0.2, FCS–FCS `mw_fcs_fcs` 0.1. P4–G5 stays 0.8. B was not adopted.
2. **(C) The start is the tier rating plus a held offset.** `start = tier + clamp(prior_offset_strength × offset, ±prior_offset_cap)`. `prior_offset_strength` is **0.4** (the tune pick below). `prior_offset_cap` is 150 Elo. `prior_offset_weights` are 0.70 then 0.30, renormalized over seasons the team actually has. There is no week fade. `prior_strength`, the fading schedule, and the old tier/FRS blend are gone. A request cannot set these keys or any `*_override` key.
3. **Offset definition.** For season y, `offset_y = FRS_y(team) − mean FRS_y` of that team's tier in season y. The tier is the season-y membership map. The mean uses FBS teams only (Power 4 and Group of 5). A team with no FBS season in the two-year window has offset 0 and starts at the tier rating. Tier changers are measured against the tier they were in during season y, not the tier they are in now.
4. **History enters once.** The next prior is a results-only replay when a committed file is missing: offset strength 0, tier starts. Committed `priors/2022.json` through `priors/2025.json` stay the v5.3 blend seed. Tier means are computed at run time from those files. 2025 game rows are not read.
5. **The place is still Elo.** Heat weight stays 0 (ADR 0002 decision 1). Résumé, SoS, SoV, quality wins, and bad losses stay display-only. SoS rank and SoV rank are taken over FBS teams only. Ties in the order break by team name.

## Strength rule (stated before the tune run)

`prior_offset_strength` is chosen only on 2019–2022, from {0.3, 0.4, 0.5, 0.6, 0.7}, by the lowest FBS-vs-FBS Brier of C-held (G5–G5 weight still 0.65, so A does not pick the strength). A tie goes to the value closer to 0.5, then to the lower value. 2023 and 2024 are confirmations. 2026 and the polls are not used.

## Pass bars (written before any 2025 run)

Home field is 50. Weeks 1–15. At least one FBS team. Postseason is out. Week-bootstrap 95% interval, 2,000 resamples, seed 20261111. Difference is the new arm minus the baseline. Positive means the new arm is worse.

- **C, 2025, FBS vs FBS only.** C passes if the 95% upper bound of (C-held − main) is below 0. Cross-tier calibration `|mean predicted home win − actual home win rate|` on Power 4 vs Group of 5 must be no worse than main + 0.02. The FCS level fix cannot carry this bar.
- **A, non-inferiority.** A passes if the 95% upper bound of (A+C − C) is at most +0.002.
- **Echo bar (stated before the 2023→2024 replay).** Keeping the published v5.3 seed is allowed only if the mean absolute change in 2024 starting Elo from dropping the 2022 (Y-2) offset is at most 25 Elo, and no team's start moves by more than `prior_offset_cap` (150).
- **2025 result:** PENDING. Not run. D-20261019-335 was not opened. 2025 boards were not restated.

If an arm fails its 2025 bar, it does not ship (ADR 0001). This pull request is a draft so that re-check can happen before a 2025 run.

## Measurement

From `scripts/paired_order_brier.py` after the bars above. Recorded in `docs/earned-start-brier.json`. Seeds are a one-pass results-only replay (offset 0, G5–G5 weight 0.65) of 2017–2023 game rows. That replay does not read 2025. C-faded uses `0.4 × max(0, (12 − week) / 11)`. Main still uses `max(0, 0.7 × (12 − week) / 11)` on the old un-demeaned 0.70/0.30 FRS blend. Difference is the new arm minus the baseline. Positive means the new arm is worse.

Chosen strength on tune FBS-vs-FBS Brier: **0.4**.

| Strength | n | FBS-vs-FBS Brier |
| --- | ---: | ---: |
| 0.3 | 2,689 | 0.18911 |
| **0.4** | 2,689 | **0.18839** |
| 0.5 | 2,689 | 0.18866 |
| 0.6 | 2,689 | 0.18950 |
| 0.7 | 2,689 | 0.19030 |

C-held minus main, FBS vs FBS only. The 2025 bar (upper bound below 0) is **not met** on 2019–2024. The point estimate on the pool is slightly better. Every interval crosses zero.

| Window | n | Point | 95% CI | Upper below 0 |
| --- | ---: | ---: | --- | --- |
| Tune 2019–2022 | 2,689 | −0.00038 | [−0.00210, +0.00121] | no |
| Validate 2023 | 750 | +0.00099 | [−0.00194, +0.00369] | no |
| 2024 | 751 | −0.00240 | [−0.00556, +0.00077] | no |
| 2019–2024 | 4,190 | −0.00050 | [−0.00184, +0.00080] | no |

A+C minus C-held, games with at least one FBS team. The non-inferiority bar (upper bound at most +0.002) **passes on the 2019–2024 pool** and on the tune window. It does not pass on 2023 alone or on 2024 alone.

| Window | n | Point | 95% CI | Upper ≤ +0.002 |
| --- | ---: | ---: | --- | --- |
| Tune 2019–2022 | 3,076 | +0.00070 | [−0.00022, +0.00167] | yes |
| Validate 2023 | 868 | +0.00026 | [−0.00206, +0.00256] | no |
| 2024 | 872 | +0.00056 | [−0.00135, +0.00249] | no |
| 2019–2024 | 4,816 | +0.00060 | [−0.00020, +0.00142] | yes |

A alone minus main, same games, 2019–2024: point +0.00043, 95% CI [−0.00036, +0.00124]. The point estimate is slightly worse. The upper bound is inside +0.002.

Cross-tier calibration `|mean p − actual|` on Power 4 vs Group of 5. C-held is within main + 0.02 on every window below. 2023 is the only window where C-held is worse than main, by 0.0023.

| Window | Main | C-held | A+C |
| --- | ---: | ---: | ---: |
| Tune 2019–2022 | 0.0116 | 0.0059 | 0.0053 |
| Validate 2023 | 0.0108 | 0.0131 | 0.0127 |
| 2024 | 0.0105 | 0.0012 | 0.0010 |
| 2019–2024 | 0.0071 | 0.0008 | 0.0010 |

C-level-only (offset strength 0, no fade) is worse than main on the pool: point +0.00785, 95% CI [+0.00536, +0.01053]. The held offset is what brings C back next to main. C-faded at 0.4 is also slightly worse on the pool (point +0.00115, CI [−0.00011, +0.00236]).

**2025 result:** PENDING. Not run.

## Results-dominate

C-held versus C-level-only at G5 weight 1.0, so the only difference is the offset. The start still explains about half of week-12 Elo variance. The order is almost the same (Spearman about 0.99). The largest place shift is 16.

| Year | Week | Spearman | Largest place shift | Team | R² of final Elo on the start |
| --- | ---: | ---: | ---: | --- | ---: |
| 2023 | 12 | 0.993 | 16 | Cincinnati (84 → 68) | 0.581 |
| 2023 | 15 | 0.994 | 12 | BYU (74 → 62) | 0.546 |
| 2024 | 12 | 0.993 | 16 | Oklahoma (77 → 61) | 0.577 |
| 2024 | 15 | 0.996 | 9 | Buffalo (75 → 84) | 0.542 |

## Echo

2024 starts from the committed v5.3 files for 2023 and 2022, versus 2023 only. 134 FBS teams. Mean absolute change **19.63 Elo**. Max **73.82 Elo**. Both are inside the bar stated above (25 and 150). The published-blend seed stays. The prior files were not rewritten.

## Boards

2024 weeks 1–15 and 2026 weeks 1–10 are regenerated under v5.6 at strength 0.4. 2025 week boards are not created. Prior files are not rewritten. 2024 games are the local CFBD dump used by the paired script. 2026 games are the sportsdataverse 2026 schedule CSV (FBS home games, including FCS visitors). Lower-division-only games are not in that file. This was not a CFBD call.

## Copy note for Phil

Wording on the formula page is Phil's. These facts have to be on the page. The constants in `frontend/src/routes/methodology/+page.svelte` and `EARLY_SEASON_NOTE` were updated to match the code so the page is not false while Phil rewrites it.

1. Group of 5 vs Group of 5 is 1.0. The old "dampened to prevent inflation" line does not belong. Power 4 vs Group of 5 stays 0.8.
2. A team starts at its tier rating (1500 / 1200 / 900) plus 0.4 of how far its last two FBS seasons sat above or below that season's tier average. That head start stays all season. It applies to Power 4 teams too.
3. A team new to FBS, or with no FBS season in that two-year window, starts at the tier average.
4. Method change, 2026-11-18: the stored 2024 and 2026 boards were recomputed that date, so places moved because the method changed, not because new games were added. On 2026 week 10, UCLA moved from No. 5 to No. 9 and Boise State moved from No. 44 to No. 28. On 2024 week 15, Boise State moved from No. 41 to No. 23. 2025 boards were not restated.
5. `ALGORITHM_BREAKDOWN.md` was corrected in this change: home field 50, K 50, blend 80/15/5, upset step off, G5–G5 weight 1.0, held offset. The old 65 / 40 / 27% / 8% lines are gone.

## Consequences

- Reverting the G5-weight commit restores 0.65 without removing the offset. Reverting the offset commit restores the fade and v5.5 once the boards in that commit are reverted with it.
- A raises Group of 5 conference-game Elo swings by 1/0.65 ≈ 1.54×. A later Momentum or Heat feature built on Elo deltas has to be checked for tier bias.
- Shown résumé ranks move because opponent Elo moves, and because SoS/SoV rank is now FBS-only. They still do not set the place.
- #96 is not re-baselined here.
