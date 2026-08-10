# Algorithm Evaluation Results

Recorded results from the leak-free week-by-week predictive sandbox
(`algo_lab/` + `scripts/run_algo_eval_suite.py`). Protocol: ratings through
week W−1 predict week W; primary metric is **Brier** (lower is better).

## Season split (expanded)

| Role | Years |
|------|-------|
| **Tune** | 2019–2022 |
| **Validate** | 2023 |
| **Holdout** | 2024 (never used to pick params) |

Max week 12, FBS-involved games, no historical priors,
`rating_field=team_quality_score` unless noted.
Raw JSON: [`algo_eval_results.json`](algo_eval_results.json).

### CFBD call budget

Warmed 2019–2022 with full-season fetches: **6 live calls** on slot A
(`CFBD_API_KEY`; remaining ≈818/1000). Teams + 2022–2024 were already cached.
Dual-key support: set `CFBD_API_KEY_B` + `CFBD_API_KEY_SLOT=B` for a second
1k/mo quota (see [`.cursor/SECRETS.md`](../.cursor/SECRETS.md)).

## Reference ranks A/B

| Window | ref ON Brier | ref OFF Brier |
|--------|--------------|---------------|
| Tune 2019–2022 | 0.19551 | **0.18986** |
| Validate 2023 | 0.19667 | **0.18840** |
| Holdout 2024 | 0.18829 | **0.18107** |

### Decision: `use_reference_ranks=False`

Confirmed on the longer tune window.

## Elo hyperparameter sweep

Grid: `base_factor ∈ {30,40,50}`, `hfa_elo ∈ {50,65,80}`, `upset_bonus_mult ∈ {1.0,1.18}`.

- Best on **tune**: `{base_factor: 50, hfa_elo: 50, upset_bonus_mult: 1.18}` (Brier 0.18877)
- Validate default → swept: **0.18840 → 0.18660** (Δ = +0.00180)
- Holdout default → swept: **0.18107 → 0.18079** (no regression)

### Decision: promote **K=50, HFA=50**

(Previously held at 40/65 when only 2023 was used for sweeping — longer history
changed the gate.)

## FRS weight triples (predict with `final_ranking_score`)

| TQ / Resume / CQ | Tune Brier | Val 2023 | Hold 2024 |
|------------------|------------|----------|-----------|
| 0.75 / 0.20 / 0.05 (V5.2) | 0.19268 | 0.19099 | 0.19196 |
| 0.65 / 0.27 / 0.08 (V5.1) | 0.19732 | 0.19524 | 0.19798 |
| **0.80 / 0.15 / 0.05** | **0.19025** | **0.18870** | **0.18805** |
| 0.70 / 0.22 / 0.08 | 0.19392 | 0.19221 | 0.19345 |

### Decision: promote **80 / 15 / 05**

## Promoted V5.3 config

| Key | Value |
|-----|-------|
| `ALGO_VERSION` | `v5.3` |
| `team_quality_weight` | 0.80 |
| `record_weight` | 0.15 |
| `conference_weight` | 0.05 |
| `base_factor` (K) | 50.0 |
| `hfa_elo` | 50.0 |
| `upset_bonus_mult` | 1.18 |
| `use_reference_ranks` | false |

## Version changelog

| Version | Change |
|---------|--------|
| V5.2 | First eval (2023–2024 only): FRS 75/20/05; ref ranks off; keep K=40/HFA=65 |
| **V5.3** | Expanded tune 2019–2022: FRS 80/15/05; K=50; HFA=50 |
