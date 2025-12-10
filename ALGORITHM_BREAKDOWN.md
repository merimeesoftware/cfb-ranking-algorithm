# CFB Ranking Algorithm - Complete Breakdown (V4.1)

## Master Formula

```
FRS = (0.52 × TeamQuality) + (0.38 × RecordScore) + (0.10 × ConferenceQuality)
```

**Final Ranking Score (FRS)** combines three weighted components to produce the final rankings.

---

## 1. Team Quality (52%) — Elo-Based Rating

The foundation of the ranking system. This component measures **pure team strength** through a zero-sum Elo system that updates after every game.

### Initial Ratings (Starting Points)

| Tier | Initial Elo |
|------|-------------|
| Power 4 | 1500 |
| Group of 5 | 1200 |
| FCS | 900 |

**Historical Priors (V4.0):** If multi-year historical data exists, initial ratings use a blended approach:

1. **Prior Calculation:** `T_prior = 0.70(T_Y-1) + 0.30(T_Y-2)` (dropped Y-3 to reduce legacy drag)
2. **Blending:** `T_start = (1 - prior_strength) × tier_initial + prior_strength × T_prior`

With the default `prior_strength = 0.15`, this means:
- **85% Fresh Start:** Based on current tier (P4=1500, G5=1200, FCS=900)
- **15% Historical:** Based on recent performance (70% last year + 30% two years ago)

**Net Effect:** ~10.5% influence from Y-1, ~4.5% from Y-2. This significantly reduces legacy echo and aligns closely with CFP's current-season focus.

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
| G5 vs G5 | 0.65 | **V4.0:** Reduced damping (was 0.5) to allow quality G5 teams to build Elo while still preventing runaway inflation. |
| P4/G5 vs FCS | 0.2 | Minimal exchange; FCS is separate ecosystem. |
| FCS vs FCS | 0.1 | Almost no exchange; keeps FCS isolated. |

### Upset Bonus Multipliers (V4.0 Phase 2)

After calculating the base delta, upset bonuses are applied to reward underdog victories:

```
if (loser_Elo - winner_Elo) > 150:
    Δ ×= 1.25   # Major upset bonus

if winner is G5 and loser is P4:
    Δ ×= 1.20   # Cross-tier upset bonus (stacks)
```

| Scenario | Multiplier | Example |
|----------|------------|----------|
| Major upset (Elo gap > 150) | ×1.25 | Underdog beats 150+ higher-rated team |
| G5 beats P4 | ×1.20 | James Madison beats Virginia Tech |
| G5 upsets P4 by 150+ Elo | ×1.50 | Both bonuses stack: 1.25 × 1.20 |

**Philosophy:** Rewards teams for signature wins. A G5 team upsetting a ranked P4 opponent gets significantly more Elo than a routine win, helping quality G5 teams climb into the top 15.

### Iterative Solver

The season is **simulated 4 times** (V4.0: increased from 3):

1. **Iteration 1:** Games processed sequentially; Elo evolves naturally.
2. **Iteration 2:** Same games re-processed, but uses Iteration 1's final scores as reference for opponent strength.
3. **Iteration 3:** Same games re-processed, but uses Iteration 2's final scores as reference.
4. **Iteration 4:** Final pass using Iteration 3's scores for maximum convergence on close resumes.

**Purpose:** Early-season games (when Elo is uncertain) are re-evaluated using end-of-season opponent strength, ensuring fair assessment of early performance. The additional 4th pass improves convergence for teams with similar resumes (e.g., Oregon vs Indiana tiebreaks).

**Example:** A team that beats a "mediocre" opponent in Week 1 gets re-evaluated in Iteration 2 based on that opponent's final Elo, not their uncertain Week 1 Elo.

---

## 2. Record Score (38%) — Resume / Deserving Component

Rewards **winning record**, **schedule difficulty**, and **quality of victories**. Penalizes **multi-loss teams** progressively. This component answers: "Does this team's resume deserve a high ranking?"

### Record Score Formula

```
RecordScore = 1000 + (WeightedWinPct × 1000) + SoV_Bonus + SoS_Score + CrossTier_Bonus 
            + H2H_Bonus + QL_Bonus + WinStreak_Bonus - Loss_Penalty
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

#### Sub-Component 2: Strength of Victory (SoV) — V4.0 Tier-Specific

V4.0 uses **tier-specific thresholds** to give G5 teams credit for quality intra-conference wins:

```
# Power 4 teams (V4.0.2: reduced multiplier)
SoV_Bonus = (AvgWinElo - 1200) × 0.35   [if AvgWinElo > 1200]

