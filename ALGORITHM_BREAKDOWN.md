# CFB Ranking Algorithm - Complete Breakdown (V3.9)

## Master Formula

```
FRS = (0.55 × TeamQuality) + (0.35 × RecordScore) + (0.10 × ConferenceQuality)
```

**Final Ranking Score (FRS)** combines three weighted components to produce the final rankings.

---

## 1. Team Quality (55%) — Elo-Based Rating

The foundation of the ranking system. This component measures **pure team strength** through a zero-sum Elo system that updates after every game.

### Initial Ratings (Starting Points)

| Tier | Initial Elo |
|------|-------------|
| Power 4 | 1500 |
| Group of 5 | 1200 |
| FCS | 900 |

**Historical Priors (V3.9):** If multi-year historical data exists, initial ratings use a blended approach:

1. **Prior Calculation:** `T_prior = 0.67(T_Y-1) + 0.33(T_Y-2)` (dropped Y-3 to reduce legacy drag)
2. **Blending:** `T_start = (1 - prior_strength) × tier_initial + prior_strength × T_prior`

With the default `prior_strength = 0.30`, this means:
- **70% Fresh Start:** Based on current tier (P4=1500, G5=1200, FCS=900)
- **30% Historical:** Based on recent performance (67% last year + 33% two years ago)

**Net Effect:** ~20% influence from Y-1, ~10% from Y-2 (down from 50/30/20 in V3.8). This aligns more closely with CFP's current-season focus while maintaining some year-to-year stability.

### Elo Update Formula

For each game, the algorithm calculates an Elo delta and applies it as a zero-sum transfer:

```
Δ = K × Matchup_Weight × MoV_Multiplier × (Actual - Expected)

Winner:  New_Elo = Current_Elo + Δ
Loser:   New_Elo = Current_Elo - Δ
```

#### Component Parts:

| Component | Formula / Value | Description |
|-----------|-----------------|-------------|
| **K-factor (Base)** | 40 | Controls rating volatility. Higher K = more dramatic swings per game. |
| **Expected Score** | `1 / (1 + 10^((R_loser - R_winner) / 400))` | Standard logistic Elo formula. Measures probability of the winner winning. |
| **Actual Score** | 1.0 | Win = 1.0, Loss = 0.0 (actual minus expected determines delta). |
| **Margin of Victory (MoV)** | `log(score_diff + 1)` | Logarithmic scaling prevents exploitation of blowout wins. Score diff of 1 = 0.69, diff of 50 = 3.93. |
| **Matchup Weight** | Varies (see below) | Tier-based damping to prevent artificial inflation between divisions. |

#### Matchup Weight Table (Tier Asymmetry)

The matchup weight prevents lower-tier teams from gaining excessive Elo points when beating each other, while allowing natural competition within tiers.

| Matchup | Weight | Rationale |
|---------|--------|-----------|
| P4 vs P4 | 1.0 | Full exchange; matches are naturally competitive. |
| P4 vs G5 (or G5 vs P4) | 0.8 | Reduced exchange; expected outcome (P4 typically stronger). |
| G5 vs G5 | 0.5 | **Heavily dampened** to prevent internal G5 inflation. Prevents G5 pool from artificially inflating. |
| P4/G5 vs FCS | 0.2 | Minimal exchange; FCS is separate ecosystem. |
| FCS vs FCS | 0.1 | Almost no exchange; keeps FCS isolated. |

### Iterative Solver

The season is **simulated 3 times**:

1. **Iteration 1:** Games processed sequentially; Elo evolves naturally.
2. **Iteration 2:** Same games re-processed, but uses Iteration 1's final scores as reference for opponent strength.
3. **Iteration 3:** Same games re-processed, but uses Iteration 2's final scores as reference.

**Purpose:** Early-season games (when Elo is uncertain) are re-evaluated using end-of-season opponent strength, ensuring fair assessment of early performance.

**Example:** A team that beats a "mediocre" opponent in Week 1 gets re-evaluated in Iteration 2 based on that opponent's final Elo, not their uncertain Week 1 Elo.

