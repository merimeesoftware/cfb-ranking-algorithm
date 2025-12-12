# CFB Ranking Algorithm - Complete Breakdown (V4.4 Recalibration)

## Master Formula

```
FRS = (0.55 × TeamQuality) + (0.37 × RecordScore) + (0.08 × ConferenceQuality)
```

**Final Ranking Score (FRS)** combines three weighted components to produce the final rankings.

---

## 1. Team Quality (50%) — Elo-Based Rating

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

## 2. Record Score (42%) — Resume / Deserving Component

Rewards **winning record**, **schedule difficulty**, and **quality of victories**. Penalizes **bad losses** specifically rather than all losses. This component answers: "Does this team's resume deserve a high ranking?"

### Record Score Formula

```
RecordScore = 1000 + (WeightedWinPct × 1000) + SoV_Bonus + SoS_Score + CrossTier_Bonus 
            + H2H_Bonus + QL_Bonus + QW_Bonus - BadLoss_Penalty - BaseLoss_Penalty + Undefeated_Bonus
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
# Power 4 teams (V4.4: reduced multiplier)
SoV_Bonus = (AvgWinElo - 1200) × 0.25   [if AvgWinElo > 1200]

# Group of 5 teams (V4.0.2: reduced multiplier)
SoV_Bonus = (AvgWinElo - 1050) × 0.45   [if AvgWinElo > 1050]
```

| Tier | Threshold | Multiplier | Rationale |
|------|-----------|------------|------------|
| Power 4 | 1200 | 0.25 | V4.4: Reduced from 0.35 to dampen resume inflation |
| Group of 5 | 1050 | 0.45 | V4.0.2: Reduced from 0.55 to balance with P4 |

**Examples:**
- P4 team, Avg win Elo = 1500: `(1500 - 1200) × 0.25 = +75 points`
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
# Power 4 teams (baseline 1400) - V4.3: reduced baseline
if AvgOpponentElo > 1400:
    SoS_Score = log(max(AvgOpponentElo - 1400, 1)) × 80
else:
    SoS_Score = (AvgOpponentElo - 1400) × 0.5

# Group of 5 teams (baseline 1300)
if AvgOpponentElo > 1300:
    SoS_Score = log(max(AvgOpponentElo - 1300, 1)) × 80
else:
    SoS_Score = (AvgOpponentElo - 1300) × 0.5
```

| Tier | Baseline | Rationale |
|------|----------|------------|
| Power 4 | 1400 | V4.3: Reduced from 1420 to better value "good" schedules |
| Group of 5 | 1300 | Lower bar; typical G5 slate shouldn't be heavily penalized |

**V4.0.2 Change:** Reduced log multiplier from 160 to 80 and penalty multiplier from 0.8 to 0.5 to prevent schedule from dominating resume score.

**Impact Examples:**
| Team Type | Avg Opp Elo | Old SoS (1400 baseline) | New SoS (tier-specific) |
|-----------|-------------|-------------------------|-------------------------|
| P4, tough schedule | 1550 | +117 | +109 |
| G5, average schedule | 1280 | -60 | -16 |
| G5, good schedule | 1350 | -25 | +35 |

#### Sub-Component 4: Bad Loss Penalty (V4.5)

Replaces the flat loss penalty. Penalizes losses to **significantly weaker opponents** (200+ Elo gap), blowout losses to weaker teams, OR moderate-gap blowouts.

```
# Case 1: Loss to much weaker team (180+ Elo gap)
if OpponentElo < (TeamElo - 180):
    EloGap = TeamElo - OpponentElo
    BasePenalty = (EloGap - 180) × 0.40
    MoV_Mult = log(abs(MoV) + 1) if MoV < -10 else 1.0
    Penalty = min(BasePenalty × MoV_Mult, 100)

# Case 2: Blowout loss (21+ pts) to a WEAKER opponent only
elif MoV <= -21 and OpponentElo < TeamElo:
    Penalty = min(10 + (abs(MoV) - 21) × 1.0, 37.5)

# Case 3: Minor bad loss - moderate gap (150-180) AND blowout (21+ pts)
elif MoV <= -21 and (TeamElo - 150) > OpponentElo >= (TeamElo - 180):
    EloGap = TeamElo - OpponentElo
    Penalty = min((EloGap - 150) × 0.08 + (abs(MoV) - 21) × 0.5, 25)