# Group of 5 teams (V4.0.2: reduced multiplier)
SoV_Bonus = (AvgWinElo - 1050) × 0.45   [if AvgWinElo > 1050]
```

| Tier | Threshold | Multiplier | Rationale |
|------|-----------|------------|------------|
| Power 4 | 1200 | 0.35 | V4.0.2: Reduced from 0.5 to dampen resume inflation |
| Group of 5 | 1050 | 0.45 | V4.0.2: Reduced from 0.55 to balance with P4 |

**Examples:**
- P4 team, Avg win Elo = 1500: `(1500 - 1200) × 0.5 = +150 points`
- G5 team, Avg win Elo = 1250: `(1250 - 1050) × 0.55 = +110 points` (previously +25)
- G5 team, Avg win Elo = 1100: `(1100 - 1050) × 0.55 = +27.5 points` (previously 0)

**Cross-Tier Win Bonus (V4.0 Phase 2):**
```
Cross_Tier_Bonus = 80 × num_G5_beats_P4_wins
```
G5 teams get +80 points in RecordScore for each P4 opponent defeated, separate from Elo gains.

**Philosophy:** G5 teams like JMU and Tulane get credit for beating quality G5 opponents AND get bonus points for any P4 scalps.

#### Sub-Component 3: Strength of Schedule (SoS) — V4.0 Tier-Specific

V4.0 uses **tier-specific baselines** to reduce unfair penalties on G5 teams:

```
# Power 4 teams (baseline 1420) - V4.0.2: reduced log multiplier
if AvgOpponentElo > 1420:
    SoS_Score = log(max(AvgOpponentElo - 1420, 1)) × 80
else:
    SoS_Score = (AvgOpponentElo - 1420) × 0.5

# Group of 5 teams (baseline 1300)
if AvgOpponentElo > 1300:
    SoS_Score = log(max(AvgOpponentElo - 1300, 1)) × 80
else:
    SoS_Score = (AvgOpponentElo - 1300) × 0.5
```

| Tier | Baseline | Rationale |
|------|----------|------------|
| Power 4 | 1420 | Higher bar; P4 schedules should be tough |
| Group of 5 | 1300 | Lower bar; typical G5 slate shouldn't be heavily penalized |

**V4.0.2 Change:** Reduced log multiplier from 160 to 80 and penalty multiplier from 0.8 to 0.5 to prevent schedule from dominating resume score.

**Impact Examples:**
| Team Type | Avg Opp Elo | Old SoS (1400 baseline) | New SoS (tier-specific) |
|-----------|-------------|-------------------------|-------------------------|
| P4, tough schedule | 1550 | +117 | +109 |
| G5, average schedule | 1280 | -60 | -16 |
| G5, good schedule | 1350 | -25 | +35 |

#### Sub-Component 4: Loss Penalty (V4.1)

```
Loss_Penalty = 100 × (num_losses ^ 1.05)
```

| Losses | Penalty | Interpretation |
|--------|---------|----------------|
| 0 | 0 | No penalty for undefeated teams |
| 1 | -100 | Single loss is costly but recoverable |
| 2 | -207 | Two losses significantly hurts ranking |
| 3 | -317 | Three losses drops team substantially |
| 4 | -429 | Four losses puts team out of contention |

**V4.1:** Base reduced from 150 to 100 and exponent reduced to 1.05. This diminishes the penalty for losses, allowing quality teams with tough schedules to stay ranked higher. Capped at 500 points.

#### Sub-Component 5: Head-to-Head Bonus (V4.1)

Rewards teams for defeating top-ranked opponents in the current rankings:

```
H2H_Bonus = min((Top10_Wins × 88) + (Top25_Wins × 44), 220)
```

| Win Type | Bonus | Rationale |
|----------|-------|----------|
| Win vs Top 10 Team (Elo > 1650) | +88 | V4.1: Boosted by 10% |
| Win vs Top 11-25 Team (Elo > 1550) | +44 | V4.1: Boosted by 10% |
| Maximum Total | 220 | V4.1: Capped to prevent runaway stacking |

**Examples:**
- Team with 2 wins vs Top 10 + 1 win vs Top 20: `min((2 × 88) + (1 × 44), 220) = +220 points` (capped)
- Team with 0 ranked wins: `+0 points`
- Team with 3 wins vs Top 25 (none Top 10): `min((0 × 88) + (3 × 44), 220) = +132 points`

#### Sub-Component 6: Quality Loss Bonus (V4.1)

Rewards teams whose losses came against elite opponents (Elo > 1600):

```
for each loss:
    if opponent_elo > 1600:
        quality_loss_points += min((opponent_elo - 1600) × 0.165, 33)