---

## 2. Record Score (35%) — Resume / Deserving Component

Rewards **winning record**, **schedule difficulty**, and **quality of victories**. This component answers: "Does this team's resume deserve a high ranking?"

### Record Score Formula

```
RecordScore = 1000 + (WeightedWinPct × 1000) + SoV_Bonus + SoS_Score
```

The base of 1000 is then modified by the sub-components below.

#### Sub-Component 1: Weighted Win Percentage

```
WeightedWinPct = ((HomeWins × 1.0) + (RoadWins × 1.1)) / TotalGames
```

| Factor | Weight | Rationale |
|--------|--------|-----------|
| Home Wins | 1.0 | Baseline |
| Road Wins | 1.1 | 10% bonus for playing tough environments |

**Example:** 10-2 record with 7 home wins and 3 road wins:
- Weighted wins = (7 × 1.0) + (3 × 1.1) = 7 + 3.3 = 10.3
- WeightedWinPct = 10.3 / 12 = 0.858
- Contribution to RecordScore = 0.858 × 1000 = +858 points

#### Sub-Component 2: Strength of Victory (SoV)

```
SoV_Bonus = (AvgWinElo - 1200) × 0.5   [if AvgWinElo > 1200, else 0]
```

| Part | Description |
|------|-------------|
| **AvgWinElo** | Average Elo rating of all opponents you defeated |
| **Threshold** | 1200 (roughly Group of 5 level) |
| **Multiplier** | 0.5x |

**Rewards:** Beating quality opponents. The better the opponents you beat, the higher your bonus.

**Examples:**
- Avg win Elo = 1800 (Elite): `(1800 - 1200) × 0.5 = +300 points` ✓
- Avg win Elo = 1500 (Average): `(1500 - 1200) × 0.5 = +150 points` ✓
- Avg win Elo = 1100 (Weak): No bonus (0 points)

**Philosophy:** SoV doesn't reward quantity of wins, but *quality* of opponents beaten. A team with 5 elite wins scores better than a team with 10 mediocre wins.

#### Sub-Component 3: Strength of Schedule (SoS) — V3.9 Logarithmic Scaling

```
if AvgOpponentElo > 1400:
    SoS_Score = log(AvgOpponentElo - 1400) × 150
else:
    SoS_Score = (AvgOpponentElo - 1400) × 0.5  # Linear penalty for weak schedules
```

| Part | Description |
|------|-------------|
| **AvgOpponentElo** | Average Elo of all opponents (including losses) |
| **Baseline** | 1400 (below average) |
| **Scaling** | Logarithmic above 1400, linear penalty below |

**V3.9 Change:** Switched from linear (1.0x multiplier) to logarithmic scaling. This provides:
- Smoother differentiation between "tough" and "brutal" schedules
- Diminishing returns to prevent runaway inflation
- No hard cap that would flatten elite schedules

**Examples (Logarithmic):**
| Avg Opponent Elo | SoS Score | Interpretation |
|------------------|-----------|----------------|
| 1400 (weak) | ~0 | Baseline |
| 1500 (average) | ~150 | Standard P4 schedule |
| 1600 (good) | ~270 | Above-average difficulty |
| 1700 (tough) | ~330 | Top-tier schedule |
| 1800 (brutal) | ~370 | Elite schedule |
| 1300 (very weak) | -50 | Penalty for cupcake slate |

**Philosophy:** Incentivizes scheduling stronger non-conference opponents and rewards teams in stronger conferences, with diminishing returns at the top.

### Full Record Score Example

A team with:
- 11-1 record (9 home wins, 2 road wins)
- Beaten opponents average Elo = 1600
- Overall schedule average Elo = 1650

```
Weighted Win %  = ((9 × 1.0) + (2 × 1.1)) / 11 = 10.2 / 11 = 0.927
Win contribution = 0.927 × 1000 = 927 points

SoV Bonus       = (1600 - 1200) × 0.5 = 400 × 0.5 = 200 points
SoS Score       = (1650 - 1500) × 1.0 = 150 × 1.0 = 150 points

RecordScore     = 1000 + 927 + 200 + 150 = 2277 points
```

