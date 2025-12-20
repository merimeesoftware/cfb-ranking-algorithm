# CFB Ranking Algorithm - Complete Breakdown (V5)

## Master Formula

```
FRS = (0.65 × TeamQuality) + (0.27 × RecordScore) + (0.08 × ConferenceQuality)
```

**Final Ranking Score (FRS)** combines three weighted components to produce the final rankings.

---

## 1. Team Quality (65%) — Elo-Based Rating

The foundation of the ranking system. This component measures **pure team strength** through a zero-sum Elo system that updates after every game.

### Initial Ratings (Starting Points)

| Tier | Initial Elo |
|------|-------------|
| Power 4 | 1500 |
| Group of 5 | 1200 |
| FCS | 900 |

**Historical Priors:** If multi-year historical data exists, initial ratings use a blended approach (85% fresh start, 15% historical).

### Elo Update Formula

For each game, the algorithm calculates an Elo delta and applies it as a zero-sum transfer:

```
Δ = K × Matchup_Weight × MoV_Multiplier × (Actual - Expected)

Winner:  New_Elo = min(Current_Elo + Δ, 1850)  # V5.3: Elo clamp
Loser:   New_Elo = Current_Elo - Δ
```

#### Component Parts:

| Component | Formula / Value | Description |
|-----------|-----------------|-------------|
| **K-factor (Base)** | 40 (×0.65 postseason) | Controls rating volatility. Reduced in bowls to prevent "Bowl Bias". |
| **Expected Score** | `1 / (1 + 10^((R_opp_eff - R_team_eff) / 400))` | Standard logistic Elo formula with HFA adjustment. |
| **Actual Score** | 1.0 | Win = 1.0, Loss = 0.0. |
| **Margin of Victory (MoV)** | `log(score_diff + 1)` | Logarithmic scaling prevents exploitation of blowout wins. |
| **Matchup Weight** | Varies | Tier-based damping (P4 vs P4 = 1.0, G5 vs G5 = 0.65). |

### Home-Field Advantage (HFA)

HFA adjusts the **expected** score calculation, not actual ratings:

```
Home_Effective_Elo = Home_Elo + HFA
Away_Effective_Elo = Away_Elo

HFA Values:
  Regular Season: 65 Elo points
  Postseason: 20 Elo points
  Neutral Site: 0 (detected via "neutral" or "kickoff" in game notes)
```

**Result:** Road wins yield larger positive deltas; home wins yield smaller deltas.

### Upset Bonus Multipliers

```
if (loser_Elo - winner_Elo) > 150:
    Δ ×= 1.18   # Major upset bonus (reduced from 1.25)

if winner is G5 and loser is P4:
    Δ ×= 1.12   # Cross-tier upset bonus (reduced from 1.20)
```

### Iterative Solver

The season is **simulated 2 times** (reduced from 4 for efficiency):
1. **Iteration 1:** Games processed with tier-based starting Elos.
2. **Iteration 2:** Re-processed using Iteration 1's final scores as reference.

### Elo Clamp

Winner Elo is capped at **1850** to prevent runaway outliers.

---

## 2. Record Score (27%) — Resume / Deserving Component

Rewards **winning record**, **milestones**, and **quality of victories**. This component answers: "Does this team's resume deserve a high ranking?"

### Record Score Formula

```
RecordScore = (BaseScore + Bonuses - Penalties) × PerfectionMultiplier
```

#### Components

| Component | Formula | Description |
|-----------|---------|-------------|
| **Base + Win%** | `1000 + (WeightedWinPct × 1000)` | Road wins count 1.1×, home wins 1.0× |
| **SoV Bonus** | `(AvgWinElo - Threshold) × 0.35` | P4 threshold: 1200, G5 threshold: 1050 |
| **SoS Score** | `log(max(AvgOppElo - Baseline, 1)) × 80` | P4 baseline: 1420, G5 baseline: 1300 |
| **Cross-Tier Bonus** | `60 × num_G5_beats_P4` | Reduced from 80 |
| **Quality Win Bonus** | `0.35 × (OppElo - P75)` per win | UNCAPPED (was 250) |
| **Quality Loss Bonus** | `0.10 × (OppElo - P90)` per loss | Credit for Top 10% losses |
| **Bad Loss Penalty** | `0.25 × (P25 - OppElo)` per loss | Penalty for Bottom 25% losses |
| **Loss Penalty** | `150 × (losses ^ 1.1)` | Progressive penalty |
| **Champ Anchors** | +100 (champ), +50 (finalist) | Conference success bonus |

