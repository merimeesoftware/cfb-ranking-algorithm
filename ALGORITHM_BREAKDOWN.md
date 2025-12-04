# CFB Ranking Algorithm - Complete Breakdown (V4.0)

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
# Power 4 teams
SoV_Bonus = (AvgWinElo - 1200) × 0.50   [if AvgWinElo > 1200]

# Group of 5 teams  
SoV_Bonus = (AvgWinElo - 1050) × 0.55   [if AvgWinElo > 1050]
```

| Tier | Threshold | Multiplier | Rationale |
|------|-----------|------------|------------|
| Power 4 | 1200 | 0.50 | Standard bar for quality wins |
| Group of 5 | 1050 | 0.55 | Lower bar + higher mult credits intra-G5 quality |

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
# Power 4 teams (baseline 1420)
if AvgOpponentElo > 1420:
    SoS_Score = log(max(AvgOpponentElo - 1420, 1)) × 160
else:
    SoS_Score = (AvgOpponentElo - 1420) × 0.8

# Group of 5 teams (baseline 1300)
if AvgOpponentElo > 1300:
    SoS_Score = log(max(AvgOpponentElo - 1300, 1)) × 160
else:
    SoS_Score = (AvgOpponentElo - 1300) × 0.8
```

| Tier | Baseline | Rationale |
|------|----------|------------|
| Power 4 | 1420 | Higher bar; P4 schedules should be tough |
| Group of 5 | 1300 | Lower bar; typical G5 slate shouldn't be heavily penalized |

**Impact Examples:**
| Team Type | Avg Opp Elo | Old SoS (1400 baseline) | New SoS (tier-specific) |
|-----------|-------------|-------------------------|-------------------------|
| P4, tough schedule | 1550 | +117 | +109 |
| G5, average schedule | 1280 | -60 | -16 |
| G5, good schedule | 1350 | -25 | +35 |

#### Sub-Component 4: Loss Penalty (V4.0 New)

```
Loss_Penalty = 180 × (num_losses ^ 1.15)
```

| Losses | Penalty | Interpretation |
|--------|---------|----------------|
| 0 | 0 | No penalty for undefeated teams |
| 1 | -180 | Single loss is costly but recoverable |
| 2 | -399 | Two losses significantly hurts ranking |
| 3 | -650 | Three losses drops team substantially |
| 4 | -923 | Four losses puts team out of contention |

**Philosophy:** Addresses fan perception that 2+ loss teams were ranked too high. The exponential (^1.15) scaling ensures each additional loss hurts progressively more. This drops teams like Alabama (10-2) and Texas (9-3) while preserving 1-loss contenders like Ole Miss.

#### Sub-Component 5: Head-to-Head Bonus (V4.0 Phase 3)

Rewards teams for defeating top-ranked opponents in the current rankings:

```
H2H_Bonus = (Top10_Wins × 120) + (Top25_Wins × 60)
```

| Win Type | Bonus | Rationale |
|----------|-------|----------|
| Win vs Top 10 Team | +120 | Major statement win deserves substantial credit |
| Win vs Top 11-25 Team | +60 | Quality win, but less impactful than top 10 |

**Examples:**
- Team with 2 wins vs Top 10 + 1 win vs Top 20: `(2 × 120) + (1 × 60) = +300 points`
- Team with 0 ranked wins: `+0 points`
- Team with 3 wins vs Top 25 (none Top 10): `(0 × 120) + (3 × 60) = +180 points`

**Philosophy:** Provides tiebreaker value for teams with similar records but different quality of wins. A 1-loss team that lost to #3 but beat #8 and #14 deserves credit over a 1-loss team with no ranked wins.

#### Sub-Component 6: Quality Loss Bonus (V4.0 Phase 3)

Rewards teams whose losses came against elite opponents (Elo > 1550):

```
for each loss:
    if opponent_elo > 1550:
        quality_loss_points += (opponent_elo - 1550) × 0.25

QL_Bonus = quality_loss_points / num_losses   [if num_losses > 0]
```

| Opponent Elo | Bonus per QL | Example |
|--------------|--------------|----------|
| 1550 | +0 | Threshold - no bonus |
| 1600 | +12.5 | (1600-1550) × 0.25 |
| 1700 | +37.5 | (1700-1550) × 0.25 |
| 1800 | +62.5 | (1800-1550) × 0.25 |

**Examples:**
- Team with 1 loss to #2 (Elo 1750): `(1750-1550) × 0.25 / 1 = +50 points`
- Team with 2 losses: to #3 (1700) and to #25 (1520): `((1700-1550) × 0.25 + 0) / 2 = +18.75 points`
- Team with 2 losses both to unranked teams: `+0 points`

**Philosophy:** "Quality of losses" matters. A team that lost only to playoff-caliber teams should be treated better than a team with losses to mediocre opponents. The division by number of losses ensures the bonus doesn't reward accumulating many losses.

#### Sub-Component 7: Win Streak Bonus (V4.0 Phase 3)

Rewards G5 teams demonstrating conference dominance:

```
if team_conference_type == 'Group of 5' AND num_losses <= 1 AND conf_wins >= 7:
    WinStreak_Bonus = 150
else:
    WinStreak_Bonus = 0
```

| Requirement | Threshold | Rationale |
|-------------|-----------|----------|
| Conference Type | Group of 5 | Only G5 teams need this boost |
| Maximum Losses | ≤ 1 | Ensures team is truly elite |
| Minimum Conf Wins | ≥ 7 | Demonstrates conference dominance |
| Bonus Amount | +150 | Significant boost to close gap with P4 |

**Examples:**
- JMU (G5, 11-1, 8 conf wins): Eligible → `+150 points`
- Tulane (G5, 10-2, 7 conf wins): NOT eligible (2 losses) → `+0 points`
- Ohio State (P4, 12-0, 9 conf wins): NOT eligible (P4 team) → `+0 points`
- Marshall (G5, 9-3, 6 conf wins): NOT eligible (3 losses, only 6 conf wins) → `+0 points`

**Philosophy:** Helps elite G5 teams bridge the gap to P4 teams. A dominant G5 team that runs the table in conference play deserves CFP consideration alongside 1-loss P4 teams.

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

- **V4.0.1 (Current):** Hotfix for ND resume anomaly. Capped H2H bonus at 300 max, capped QL bonus at 50 per loss, added Elo floor (1500) for Top-25 H2H credit, added Indie SoS baseline (1350) to penalize soft independent schedules. Synced app.py defaults with V4.0.
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