---

## 3. Conference Quality (10%) — Contextual League Boost

Measures the overall strength of a team's conference to provide contextual credit. A team in a weak conference should be penalized; a team in a strong conference gets a small boost.

### Conference Quality Formula

```
CQ = RawCQ × OOC_Multiplier
```

The raw conference strength is then adjusted by how well the conference performs outside the conference.

#### Sub-Component 1: Raw Conference Quality (RawCQ)

```
RawCQ = Average Elo of the Top 50% of teams in the conference
```

| Step | Method |
|------|--------|
| 1. List all teams in conference | Get their current Elo ratings |
| 2. Sort by Elo (descending) | Strongest teams first |
| 3. Take top 50% | If 14 teams, take top 7 |
| 4. Calculate average | Sum their Elos ÷ count |

**Philosophy:** Uses top half to avoid dragging down the conference average with weak teams. A conference with 3 elite and 11 weak teams should reflect the strength of the elite teams.

**Example:** SEC with teams at [1700, 1650, 1600, 1500, 1400, 1300, 1100, 1050, 1000, 950, 900, 850, 800, 750]:
- Top 50% = [1700, 1650, 1600, 1500, 1400, 1300, 1100]
- RawCQ = (1700 + 1650 + 1600 + 1500 + 1400 + 1300 + 1100) / 7 = **1464** (approximate)

#### Sub-Component 2: Out-of-Conference (OOC) Multiplier

```
OOC_Multiplier = 0.8 + (0.4 × PerformanceRatio)
```

Ranges from **0.8 to 1.2** based on how the conference performs against other conferences.

| PerformanceRatio | OOC_Multiplier | Interpretation |
|------------------|----------------|-----------------|
| 0.0 (0% wins) | 0.8 | Terrible OOC record → 20% penalty |
| 0.5 (50% wins) | 1.0 | Average OOC record → no adjustment |
| 1.0 (100% wins) | 1.2 | Perfect OOC record → 20% boost |

**PerformanceRatio Calculation:**

```
PerformanceRatio = WeightedWins / WeightedTotalGames
```

Where weighted games emphasize Power 4 competition:

| Opponent Tier | Weight |
|---------------|--------|
| vs Power 4 | 1.0 |
| vs Group of 5 | 0.5 |
| vs FCS | 0.1 |

**Example:** A conference with OOC record of:
- 10-5 vs P4 (weight 1.0) = 10 wins, 5 losses
- 8-2 vs G5 (weight 0.5) = 4 wins, 1 loss
- 6-1 vs FCS (weight 0.1) = 0.6 wins, 0.1 loss

```
WeightedWins = 10 + 4 + 0.6 = 14.6
WeightedLosses = 5 + 1 + 0.1 = 6.1
WeightedTotal = 20.7

PerformanceRatio = 14.6 / 20.7 = 0.705
OOC_Multiplier = 0.8 + (0.4 × 0.705) = 0.8 + 0.282 = 1.082
```

### Special Case: FBS Independents

Teams without a conference (like Notre Dame) are assigned:

```
CQ = Average of all Power 4 Conference Quality scores
```

This treats them as members of the elite tier without giving them artificial advantage.

### Full Conference Quality Example

**ACC Example:**

```
RawCQ = 1300 (top 50% of teams average 1300)
OOC Performance:
  - vs P4: 5-8 (weighted: 5 wins, 8 losses)
  - vs G5: 12-3 (weighted: 6 wins, 1.5 losses)
  - vs FCS: 20-0 (weighted: 2 wins, 0 losses)

WeightedWins = 5 + 6 + 2 = 13
WeightedTotal = 5 + 8 + 6 + 1.5 + 2 + 0 = 22.5
PerformanceRatio = 13 / 22.5 = 0.578
OOC_Multiplier = 0.8 + (0.4 × 0.578) = 0.8 + 0.231 = 1.031

Final CQ = 1300 × 1.031 = 1340
```

