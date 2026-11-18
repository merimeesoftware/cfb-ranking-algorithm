# ADR 0003: G5-G5 weight

- **Status:** Proposed with this change. Michael (2026-11-18): ship A, hold C. Archie re-check on pull request #203 is REVISE. This record is the A-only ship. It does not supersede [ADR 0002](0002-board-order-elo-heat.md) decision 4. The week fade stays live.
- **Decided by:** Michael Merimee (ship A, hold C). Archie (mechanism re-check).
- **Related:** Issue #202. Pull request #203. Held branch `held/earned-start-c` at `b99897b068a671b689353ce4610290aec7622199` keeps C and is not merged. D-20261019-335 still seals 2025.
- **Algo label:** `v5.6` is this weight only. It is not the held offset. Committed prior files stay `v5.3`.

## Decision

1. **Group of 5 vs Group of 5 weight is 1.0.** The matchup table in `DEFAULT_CONFIG` is P4–P4 1.0, P4–G5 0.8, G5–G5 1.0, FBS–FCS 0.2, FCS–FCS 0.1. P4–G5 stays 0.8. A request cannot set these weights.
2. **C is held.** The history offset does not ship. The fade in ADR 0002 decision 4 stays. C's code stays on `held/earned-start-c`.
3. **Lab home field matches the ranker.** `algo_lab/predict.py` uses home field 50, the same value the ranker and this protocol use.

## Pass bars (written before any 2025 run)

Home field 50. Weeks 1–15. At least one FBS team. Postseason out. Week-bootstrap 95% interval, 2,000 resamples, seed 20261111. Difference is the new arm minus the baseline. Positive means the new arm is worse. Strength, if C had shipped, would have been chosen only on 2019–2022 FBS-vs-FBS Brier from {0.3, 0.4, 0.5, 0.6, 0.7}. The lowest was 0.4 (0.18839). 0.5 was 0.18866. 2023, 2024, 2026, and the polls were not used to pick it.

- **C, FBS vs FBS.** C passes only if the 95% upper bound of (C-held − main) is below 0. Cross-tier `|mean predicted home win − actual|` on Power 4 vs Group of 5 must be no worse than main + 0.02.
- **A, non-inferiority.** A passes if the upper bound of (A+C − C) is at most +0.002. The written fallback is: ship A alone when A is no worse than main on 2019–2024, upper bound at most +0.002.
- **2025 result:** PENDING. Not run. D-20261019-335 was not opened. 2025 boards were not restated.

## Recorded result

From `scripts/paired_order_brier.py`, stored with the held commit. This ADR does not re-run it and does not read 2025.

| Comparison | 2019–2024 | 95% CI | Call |
| --- | ---: | --- | --- |
| C-held − main, FBS vs FBS | −0.00050 | [−0.00184, +0.00080] | Upper bound is not below 0. Every window misses. **C held.** |
| A+C − C-held | +0.00060 | [−0.00020, +0.00142] | Upper bound is within +0.002 on the pool and on the tune window. Misses 2023 alone and 2024 alone. |
| A alone − main | +0.00043 | [−0.00036, +0.00124] | No worse on 2019–2024. **A ships.** |

Cross-tier `|pred − actual|` for C-held stayed within main + 0.02 on every window (2023 was the only window worse than main, by 0.0023). That does not carry C. The FBS-vs-FBS bar is the one C missed.

## Consequences

- 2024 weeks 1–15 and 2026 weeks 1–10 are regenerated under this weight. The deploy uploads those files. It does not recompute them.
- Prior files stay v5.3. 2025 week boards are not created.
- The opening rating and the fade are unchanged.
- #96 is still after this change, on the new Elo, and was not run.
