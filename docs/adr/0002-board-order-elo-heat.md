# ADR 0002: The board is ordered by Elo

- **Status:** Proposed with this change. Heat weight stays 0. Issue #96 stays open.
- **Cites:** [ADR 0001](0001-product-direction-2026-10-18.md) (2026-10-18). Decision D-20261018-198 asked for Elo plus Heat, and for Heat to stay at weight 0 when it misses its gate. D-20261019-335 makes 2025 the holdout. 2024 is a mid-gate check, not that holdout.
- **Algo label:** `v5.5`. The label is the cache key for the order and for a stored week. It is not a weight. `v5.4` still carried the 1.18 upset step.

## Decision

1. **The place is Elo.** `ordering_score` is `team_quality_score`. Teams are sorted by that number, high to low. The old blend `0.80 × Elo + 0.15 × record + 0.05 × conference quality` is still computed as `final_ranking_score` and is not the order. The headline number shown next to a place is `ordering_score`.
2. **Heat weight is 0.** Issue #96's gate was not run as a formal artifact in this repo (no result on the issue, no committed protocol output). Per ADR 0001, a missing or inconclusive gate keeps the ordering weight at 0 and leaves #96 open. A separate scoring note tried three display features (last-3 surprise, dominant-win size, and Elo change over three games). Every positive weight was worse on 2019–2022, so none of them is in the sort. A later column for recent form, if it ships, is named Momentum. It is not the #96 Heat form, and it does not enter the sort unless a non-zero weight passes the #96 gate on the sealed 2025 holdout.
3. **The record is display-only.** Record quality and a recent-form column are not in this change. They do not move the place.
4. **Conference still enters the early order through the prior.** Tier starts stay (1500 / 1200 / 900). Flat 1500 starts were worse. Weeks 1–11 also seed Elo from last season's published score, which is the blend, not Elo. That seed stays: replacing it with an Elo-only prior was not better on the tune or on 2023. Week 1 keeps 70% of that stored prior, which is about 49% of last year and 21% of the year before. From week 12 the prior weight is 0.
5. **2025 is untouched.** It is the holdout. Nothing in this record is a 2025 result.

## Paired Brier

Home field is the ranker's 50. Regular season, weeks 1–15, at least one FBS team, postseason left out, cold priors 0.70/0.30, season membership map. Difference is blend minus Elo. Positive means the blend is worse. Week-bootstrap 95% intervals are from an independent re-run (2,000 week resamples). This is not the stored eval table, which used home field 65.

| Window | Games | Blend − Elo | 95% CI |
| --- | ---: | ---: | --- |
| Tune 2019–2022 | 3,074 | +0.00307 | [+0.00089, +0.00524] |
| Validate 2023 | 868 | +0.00443 | [−0.00119, +0.01007] |
| 2024 mid-gate | 872 | +0.00527 | [+0.00098, +0.01010] |

Elo is not worse on any window. 2023's interval crosses zero. The blend-versus-Elo scores come from `scripts/monotonicity_counts.py`. The week-bootstrap intervals in this table are the independent re-run recorded in `docs/elo-order-brier.json` (`blend_minus_elo.source`). They are not from `scripts/paired_order_brier.py`.

## Upset step

A later change on this stack removes the ×1.18 upset step at a 150-point live gap. A bigger earlier win can push that later gap under 150 and take the bonus away, so the season-end Elo falls. With the step removed (`upset_bonus_mult` 1.0), the same offline protocol, difference is bonus-off minus current (negative means removing the step is better):

| Window | Games | Bonus 1.0 − current | 95% CI |
| --- | ---: | ---: | --- |
| Tune 2019–2022 | 3,076 | −0.00024 | [−0.00057, +0.00007] |
| Validate 2023 | 868 | −0.00009 | [−0.00065, +0.00042] |
| 2024 mid-gate | 872 | −0.00021 | [−0.00063, +0.00019] |

Point estimates are not worse. The intervals cross zero. The step is removed because it breaks monotonicity and the rating does not get worse. Those intervals are from `scripts/paired_order_brier.py` (`--compare upset`), recorded in `docs/elo-order-brier.json` under `upset_bonus_1_minus_current`.

## Consequences

- Rank and the number beside it have to be `ordering_score`. A lower place must not show a higher rating.
- `ALGO_VERSION` is `v5.5`, so a computed cache from `v5.4` is not reused. Committed static boards are still served. Committed prior files stay `v5.3` on purpose: they are the blend seed, and 2025 is not regenerated.
- Methodology copy that said 0.65 / 0.27 / 0.08, or that parts are scaled to 0–100 before weighting, was describing a different formula. The methodology page still names Elo. The board, team panel, title, and share copy call the rating TR+.
