# College Football Ranking System - Algorithm V3.4

This document outlines the mathematical framework used in Version 3.4 of the ranking system. The system uses a **Resume-Dominant Hybrid** model that prioritizes actual on-field results (Record) while using Elo to differentiate between teams with similar records based on Strength of Schedule.

## Core Philosophy

1.  **Resume First:** Winning matters most. A team with a significantly better record (e.g., 11-2) should generally rank ahead of a team with a mediocre record (e.g., 8-5), regardless of schedule strength.
2.  **Elo as Context:** Elo is used as a "Strength of Schedule" and "Margin of Victory" context provider, not as a pure predictor. It differentiates between an 11-1 SEC team and an 11-1 MAC team.
3.  **Zero-Sum Economy:** The core Elo engine remains zero-sum to prevent inflation.

---

## Mathematical Model

### 1. Logistic Elo Formula (50% Weight)

We use the standard Logistic Elo expectation formula to calculate the probability of winning:

$$ E_A = \frac{1}{1 + 10^{(R_B - R_A) / 400}} $$

*   $E_A$: Expected score for Team A (Probability of winning).
*   $R_A$: Current Elo rating of Team A.
*   $R_B$: Current Elo rating of Team B.
*   $400$: Standard scaling factor.

### 2. Score Update (Delta)

The change in score ($\Delta$) is calculated after every game:

$$ \Delta = K \times W_{matchup} \times M_{mov} \times (S_{actual} - E_A) $$

Where:
*   **$K$ (Base Factor):** Default is **40.0**.
*   **$W_{matchup}$ (Matchup Weight):**
    *   P4 vs P4: **1.0**
    *   P4 vs G5: **0.8**
    *   G5 vs G5: **0.5**
    *   vs FCS: **0.2**
*   **$M_{mov}$ (Margin of Victory Multiplier):**
    *   $M_{mov} = \ln(|Score_A - Score_B| + 1)$

### 3. Record Score (40% Weight)

To ensure that "winning matters" regardless of opponent strength, we calculate a **Record Score** that maps a team's winning percentage to the Elo scale (1000-2000).

$$ RecordScore = 1000 + (WinPercentage \times 1000) $$

*   **1.000 (Undefeated):** 2000 points
*   **0.500 (Average):** 1500 points
*   **0.000 (Winless):** 1000 points

### 4. Final Ranking Score (FRS)

The final ranking is a composite of three factors:

$$ FRS = (0.5 \times TeamQuality) + (0.4 \times RecordScore) + (0.1 \times ConferenceQuality) $$

*   **TeamQuality (50%):** The final Elo rating (Strength of Schedule / Quality).
*   **RecordScore (40%):** The win percentage score (Deserving Resume).
*   **ConferenceQuality (10%):** The average Elo of the conference (Context).

---

## Example Calculation: Florida vs BYU (2024)

**Scenario:**
*   **Florida (8-5):** Elo 1734, Conf 1762, Win% 0.615
*   **BYU (11-2):** Elo 1659, Conf 1617, Win% 0.846

**Florida FRS:**
*   Elo Part: $0.5 \times 1734 = 867.0$
*   Record Part: $0.4 \times (1000 + 615) = 646.0$
*   Conf Part: $0.1 \times 1762 = 176.2$
*   **Total:** **1689.2**

**BYU FRS:**
*   Elo Part: $0.5 \times 1659 = 829.5$
*   Record Part: $0.4 \times (1000 + 846) = 738.4$
*   Conf Part: $0.1 \times 1617 = 161.7$
*   **Total:** **1729.6**

**Result:** BYU (1729) > Florida (1689). The 40% weight on record ensures the 11-win team ranks ahead of the 8-win team, despite Florida's superior strength of schedule.

---

## Project History

*   **V1.0:** Simple additive points.
*   **V2.0:** Iterative Accumulator (Failed: Inflation).
*   **V3.0:** Logistic Elo (Success: Realistic Rankings).
*   **V3.1:** Refined Weights (Reduced Conf to 10%).
*   **V3.2:** Hybrid Elo (Added 20% Record Weight).
*   **V3.4:** Resume-Dominant (Current: 50% Elo / 40% Record / 10% Conf). Increased Record weight to fix "8-5 Power Team" inflation.

---

### Enhanced Team Quality Scores

The current system assigns fixed initial points to teams based on their conference (e.g., Power 4: 100, Group of 5: 80, FCS: 60) and adjusts scores with fixed increments based on game outcomes against opponent types. This approach lacks precision, as it doesn’t account for the actual strength of opponents. To make the system mathematically robust:

