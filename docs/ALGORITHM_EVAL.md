# Algorithm Evaluation Sandbox

How we prove the ranking algorithm is a good predictor of game outcomes — and how
we improve it without fooling ourselves.

## Why this exists

Published rankings (FRS) answer “who deserves to be ranked where?” Predictive
strength answers a harder question: **given only information available before
kickoff, how often does the higher-rated team win, and how well-calibrated are
the probabilities?**

Those are related but not identical. Resume bonuses (quality wins, undefeated
multipliers, conference quality) help a human-facing poll. **Next-game prediction
should primarily use Team Quality (Elo)** — the component that models strength.

## Leak-free protocol

For season `Y`, outcome week `W`:

1. Build ratings using **only** games with `week <= W-1` (preseason for `W=1`).
2. Convert ratings → `P(home wins)` with logistic Elo + HFA (same 400-scale / HFA
   rules as `TeamQualityRanker`).
3. Compare to the actual week-`W` results.
4. Aggregate with **proper scoring rules**.

Allowed at the start of season `Y`: priors from `Y-1` and `Y-2` (known history).  
Forbidden: any game from week `W` (or later) when forming the rating used to
predict week `W`.

```
Week 1 ratings (preseason) → predict Week 1 games
Week 1 results → Week 1 ratings → predict Week 2 games
…
Week N results → Week N ratings → predict Week N+1 games
```

## Metrics (what “better” means)

| Metric | Good direction | Coin-flip reference | Notes |
|--------|----------------|---------------------|-------|
| **Brier score** | Lower | ~0.25 | Primary objective; rewards calibrated probs |
| **Log loss** | Lower | ~0.693 | Harsh on confident wrong calls |
| **Accuracy** | Higher | ~0.50 | Secondary; ignore alone (can reward overconfidence) |

Always report lift vs baselines:

- **Coin flip** — `p=0.5`
- **Always home** — constant ~0.55 home win rate
- **Equal Elo + HFA** — all teams 1500, only home-field separates them

A ranking system that cannot beat “always home” on Brier is not yet a useful
predictor.

## Code map

| Path | Role |
|------|------|
| `algo_lab/predict.py` | Elo → `P(home)` |
| `algo_lab/metrics.py` | Brier / log-loss / accuracy |
| `algo_lab/runner.py` | Pure recompute through week N (no API I/O) |
| `algo_lab/backtest.py` | Week-by-week protocol + baselines |
| `algo_lab/sweep.py` | Discrete hyperparameter grid search |
| `algo_lab/baselines.py` | Naive predictors |
| `scripts/backtest_rankings.py` | CLI for real seasons |
| `tests/test_algo_lab.py` | Offline synthetic league tests |

Production ranking code (`ranking_algorithm.py`, `ranking_service.py`) stays the
source of truth for math. The lab **imports** it; it does not fork a second algo.

## How to run

### Unit / synthetic (always offline)

```bash
./venv/bin/pytest tests/test_algo_lab.py -q
```

### Real seasons (needs game data)

Warm `.cache/` once (or allow a capped live pull):

```bash
# Prefer cache hits after a prior precompute / rankings run
CFBD_OFFLINE=0 CFBD_MAX_CALLS=25 \
  ./venv/bin/python scripts/backtest_rankings.py --years 2024 --max-week 10

# Elo vs FRS as predictors
./venv/bin/python scripts/backtest_rankings.py --years 2024 --rating-field team_quality_score
./venv/bin/python scripts/backtest_rankings.py --years 2024 --rating-field final_ranking_score

# Small K / HFA sweep (expensive: many full recomputes)
./venv/bin/python scripts/backtest_rankings.py --years 2023 --max-week 8 --sweep
```

Static files under `frontend/static/rankings/` are **outputs**, not game logs —
backtests need raw games from CFBD/cache.

## How to “train” / improve (properly)

This is **model selection**, not neural net training:

1. **Freeze a protocol** — the leak-free week-by-week backtest above.
2. **Split seasons** — e.g. tune on 2019–2022, validate on 2023, final report on 2024+.
   Never peek at the test season while choosing parameters.
3. **Optimize Brier** (or log-loss) on the validation split via `algo_lab.sweep`.
   High-leverage Elo knobs first: `base_factor` (K), `hfa_elo`, upset multipliers.
4. **Then** tune FRS blend weights (`team_quality_weight` / `record_weight` /
   `conference_weight`) for *ranking* quality (top-25 stability, playoff slate
   agreement) — separate from predictive Elo calibration.
5. **Promote** winning configs into `DEFAULT_CONFIG` / `ALGORITHM_BREAKDOWN.md`
   only after test-season confirmation and a recorded before/after table.

### What not to do

- Optimize accuracy alone.
- Fit parameters on the same season you report as “proof.”
- Use week-`W` FRS (which includes week-`W` resume) to “predict” week-`W` games.
- Declare superiority from one week’s top-25 smell test.

## Suggested research loop

1. Establish baseline Brier for current V5.1 on 2022–2024.
2. Sweep K and HFA; keep if validation Brier improves ≥ ~0.005 and test holds.
3. Probe whether iterative `reference_ranks` should actually feed Elo (today the
   arg is unused — iterations mainly enable chaos tax).
4. Optional market baseline: CFBD `/lines` spreads → implied probs; aim to approach
   (not necessarily beat) the market on Brier.
5. Keep a changelog of config fingerprints + pooled metrics in
   [`docs/ALGORITHM_EVAL_RESULTS.md`](ALGORITHM_EVAL_RESULTS.md) when you land a winner.
   Latest: **V5.3 confirmed** by full priors + week-15 + 32-config sweep
   (tune 2019–2022 / validate 2023 / holdout 2024) — no further promotions.

## Relationship to published rankings

| Use case | Prefer |
|----------|--------|
| Next-game win probability / backtest | `team_quality_score` (Elo) |
| Human-facing poll / “deserving” slate | `final_ranking_score` (FRS) |
| Early season | Stronger priors (`prior_strength` schedule) |
| Late season | Games dominate; priors → 0 by week 12 in API path |

The product can keep showing FRS while the lab insists Elo predicts games. If Elo
predicts well but FRS looks “wrong” to fans, that is a product/weights question —
not a reason to break the predictive sandbox.
