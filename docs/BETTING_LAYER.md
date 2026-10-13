# Betting Layer (v0)

Two products. One rating engine.

| Layer | Job | Source of truth | Do not use for |
|-------|-----|-----------------|----------------|
| **Board (TR+ / FRS)** | Who deserves to be ranked where | `final_ranking_score` | Pricing a spread |
| **Book (betting layer)** | Where we disagree with the number | `team_quality_score` (V5.3 Elo) + close | Public ranking order |

Do **not** retune FRS for ATS. Do **not** fold ATS bonuses into Elo.
The board stays V5.3. The book is a pricing + traffic-light layer on top.

## Why adapt, not rewrite

Holdout 2024 Elo already beats home-field on winner Brier (`0.18051`, acc `0.719`).
That rating is leak-free and week-scoped. A fresh model would throw away the
only component that has been evaluated. Resume (15%) and CQ (5%) are
*deservingness* terms — they make the board look right and the line look wrong.

## Pricing

Home spread convention: **negative = home favored**.

```
model_spread_home = (away_elo - home_elo - hfa) / elo_per_point
edge_home         = model_spread_home - market_spread_home
```

- `edge_home < 0` → model likes home vs the number → pick HOME
- `edge_home > 0` → model likes away vs the number → pick AWAY

Defaults (v0, to be fit on 2019–2024 closes):

- `elo_per_point = 25`
- `hfa = 50` (match live ranker, not the stale 65 in `predict.py`)
- Neutral / postseason HFA follows `TeamQualityRanker`

Fit `elo_per_point` later by minimizing ATS log-loss on closes. Do not guess it
from FRS points — `matchup_service.py` currently does that and it is wrong for betting.

## Traffic lights

| Signal | Meaning | Rule (v0) |
|--------|---------|-----------|
| **GREEN** | Take it | `abs(edge) >= 3.0` and no veto |
| **LEAN** | Close to green | `1.5 <= abs(edge) < 3.0` and no veto |
| **PASS** | Stay away | everything else |

Hard vetoes (force PASS even if edge is huge):

- no market close
- week `< 3` (priors dominate)
- opponent is FCS
- `abs(market_spread) > 28` (landmine / clamp zone)
- steam against the pick `>= 1.5` pts (open → close)

Ohio: team spread / ML / total only. No college player props.

## Momentum / social — keep it out of Elo

Do **not** put narrative heat, X volume, or "vibes" inside the rating update.
Those features are noisy, leaky, and uncalibrated.

What *is* momentum, measured:

1. **Steam** (open vs close) — the market's social + sharp aggregator. Veto only.
2. **Rest / short week** — later, as an HFA tweak, after ATS baseline exists.
3. **Last-N ATS** — diagnostic, not a rating input.

If steam agrees with the pick, do not upsize. Confirmation is not edge.
If steam fights the pick hard, downgrade to PASS. That is the whole social layer in v0.

## Eval protocol

Reuse `algo_lab/backtest.py` week-scoping (ratings through week W-1 → price week W).
Score the book on:

- ATS win % (pushes excluded)
- units at -110
- CLV (close - open in pick direction)
- GREEN-only vs LEAN vs all-games

Winner Brier stays a health check on Elo. It is not the betting KPI.

Historical lines: CFBD `BettingApi.get_lines`. Offline fixtures live in
`tests/fixtures/sample_ats_slate.json` so CI does not spend quota.

## Fit order

1. Lock Elo (already V5.3).
2. Fit `elo_per_point` on 2019–2022 closes; validate 2023; holdout 2024.
3. Fit GREEN threshold (start 3.0) on units, not on hit rate.
4. Only then test rest / last-N ATS as vetoes. If they do not lift holdout units, drop them.