#### Dynamic Adjustments Based on Opponent Quality
- **Concept**: Adjust a team’s quality score based on the opponent’s current quality score, ensuring that beating stronger teams yields greater rewards and losing to weaker teams incurs larger penalties.
- **Mathematical Formulation**:
  - Let \( Q_A \) be Team A’s quality score, and \( Q_B \) be Team B’s quality score before a game.
  - If Team A beats Team B:
    - \( Q_A' = Q_A + \alpha \cdot Q_B \)
    - \( Q_B' = Q_B - \alpha \cdot Q_A \)
  - If Team A loses to Team B:
    - \( Q_A' = Q_A - \alpha \cdot Q_B \)
    - \( Q_B' = Q_B + \alpha \cdot Q_A \)
  - Here, \( \alpha \) is a scaling factor (e.g., \( \alpha = 0.1 \)), controlling the magnitude of adjustments.
- **Why It’s Pure**: This creates a zero-sum exchange where the total quality in the system remains balanced, and adjustments reflect the relative strength of opponents dynamically.

#### Home/Away Consideration
- **Concept**: Account for the increased difficulty of away games by adjusting the scaling factor based on game location.
- **Mathematical Formulation**:
  - For an **away win**: \( Q_A' = Q_A + 0.15 \cdot Q_B \), \( Q_B' = Q_B - 0.15 \cdot Q_A \)
  - For a **home win**: \( Q_A' = Q_A + 0.1 \cdot Q_B \), \( Q_B' = Q_B - 0.1 \cdot Q_A \)
  - For a **home loss**: \( Q_A' = Q_A - 0.15 \cdot Q_B \), \( Q_B' = Q_B + 0.15 \cdot Q_A \)
  - For an **away loss**: \( Q_A' = Q_A - 0.1 \cdot Q_B \), \( Q_B' = Q_B + 0.1 \cdot Q_A \)
- **Why It’s Pure**: The differential scaling (0.15 vs. 0.1) mathematically reflects the empirical advantage of home-field performance, ensuring fairness across game contexts.

#### Optional Against-the-Spread (ATS) Performance
- **Concept**: Reward teams for exceeding expectations by covering the spread or winning outright as underdogs.
- **Mathematical Formulation**: Add a fixed bonus (e.g., 10 points) to \( Q_A' \) if Team A beats or covers the spread.
- **Why It’s Optional**: While this adds predictive nuance, it introduces an external variable (betting spreads) that may not align with a purely performance-based system. Make it user-configurable.

#### Initialization
- Start with initial quality scores: Power 4 = 100, Group of 5 = 80, FCS = 60. These serve as priors that adjust dynamically as games are played.

---

### Improved Conference Quality Scores

The current system uses fixed points for conference quality based on games played and outcomes, which doesn’t adapt to actual team performance within the conference. A mathematically pure approach ties conference strength to its teams’ quality scores.

#### Average Team Quality
- **Concept**: Define the conference quality score as the mean of its teams’ quality scores, reflecting collective strength.
- **Mathematical Formulation**:
  - For a conference \( C \) with \( n \) teams, where each team \( i \) has quality score \( Q_i \):
    - \( CQ_C = \frac{1}{n} \sum_{i=1}^n Q_i \)
- **Why It’s Pure**: This ensures the conference score is a direct, unbiased aggregation of individual performances, avoiding arbitrary fixed adjustments. It dynamically updates as team scores change, maintaining consistency.

---

### Refined Final Ranking Scores

The current final ranking score (team quality + sum of beaten teams’ scores + conference quality for conference wins) risks imbalance due to the cumulative effect of beaten teams’ scores, which can disproportionately favor teams with many wins against weak opponents. A simpler, mathematically balanced formula is:

#### Simplified Combination
- **Concept**: Combine team quality with a weighted conference quality score to balance individual and collective performance.
- **Mathematical Formulation**:
  - Final Ranking Score for Team \( A \), \( FRS_A \):
    - \( FRS_A = Q_A + k \cdot CQ_{C_A} \)
  - Where \( Q_A \) is Team A’s quality score, \( CQ_{C_A} \) is the conference quality score of Team A’s conference, and \( k \) is a weighting factor (e.g., \( k = 0.5 \)).
- **Why It’s Pure**: This avoids over-amplification from summing beaten teams’ scores, ensuring the ranking reflects both a team’s standalone strength and its conference context. The constant \( k \) scales the influence of conference strength, tunable for balance.

#### Parameter Tuning
- Allow users to adjust:
  - Initial scores (e.g., Power 4: 100, Group of 5: 80, FCS: 60).
  - Adjustment factors (\( \alpha = 0.1 \) or 0.15 for home/away).
  - Conference weight (\( k = 0.5 \)).
- This interactivity ensures the system can be calibrated to reflect different philosophies while remaining mathematically consistent.

---

### User Interface Enhancements

To make the rankings transparent and user-friendly, update the app’s displays:

- **Conference Rankings**:
  - Columns: Conference Name | Record vs. Power 4 | Record vs. Group of 5 | Record vs. FCS | Average Team Quality Score (\( CQ_C \))
- **Team Quality Scores**:
  - Columns: Team Name | Team Record | Conference Game Record | ATS Record | Base Team Quality Score (\( Q_A \))
- **Final Team Rankings**:
  - Columns: Team Name | Record vs. Power 4 | Record vs. Group of 5 | Record vs. FCS | Base Team Quality Score (\( Q_A \)) | Conference Quality Score (\( CQ_{C_A} \)) | Total Team Ranking Score (\( FRS_A \))

These displays provide a clear view of how rankings are derived, enhancing trust in the system.

---

### Mathematical Purity and Implementation Considerations

#### Ensuring Convergence
- The dynamic adjustments form an iterative system. To prevent instability (e.g., scores diverging to infinity), process games sequentially each week, updating all scores after each game. This mimics real-time ranking updates and ensures convergence as the season progresses.

#### Edge Cases
- **Teams Without Games**: Retain initial scores until they play, ensuring early rankings remain fair.
- **Small Conferences**: The average team quality score remains valid, though it may be more volatile with fewer teams. This reflects reality and requires no adjustment.

#### Normalization
- Optionally, normalize final scores to a 0–100 scale after each week for readability:
  - \( FRS_{A,\text{normalized}} = 100 \cdot \frac{FRS_A - \min(FRS)}{\max(FRS) - \min(FRS)} \)
- This preserves rank order while making scores intuitive.

---

### Conclusion

This enhanced system is mathematically pure because:
- Team quality scores adapt dynamically to opponent strength, ensuring fairness and balance.
- Conference quality scores aggregate team performance without bias, reflecting true collective strength.
- Final rankings combine individual and conference factors in a controlled, scalable way, avoiding skews.

By implementing these changes, your app will produce rankings that accurately mirror the college football landscape, potentially rendering subjective committee decisions obsolete. The tunable parameters and clear UI further empower users to explore and trust the system.

---

### Project History & Evolution

#### Version 1.0: Initial Concept
- **Mechanism:** Simple additive points based on wins/losses and conference tiers.
- **Result:** Functional but simplistic. Didn't account for strength of schedule well.

#### Version 2.0: Iterative Accumulator
- **Mechanism:** Iterative solver with asymmetric rewards (underdogs gain more).
- **Failure:** "Accumulator" effect. Teams with many games (even losses) could accumulate high scores because penalties weren't severe enough.
- **Symptom:** D2 teams ranked too high.

#### Version 2.1: Strict Filtering
- **Mechanism:** Added strict division-based filtering and matchup penalties.
- **Failure:** Still suffered from inflation. A 7-6 Georgia Tech team ranked #1 in 2024 because they played a "hard schedule" and accumulated points from "quality losses" or minor wins that weren't penalized enough.
- **Symptom:** 7-6 team ranked #1.

#### Version 3.0: Logistic Elo (Current Standard)
- **Mechanism:** Zero-sum Logistic Elo model.
    - **Expectation:** $E_A = 1 / (1 + 10 ^ ((R_B - R_A) / 400))$
    - **Update:** $\Delta = K \times MatchupWeight \times MoV \times (Actual - Expected)$
    - **Tiers:** Power 4 (1500), Group of 5 (1200), FCS (900).
    - **Damping:** G5 vs G5 games have 0.5x weight to prevent internal inflation.
    - **Priors:** Weighted average of last 3 years (50%/30%/20%) on Elo scale.
- **Result:** 2024 Verification produced a realistic top 5 (Oregon, Ohio State, Georgia, Texas, Penn State) and correctly tiered conferences (SEC > B10 > B12 > ACC).
- **Status:** **SUCCESS**. This is the current production algorithm.