QL_Bonus = quality_loss_points / num_losses   [if num_losses > 0]
```

| Opponent Elo | Bonus per QL | Example |
|--------------|--------------|----------|
| 1600 | +0 | Threshold - no bonus |
| 1650 | +8.25 | (1650-1600) × 0.165 |
| 1700 | +16.5 | (1700-1600) × 0.165 |
| 1800 | +33 | Capped at 33 per loss |

**V4.1 Changes:**
- Multiplier increased to 0.165 (10% boost)
- Cap increased to 33 per loss

**Philosophy:** "Quality of losses" matters, but losing shouldn't be rewarded too much. Only losses to truly elite teams (Elo > 1600) count.

#### Sub-Component 7: Win Streak Bonus (Removed in V4.1)

*This component was removed in V4.1 to simplify the algorithm and rely more on the Cross-Tier Bonus and Upset Multipliers to reward G5 performance.*

### Full Record Score Example

A team with:
- 11-1 record (9 home wins, 2 road wins)
- Beaten opponents average Elo = 1600
- Overall schedule average Elo = 1650

```
Weighted Win %  = ((9 × 1.0) + (2 × 1.1)) / 11 = 10.2 / 11 = 0.927
Win contribution = 0.927 × 1000 = 927 points

SoV Bonus       = (1600 - 1200) × 0.5 = 400 × 0.5 = 200 points
SoS Score       = log(max(1650 - 1400, 1)) × 150 = log(250) × 150 = 828 points
Loss Penalty    = 180 × (1 ^ 1.15) = 180 points

RecordScore     = 1000 + 927 + 200 + 828 - 180 = 2775 points
```

---

## 3. Conference Quality (10%) — Contextual League Boost

Measures the overall strength of a team's conference to provide contextual credit. A team in a weak conference should be penalized; a team in a strong conference gets a small boost.

### Conference Quality Formula

```
CQ = RawCQ × OOC_Multiplier
```

The raw conference strength is then adjusted by how well the conference performs outside the conference.

#### Sub-Component 1: Raw Conference Quality (RawCQ) — V4.0 Hybrid

V4.0 uses a **hybrid formula** that rewards conference depth while not dragging down elite conferences:

```
top_n = ceil(num_teams / 2)   # Rounds up for odd numbers
top_half_avg = avg(top_n teams by Elo)
full_avg = avg(all teams by Elo)

