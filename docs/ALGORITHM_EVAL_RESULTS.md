# Algorithm Evaluation Results

Leak-free week-by-week predictive sandbox
(`algo_lab/` + `scripts/run_algo_eval_suite.py`).
Primary metric: **Brier** (lower is better).

## Latest run: FULL (with priors)

| Setting | Value |
|---------|-------|
| Mode | `full` |
| Priors | **Yes** (Y−1 / Y−2) |
| Max week | **15** |
| Tune | 2019–2022 |
| Validate | 2023 |
| Holdout | 2024 |
| Elo grid | K∈{30,40,50,60} × HFA∈{40,50,65,80} × upset∈{1.0,1.18} = **32 configs** |

Raw JSON: [`algo_eval_results.json`](algo_eval_results.json).

### CFBD spend for this expansion

| Action | Live calls |
|--------|------------|
| Warm 2017–2018 (for 2019 priors) | **4** |
| Slot A remaining after warm | ≈814/1000 |
| Eval itself | **0** (offline + cache) |

Dual keys: `CFBD_API_KEY` / `CFBD_API_KEY_B` + `CFBD_API_KEY_SLOT=A|B`
(see [`.cursor/SECRETS.md`](../.cursor/SECRETS.md)). Slot B not injected on this VM yet.

## Reference ranks A/B (with priors)

| Window | ref ON | ref OFF |
|--------|--------|---------|
| Tune 2019–2022 | 0.19021 | **0.18500** |
| Validate 2023 | 0.19168 | **0.17984** |
| Holdout 2024 | 0.19226 | **0.18051** |

### Decision: `use_reference_ranks=False` (unchanged)

## Elo sweep (32 configs, priors on)

- **Best on tune:** `{base_factor: 50, hfa_elo: 50, upset_bonus_mult: 1.18}` — Brier **0.18500**
- That config **is already V5.3 default**, so validate/holdout default ≡ swept
- Validate 2023 Brier **0.17984** (accuracy 0.733, lift vs home +0.060)
- Holdout 2024 Brier **0.18051** (accuracy 0.719, lift vs home +0.059)

### Decision: no Elo change — **confirm V5.3 K=50 / HFA=50**

Top-5 tune Briers were all ≥ 0.185; next-best configs (~0.188) were worse.

## FRS weight triples (with priors)

| TQ / Resume / CQ | Tune | Val 2023 | Hold 2024 |
|------------------|------|----------|-----------|
| **0.80 / 0.15 / 0.05 (V5.3)** | **0.18698** | **0.18331** | **0.18730** |
| 0.85 / 0.10 / 0.05 | worse on gate | — | — |
| 0.75 / 0.20 / 0.05 | worse | — | — |
| 0.65 / 0.27 / 0.08 | worse | — | — |

### Decision: no FRS change — **confirm 80 / 15 / 05**

## Confirmed V5.3 config

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
| V5.2 | Short eval (2023–2024, no priors, week≤12): FRS 75/20/05; keep K=40/HFA=65 |
| V5.3 | Expanded tune 2019–2022 (no priors, week≤12): FRS 80/15/05; K=50; HFA=50 |
| **V5.3 confirmed** | **Full** tune with priors + week 15 + 32-config Elo grid: **no further promotions** |