### Perfection Bonus (Multiplicative)

Applied after all other RecordScore components:

| Record | Multiplier | Requirement |
|--------|------------|-------------|
| Undefeated | 1.05× | 0 losses, 12+ games |
| One-loss | 1.02× | 1 loss, 12+ games |

---

## 3. Conference Quality (8%) — Contextual League Boost

Measures the overall strength of a team's conference.

### Formula

```
Raw_CQ = (0.70 × TopHalfAvg) + (0.30 × FullAvg)
Final_CQ = Raw_CQ × OOC_Multiplier × ChaosTax_Multiplier
```

### Chaos Tax

Conferences with high internal variance (cannibalization) receive a penalty:

```
if Conference_StdDev > 160:
    ChaosTax_Multiplier = 0.90   # 10% penalty
else:
    ChaosTax_Multiplier = 1.00
```

### Synthetic CQ for FBS Independents

Instead of CQ=0, independents receive a **schedule-weighted synthetic CQ**:

```
Indie_CQ = Average(CQ of all opponents' conferences)
```

This rewards Notre Dame (plays P4 schedule) more than UMass (plays weaker schedule).

### OOC Multiplier

Based on inter-conference performance (P4 games weighted 1.0, G5 games 0.5, FCS games 0.1):

```
Performance_Ratio = Weighted_Wins / Total_Weighted_Games
Multiplier = 0.8 + (0.4 × Performance_Ratio)   # Range: 0.8 to 1.2
```

---

## V5 Feature Summary

| Feature | Description | Impact |
|---------|-------------|--------|
| **HFA (65 Elo)** | Road wins worth more, home wins worth less | +5-15 Elo for road wins |
| **Postseason K (0.65×)** | Reduced K-factor for bowl games | Prevents Bowl Bias |
| **Neutral Site Detection** | Keyword parsing ("neutral", "kickoff") | Fair treatment of neutral games |
| **Elo Clamp (1850)** | Maximum Elo cap | Prevents runaway outliers |
| **Chaos Tax (-10%)** | Penalty for high-variance conferences | ACC/Big 12 penalty if chaotic |
| **Synthetic Indie CQ** | Schedule-weighted CQ for independents | Notre Dame +80-120 FRS |
| **G5 Dampening** | Reduced upset/cross-tier bonuses | JMU/Tulane drop 3-5 spots |
| **Quality Loss Bonus** | Credit for losses to Top 5% | +5-25 FRS for quality losses |
| **Bad Loss Penalty** | Penalty for Bottom 25% losses | -10-50 FRS per bad loss |
| **Perfection Bonus** | 5%/2% multiplier for 0/1 losses | Guarantees undefeated > 1-loss |
| **QW Uncapped** | No 250pt cap on quality win bonus | Elite schedules fully rewarded |

---

## Version History

- **V5 (Current):**
  - **Weights:** 65/27/08 (TQ/RS/CQ)
  - **Iterations:** 2 (reduced from 4)
  - **New Features:**
    - Home-Field Advantage (65 Elo)
    - Postseason K-factor reduction (0.65×)
    - Neutral site detection
    - Elo clamp (1850 max)
    - Chaos Tax for high-variance conferences
    - Synthetic CQ for independents
    - Quality Loss Bonus (P90 threshold)
    - Bad Loss Penalty (P25 threshold)
    - Perfection Bonus (1.05×/1.02×)
  - **Removed:** Winstreak bonus (G5-exclusive advantage)
  - **Dampened:** G5 upset bonus (1.18×), cross-tier bonus (60pts), SoV mult G5 (0.35)

- **V4 (Previous):****
  - Weights: 52/38/10
  - Winstreak bonus for G5 (+150)
  - QW cap at 250

---

## Mathematical Notation Summary

| Symbol | Meaning |
|--------|---------|
| $E_A$ | Expected score for team A |
| $R_A$ | Elo rating for team A |
| $\Delta$ | Elo delta |
| $K$ | Base factor (40, ×0.65 postseason) |
| $HFA$ | Home-field advantage (65 regular, 20 postseason) |
| $FRS$ | Final Ranking Score |
| $P_{75}$ | 75th percentile Elo (quality win threshold) |
| $P_{90}$ | 90th percentile Elo (quality loss threshold) |
| $P_{25}$ | 25th percentile Elo (bad loss threshold) |