RawCQ = (0.70 × top_half_avg) + (0.30 × full_avg)
```

| Component | Weight | Purpose |
|-----------|--------|----------|
| Top 50% Average | 70% | Rewards elite teams, prevents bottom drag |
| Full Conference Average | 30% | Rewards depth, penalizes top-heavy conferences |

**Impact Example (14-team conferences):**
| Conference | Top 7 Avg | Full Avg | Old CQ (top 50%) | V4.0 Hybrid CQ |
|------------|-----------|----------|------------------|----------------|
| Big Ten | 1620 | 1480 | 1620 | 1578 |
| SEC | 1580 | 1520 | 1580 | 1562 |
| Big 12 | 1540 | 1450 | 1540 | 1513 |
| ACC | 1480 | 1380 | 1480 | 1450 |

**Philosophy:** Conferences with more depth (SEC) lose less from the hybrid formula than top-heavy conferences (Big Ten). This better reflects overall conference strength.

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

Teams without a conference (like Notre Dame, Army) are handled specially:

**V4.1 Changes:**
- **Conference Type:** Treated as "Power 4" for all tier-based calculations (SoV threshold 1200, SoS baseline 1420)
- **Conference Quality:** Assigned a **Synthetic CQ** based on their schedule.

```
Indie_CQ = Average(CQ of all opponents' conferences)
```

**Rationale:** Independents don't have a conference to boost/drag them. Instead of an arbitrary zero or average, their "conference strength" is determined by the company they keep. If Notre Dame plays an all-ACC/Big Ten schedule, they get a P4-level CQ. If UMass plays mostly G5 teams, they get a G5-level CQ.

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
| **Team Quality (52%)** | Elo = 1750 | 1750 |
| **Record Score (38%)** | (calculated above) = 2775 | 2775 |
| **Conference Quality (10%)** | SEC CQ = 1380 | 1380 |

```
Final Score = (0.52 × 1750) + (0.38 × 2775) + (0.1 × 1380)
            = 910 + 1054.5 + 138
            = 2102.5
```

### Example: Tulane (11-1) in different conference

| Component | Calculation | Score |
|-----------|-------------|-------|
| **Team Quality (52%)** | Elo = 1600 (lower from playing weaker opponents) | 1600 |
| **Record Score (38%)** | (same 11-1) = 2775 | 2775 |
| **Conference Quality (10%)** | AAC CQ = 1150 | 1150 |

```
Final Score = (0.52 × 1600) + (0.38 × 2775) + (0.1 × 1150)
            = 832 + 1054.5 + 115
            = 2001.5
```

**Key:** Same record (11-1), but Georgia ranks higher due to:
1. Stronger Team Quality (better Elo from playing tougher opponents)
2. Slightly lower Conference Quality bonus/penalty

---

## Key Features & Design Decisions

### 1. Road Wins Matter More (1.1x)
Playing and winning on the road is inherently harder. Teams get a 10% boost for road wins.

### 2. Iterative Solver (4 passes)
Early-season games are re-evaluated based on final-season opponent strength, ensuring fair assessment when teams were still unknown. V4.0 adds a 4th pass for better convergence on close resumes.

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
- G5 vs G5 games (0.65x weight, V4.0) allow quality G5 teams to build Elo while preventing runaway inflation
- FCS games (0.1x-0.2x weight) keep FCS isolated
- This creates natural stratification between tiers

### 8. Conference Quality Adjustment
Weak OOC records reduce conference CQ; strong OOC records increase it. Prevents weak conferences from unfairly boosting all members.

### 9. Explicit Loss Penalty (V4.0 New)
Multi-loss teams are penalized progressively: 1 loss = -180, 2 losses = -399, 3 losses = -650. This addresses fan perception that 2-3 loss teams were ranked too high compared to polls.

### 10. G5 Credibility System (V4.0 Phase 2)
Multiple mechanisms boost quality G5 teams:
- **Tier-specific SoV:** Lower threshold (1050 vs 1200) gives credit for intra-G5 wins
- **Tier-specific SoS:** Lower baseline (1300 vs 1420) reduces schedule penalty
- **Cross-tier bonus:** +80 points per P4 opponent defeated
- **Upset multipliers:** ×1.20 for any G5>P4 win, stacking with ×1.25 for major upsets
- **Reduced damping:** G5 vs G5 weight 0.65 (was 0.5) allows Elo growth

**Target Impact:** JMU/Tulane-caliber teams should rank #12-18 instead of #20+.

---

## Version History

- **V4.1 (Current):** Diminished loss penalty (power formula 100*L^1.05), boosted H2H bonuses (88/44), boosted Quality Loss bonus (0.165 mult), removed Win Streak bonus.
- **V4.0.2:** Resume rebalancing. Reduced SoV multipliers (P4: 0.35, G5: 0.45), reduced SoS log multiplier (80 from 160), reduced H2H bonuses (80/40, max 200), reduced QL impact (threshold 1600, mult 0.15, cap 30), adjusted loss penalty (base 150). FBS Independents now treated as Power 4 tier with CQ=0.
- **V4.0.1:** Hotfix for ND resume anomaly. Capped H2H bonus at 300 max, capped QL bonus at 50 per loss, added Elo floor (1500) for Top-25 H2H credit, added Indie SoS baseline (1350) to penalize soft independent schedules. Synced app.py defaults with V4.0.
- **V4.0 Phase 3:** Head-to-head bonus (+120 per Top 10 win, +60 per Top 25 win), quality loss bonus (scaled by opponent Elo above 1550), G5 win streak bonus (+150 for ≤1 loss and ≥7 conf wins).
- **V4.0 Phase 2:** Upset bonuses (×1.25 for 150+ Elo gap, ×1.20 for G5>P4), tier-specific SoV (P4: 1200/0.5, G5: 1050/0.55), tier-specific SoS baselines (P4: 1420, G5: 1300), hybrid CQ (70% top half + 30% full), cross-tier win bonus (+80 per G5>P4 win).
- **V4.0 Phase 1:** 85% fresh priors (prior_strength=0.15), G5 matchup weight 0.65, 4 Elo iterations, explicit loss penalty (-180 × losses^1.15), reweighted FRS to 0.52/0.38/0.10.
- **V3.9:** Reduced legacy bias (30% prior vs 70% fresh), dropped Y-3 from priors, logarithmic SoS scaling, reweighted FRS to 0.55/0.35/0.10.
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