```

| Scenario | Penalty | Interpretation |
|----------|---------|----------------|
| Loss to stronger team | 0 | "Quality loss" - no penalty |
| Loss to similar team | 0 | Expected variance |
| Loss to 180+ weaker team | Scaled (max 100) | Truly bad loss |
| Blowout (21+) to weaker team | 10-37.5 | Non-competitive performance |
| Moderate gap (150-180) + blowout | Scaled (max 25) | Minor bad loss |

**V4.5 Change:** Added **Case 3: Minor bad loss tier** for moderate Elo gaps (150-180) combined with blowouts (21+ points).

**V4.4 Change:** Tightened threshold to **180 Elo gap** and increased multiplier to 0.40. This ensures losses to genuinely inferior teams are heavily penalized.

#### Sub-Component 5: Head-to-Head Bonus (V4.1)

Rewards teams for defeating top-ranked opponents in the current rankings:

```
H2H_Bonus = min((Top10_Wins × 100) + (Top25_Wins × 50), 250)
```

| Win Type | Bonus | Rationale |
|----------|-------|----------|
| Win vs Top 10 Team (Elo > 1650) | +100 | V4.3: Boosted to reward elite wins |
| Win vs Top 11-25 Team (Elo > 1550) | +50 | V4.3: Boosted to reward ranked wins |
| Maximum Total | 250 | V4.3: Capped to prevent runaway stacking |

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

#### Sub-Component 7: Quality Win Bonus (V4.5)

Rewards wins against **top-20 caliber teams** using an absolute Elo threshold.

```
if OpponentElo >= 1625:
    EloAboveFloor = OpponentElo - 1625
    BaseBonus = 25 + (EloAboveFloor × 0.30)
    
    # MoV multiplier for dominant wins
    if MoV >= 14:
        MoV_Mult = 1.0 + log(MoV - 12) × 0.15  # Up to ~1.4x
    elif MoV >= 7:
        MoV_Mult = 1.0
    else:
        MoV_Mult = 0.8  # Close game penalty
    
    Bonus = min(BaseBonus × MoV_Mult, 100)
```

| Opponent Elo | Base Bonus | With 21-pt MoV |
|--------------|------------|----------------|
| 1625 | +25 | +35 |
| 1700 | +47.5 | +66.5 |
| 1800 | +77.5 | +100 (capped) |

**V4.5 Change:** Raised threshold to **1625 (Top 20)** and removed the "Good Record" loophole (previously 1500+ Elo & 8+ wins). This ensures:
- Only wins over genuinely elite teams count
- Prevents "farming" bonuses from beating average Power 4 teams
- Reduces inflation for conferences with many mid-tier teams

#### Sub-Component 8: Bad Win Penalty (V4.4)

Penalizes close wins (7 points or fewer) against **truly weak teams** using an absolute Elo threshold.

```
if OpponentElo < 1300 and MoV <= 7:
    Penalty = min(10 + (7 - MoV) × 1.5, 40)
```

| MoV | Penalty |
|-----|--------|
| 7 pts | 10 |
| 3 pts | 16 |
| 1 pt | 19 |

**V4.4 Change:** Switched from relative threshold (TeamElo - 200) to **absolute threshold (1300)**. This ensures:
- Good teams aren't unfairly penalized for close wins against average opponents
- Only close wins against genuinely weak teams (1300 Elo ≈ bottom-tier FBS) count as "bad"
- Georgia beating a 1450 Elo team by 3 points is NOT a bad win (they're a decent team)

### Full Record Score Example

A team with:
- 11-1 record (9 home wins, 2 road wins)
- Beaten opponents average Elo = 1600
- Overall schedule average Elo = 1650
- Loss was to #3 team (Quality Loss, not Bad Loss)

```
Weighted Win %  = ((9 × 1.0) + (2 × 1.1)) / 11 = 10.2 / 11 = 0.927
Win contribution = 0.927 × 1000 = 927 points

SoV Bonus       = (1600 - 1200) × 0.5 = 400 × 0.5 = 200 points
SoS Score       = log(max(1650 - 1400, 1)) × 150 = log(250) × 150 = 828 points
Bad Loss Penalty = 0 (Loss was to stronger team)