---

## How All Three Components Work Together

### Example: Georgia (11-1)

| Component | Calculation | Score |
|-----------|-------------|-------|
| **Team Quality (60%)** | Elo = 1750 | 1750 |
| **Record Score (30%)** | (calculated above) = 2277 | 2277 |
| **Conference Quality (10%)** | SEC CQ = 1380 | 1380 |

```
Final Score = (0.6 × 1750) + (0.3 × 2277) + (0.1 × 1380)
            = 1050 + 683 + 138
            = 1871
```

### Example: Tulane (11-1) in different conference

| Component | Calculation | Score |
|-----------|-------------|-------|
| **Team Quality (60%)** | Elo = 1600 (lower from playing weaker opponents) | 1600 |
| **Record Score (30%)** | (same 11-1) = 2277 | 2277 |
| **Conference Quality (10%)** | AAC CQ = 1150 | 1150 |

```
Final Score = (0.6 × 1600) + (0.3 × 2277) + (0.1 × 1150)
            = 960 + 683 + 115
            = 1758
```

**Key:** Same record (11-1), but Georgia ranks higher due to:
1. Stronger Team Quality (better Elo from playing tougher opponents)
2. Slightly lower Conference Quality bonus/penalty

---

## Key Features & Design Decisions

### 1. Road Wins Matter More (1.1x)
Playing and winning on the road is inherently harder. Teams get a 10% boost for road wins.

### 2. Iterative Solver (3 passes)
Early-season games are re-evaluated based on final-season opponent strength, ensuring fair assessment when teams were still unknown.

### 3. Zero-Sum Elo
Every point gained by the winner is subtracted from the loser. This prevents artificial inflation of the entire system.

### 4. Margin of Victory (Logarithmic)
Prevents teams from exploiting blowout wins. Logarithmic scaling means:
- 1-point win ≈ 0.7x multiplier
- 10-point win ≈ 2.3x multiplier
- 50-point win ≈ 3.9x multiplier (not 50x)

### 5. Schedule Rewards (SoS)
Teams are rewarded for **scheduling** tough opponents, regardless of outcome. Incentivizes non-conference strength-of-schedule.

### 6. Quality of Wins, Not Quantity (SoV)
A team with 5 elite wins scores better than 10 mediocre wins. The average opponent Elo is what matters.

### 7. Conference Tier Damping
- G5 vs G5 games (0.5x weight) prevent the Group of 5 pool from inflating
- FCS games (0.1x-0.2x weight) keep FCS isolated
- This creates natural stratification between tiers

### 8. Conference Quality Adjustment
Weak OOC records reduce conference CQ; strong OOC records increase it. Prevents weak conferences from unfairly boosting all members.

---

## Version History

- **V3.9 (Current):** Reduced legacy bias (30% prior vs 70% fresh), dropped Y-3 from priors, logarithmic SoS scaling, reweighted FRS to 0.55/0.35/0.10.
- **V3.8:** Full weighting of Record Score (30%), simplified OOC multiplier calculation, P4-weighted inter-conference performance.
- **V3.7:** Introduced SoS (Strength of Schedule) component to reward tough schedules.
- **V3.6:** Weighted road wins (1.1x) in Record Score calculation.
- **V3.0+:** Logistic Elo with tier-based matchup weights, iterative solver.

---

## Mathematical Notation Summary

| Symbol | Meaning |
|--------|---------|
| $E_A$ | Expected score for team A |
| $R_A, R_B$ | Elo ratings for teams A and B |
| $\Delta$ | Elo delta (points transferred) |
| $K$ | Base factor (40) |
| $M_{mov}$ | Margin of Victory multiplier |
| $M_{tier}$ | Matchup weight (tier asymmetry) |
| $AvgWinElo$ | Average Elo of defeated opponents |
| $AvgOppElo$ | Average Elo of all opponents |
| $RawCQ$ | Raw conference quality (top 50% avg) |
| $OOC_{mult}$ | Out-of-conference performance multiplier |
| $FRS$ | Final Ranking Score |

