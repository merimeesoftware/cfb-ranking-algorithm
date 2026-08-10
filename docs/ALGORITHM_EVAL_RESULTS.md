# Algorithm Evaluation Results

Recorded results from the leak-free week-by-week predictive sandbox
(`algo_lab/` + `scripts/run_algo_eval_suite.py`). Protocol: ratings through
week W−1 predict week W; primary metric is **Brier** (lower is better).

**Run settings:** seasons 2023–2024, max week 12, FBS-involved games only,
no historical priors, `rating_field=team_quality_score` unless noted.
Raw JSON: [`algo_eval_results.json`](algo_eval_results.json).

## Baseline vs always-home

| Config | Season | N | Accuracy | Brier | Brier lift vs home |
|--------|--------|---|----------|-------|--------------------|
| `use_reference_ranks=True` | 2023 | 881 | 0.692 | 0.1967 | +0.0414 |
| `use_reference_ranks=True` | 2024 | 815 | 0.704 | 0.1883 | +0.0504 |
| `use_reference_ranks=False` | 2023 | 881 | 0.720 | 0.1884 | +0.0496 |
| `use_reference_ranks=False` | 2024 | 815 | 0.718 | 0.1811 | +0.0576 |

Pooled Brier: **0.1926** (ref on) vs **0.1849** (ref off).

### Decision: `use_reference_ranks=False` (default)

Feeding prior-iteration Elos into expectation **hurt** calibration. The feature
remains implemented and toggleable for future experiments; chaos-tax iterations
still run.

## Elo hyperparameter sweep (validate 2023 → holdout 2024)

Grid: `base_factor ∈ {30,40,50}`, `hfa_elo ∈ {50,65,80}`, `upset_bonus_mult ∈ {1.0,1.18}`.

- Best on 2023: `{base_factor: 50, hfa_elo: 50, upset_bonus_mult: 1.18}` (Brier 0.1866)
- 2024 holdout default (K=40, HFA=65): Brier **0.18107**
- 2024 holdout swept: Brier **0.18079** (Δ = 0.00028)

### Decision: keep default K=40 / HFA=65

Holdout gain below the ~0.0005 promotion threshold; always-home lift essentially
unchanged.

## FRS weight triples (predict with `final_ranking_score`)

| TQ / Resume / CQ | Pooled Brier | Pooled Acc |
|------------------|--------------|------------|
| 0.65 / 0.27 / 0.08 (old) | 0.19566 | — |
| 0.70 / 0.22 / 0.08 | 0.19198 | — |
| 0.60 / 0.32 / 0.08 | 0.19979 | — |
| **0.75 / 0.20 / 0.05** | **0.19060** | — |
| 0.55 / 0.35 / 0.10 | 0.20237 | — |

### Decision: promote **75 / 20 / 05**

Higher Team Quality weight moves the published FRS closer to the Elo signal that
already beats always-home on Brier. Resume/CQ remain for deservingness, at lower
weight.

## Promoted V5.2 config

| Key | Value |
|-----|-------|
| `ALGO_VERSION` | `v5.2` |
| `team_quality_weight` | 0.75 |
| `record_weight` | 0.20 |
| `conference_weight` | 0.05 |
| `base_factor` | 40.0 |
| `hfa_elo` | 65.0 |
| `use_reference_ranks` | false |

## Integrity fixes shipped with this eval

- CFBD `_transform_game` preserves `notes`, `season_type`, `neutral_site`
- Cloud Agent `environment.json` installs `python3-venv` before `python3 -m venv`
- Eval sandbox + warm-cache scripts under `scripts/`