RecordScore     = 1000 + 927 + 200 + 828 - 0 = 2955 points
```

---

## 3. Conference Quality (8%) — Contextual League Boost

Measures the overall strength of a team's conference to provide contextual credit. A team in a weak conference should be penalized; a team in a strong conference gets a small boost.

### Conference Quality Formula

```
CQ = (RawCQ + Depth_Adj - BadLoss_Agg) × OOC_Multiplier
```

The raw conference strength is adjusted by depth, bad losses, and OOC performance.

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

#### Sub-Component 2: Depth Adjustment (V4.2)

Uses standard deviation to reward deep conferences and penalize top-heavy ones.

```
Depth_Adj = (200 - StdDev) * 0.2
```

- **Low StdDev (Tight grouping):** Bonus (e.g., Big 12 often has many teams clustered together)
- **High StdDev (Top heavy):** Penalty (e.g., CUSA often has 1-2 good teams and many bad ones)

#### Sub-Component 3: Bad Loss Aggregation (V4.2)

Conferences are penalized if their member teams frequently suffer "bad losses" (losing to significantly weaker opponents).

```
BadLoss_Agg = Average(BadLossPenalty per team) * 0.05
```

#### Sub-Component 4: Out-of-Conference (OOC) Multiplier

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
| vs Power 4 | 1.2 |
| vs Group of 5 | 0.5 |
| vs FCS | 0.1 |

**V4.2:** Increased P4 weight to 1.2 to further emphasize quality OOC wins.

### Special Case: FBS Independents

Teams without a conference (like Notre Dame, Army) are handled specially:

**V4.1 Changes:**
- **Conference Type:** Treated as "Power 4" for all tier-based calculations (SoV threshold 1200, SoS baseline 1420)
- **Conference Quality:** Assigned a **Synthetic CQ** based on their schedule.

```
Indie_CQ = (0.7 * Avg_Sched_CQ) + (0.3 * Avg_Opp_Elo)
```

**Rationale:** Independents don't have a conference to boost/drag them. Instead of an arbitrary zero or average, their "conference strength" is determined by the company they keep. If Notre Dame plays an all-ACC/Big Ten schedule, they get a P4-level CQ. If UMass plays mostly G5 teams, they get a G5-level CQ.

### Full Conference Quality Example

**ACC Example:**

```
RawCQ = 1300 (top 50% of teams average 1300)
Depth Adjustment = +10 (Tight grouping)
Bad Loss Aggregation = -5 (Some bad losses)
OOC Performance:
  - vs P4: 5-8 (weighted: 5 wins, 8 losses)
  - vs G5: 12-3 (weighted: 6 wins, 1.5 losses)
  - vs FCS: 20-0 (weighted: 2 wins, 0 losses)

WeightedWins = 5 + 6 + 2 = 13
WeightedTotal = 5 + 8 + 6 + 1.5 + 2 + 0 = 22.5
PerformanceRatio = 13 / 22.5 = 0.578
OOC_Multiplier = 0.8 + (0.4 × 0.578) = 0.8 + 0.231 = 1.031

Final CQ = (1300 + 10 - 5) × 1.031 = 1345
```

---

## How All Three Components Work Together

### Example: Georgia (11-1)

| Component | Calculation | Score |
|-----------|-------------|-------|
| **Team Quality (50%)** | Elo = 1750 | 1750 |
| **Record Score (42%)** | (calculated above) = 2955 | 2955 |
| **Conference Quality (8%)** | SEC CQ = 1380 | 1380 |

```
Final Score = (0.50 × 1750) + (0.42 × 2955) + (0.08 × 1380)
            = 875 + 1241.1 + 110.4
            = 2226.5
```

### Example: Tulane (11-1) in different conference

| Component | Calculation | Score |
|-----------|-------------|-------|
| **Team Quality (50%)** | Elo = 1600 (lower from playing weaker opponents) | 1600 |
| **Record Score (42%)** | (same 11-1) = 2955 | 2955 |
| **Conference Quality (8%)** | AAC CQ = 1150 | 1150 |

```
Final Score = (0.50 × 1600) + (0.42 × 2955) + (0.08 × 1150)
            = 800 + 1241.1 + 92
            = 2133.1
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

### 9. Contextual Loss Penalty (V4.2 New)
Replaced flat loss penalty with "Bad Loss Penalty". Losing to a superior team is forgiven; losing to an inferior team is penalized.

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

- **V4.4 Recalibration (Current):** Adjusted FRS weights to 0.55/0.37/0.08 to reduce Record Score inflation. Added exponential loss penalty (-150 * L^1.1) and undefeated bonus (+100). Raised Quality Win threshold to 1650 (Top 15). Tightened Bad Loss threshold to 180.
- **V4.5 (Legacy):** Reduced Conference Quality weight from 10% to **8%**, increased Record Score from 40% to **42%** (weights now 0.50/0.42/0.08). Added **minor bad loss tier** (Case 3) for moderate Elo gaps (150-200) combined with blowouts (21+ points). This catches scenarios like Texas losing badly to a decent opponent while Georgia's close loss to Alabama correctly remains penalty-free.
- **V4.4:** Switched Quality Win and Bad Win from relative thresholds to **absolute thresholds**. Quality Win now requires opponent Elo ≥ 1550 (top-25 caliber). Bad Win now requires opponent Elo < 1300 (weak teams only). Bad Loss threshold increased to 200 Elo gap. Blowout bad loss only applies to weaker opponents. This prevents good teams from being unfairly penalized.
- **V4.3:** Rebalanced FRS weights (0.50/0.40/0.10) to emphasize on-field results. Added SOS, Quality Wins, Bad Wins, and Bad Losses to comparison metrics.
- **V4.2:** Contextual overhaul. Replaced flat loss penalty with Bad Loss Penalty (threshold 100 Elo). Added Quality Win Bonus (threshold 100 Elo). Enhanced Conference Quality with Depth Adjustment (StdDev) and Bad Loss Aggregation. Rebalanced FRS weights (0.62/0.28/0.10).
- **V4.1:** Diminished loss penalty (power formula 100*L^1.05), boosted H2H bonuses (88/44), boosted Quality Loss bonus (0.165 mult), removed Win Streak bonus.
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

