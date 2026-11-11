# Front-end story review

Audit of the board before this change, the flow this change ships, and every public string that changed. The positioning line stays verbatim:

The order you check before you argue — not a poll, not a committee, not the narrative.

## Audit (before)

Pages were opened on the published 2026 week 10 board at 390×844 and 1440×900.

Home. The field hero (brand, tagline, positioning line, share buttons) filled the first screen. At 1440 the table header barely appeared. At 390 no team row appeared. The order was a jump away. Wording on the hero was already the approved line. The share control said Top 25 and copied five names.

Week. A quieter page: tagline, optional story, then the table. No positioning line. Footer and citation were present.

Team. Rank, TR+, how they look, and who they beat. No league part and no account of how those numbers become the board score. "Ask why they're here" opened the assistant before the arithmetic.

Games. Two cards with rank and TR+. No conference names and no account of which part separates the teams.

Methodology. The mix was printed as 0.65 / 0.27 / 0.08. The page also said the parts are rescaled to 0–100, K is 40, home-field advantage is 65, and upsets are 1.25× capped at 1.20×. The ranker uses 0.80 / 0.15 / 0.05, K 50, home-field 50, upset 1.18×, and a Group of 5 over Power 4 multiplier of 1.12×. Group of 5 vs Group of 5 was printed as 0.5; the code uses 0.65.

Conferences. FBS Independents was stored and filtered as Power 4 even though Notre Dame is Power 4 and the other independents are not. The row did not say so.

Footer. Credit line and "How it works" / GitHub. Left as-is.

Meta. The default description in the document head is the positioning line. After load, the home description was a generated sentence with the tagline, not that line.

## Flow this change ships

1. Land on this week's order. The positioning line stays above it. At 1440 the first row is in the first screen, under the filters. At 390 the top of the board is in the first screen; filters follow the table.
2. Open a team. The three weighted parts are on the page and add up to the board score. The assistant is after that.
3. Compare two teams on the same published week. The page names each conference and which part is higher.
4. How it works uses the same weights. An exploratory slider can reorder a what-if on this browser. It does not change the official board.

## Copy table

Shipped strings. "Was" is the previous public text. "Proposed" is what this branch renders. Numbers come from the ranker defaults in `frontend/src/lib/publicFormula.json`.

| Where | Was | Proposed |
| --- | --- | --- |
| Home and week meta description | True Rankings TR+ board for {year} Week {week}. How good they actually are. | True Rankings, {year} Week {week}. The order you check before you argue — not a poll, not a committee, not the narrative. |
| Week page, under the tagline | (not shown) | The order you check before you argue — not a poll, not a committee, not the narrative. |
| Methodology, the mix | (0.65 × how they look) + (0.27 × who they beat) + (0.08 × league strength) | (0.80 × how they look) + (0.15 × who they beat) + (0.05 × league strength) |
| Methodology, under the mix | All components are normalized to a 0–100 scale before weighting. | The board score is those three parts added together. They are not rescaled to 0–100 before the weights. |
| Methodology cards | How they look (65%) / Who they beat (27%) / League strength (8%) | How they look (80%) / Who they beat (15%) / League strength (5%) |
| Methodology, K-factor | Base volatility = 40. Reduced in postseason (0.6-0.7) to prevent "Bowl Bias". | Base volatility = 50. Reduced in postseason (0.65×) so bowl games move the rating less. |
| Methodology, upset intro | Upsets receive bonus multipliers, but are subject to a global cap (1.20×) and a "Chaos Tax" in high-variance conferences: | A major upset (Elo gap over 150) is multiplied by 1.18×. A Group of 5 win over a Power 4 team is multiplied by 1.12×. Those can stack. High-variance conferences still take the chaos tax: |
| Methodology, upset cards | 1.25× Major Upset, 150+ Elo gap (Capped at 1.20×). 1.20× Cross-Tier, G5 beats P4 team. | 1.18× Major upset, Elo gap over 150. 1.12× Cross-tier, Group of 5 beats Power 4. |
| Methodology, G5 vs G5 weight | 0.5 | 0.65 |
| Methodology, illustration | Δ = 40 × 1.0 × 1.08 × (1.0 - 0.60) = +17.3 Elo. Post-game 1667 and 1563. | Δ = 50 × 1.0 × 1.08 × (1.0 - 0.60) = +21.6 Elo. Post-game 1671.6 and 1558.4. Illustration only. It uses the published K and skips home-field advantage. |
| Methodology, résumé note | All components are calculated then normalized to 0-100 scale. | The résumé score stays on the same scale as the other two ratings. |
| Methodology, résumé example | Total: 2202 → Normalized to ~72/100 | Total: 2202 on the résumé scale |
| Methodology, league example | FinalCQ = 1490 × 1.10 = 1639 → Normalized to ~85/100 | FinalCQ = 1490 × 1.10 = 1639 |
| Methodology, home field | Home-Field Advantage: 65 Elo bonus for home team expectation | Home-field advantage: 50 points on the home team's expected result |
| Methodology, postseason | Postseason K Reduction: 0.65× K-factor for bowl games | Postseason K: 0.65× K for bowl games |
| Methodology, balance | How they look (65%) … who they beat (27%) … | How they look (80%) … who they beat (15%) … |
| Methodology, independents | Teams without a conference (Notre Dame, UConn, UMass) receive a Synthetic Conference Quality score. … If they play a P4 schedule, they get a P4 boost; if they play a G5 schedule, they get a G5 boost. | Teams without a conference get a synthetic league-strength score: the average of the conferences on their schedule. Notre Dame is Power 4. The other independents are not, so the Independents row is mixed. |
| Conference row | FBS Independents treated as Power 4, with no tier on the row | FBS Independents shows the label Mixed. A one-tier conference shows that tier. |
| Conference modal subtitle | Avg Ranking Score: | {tier} · Avg ranking score |
| Team page and breakdown | Weights printed as 65% / 27% / 8% in the modal. Team page had no parts. | 80% / 15% / 5%, and "These three parts add up to the board score." Team page adds "How the board weights this". |
| Games | Side by side on the published TR+ board. Cards showed TR+ and record only. | Same line, plus each conference. New block: Why one is ahead. Same published week. Official board scores. Column Higher (or Even). |
| Share status | Top 5 copied for posting. The pasted list was a Top 5. | Top 25 copied for posting. The pasted list is the Top 25. The button stays Share Top 25. |
| Exploratory block (new) | (not shown) | Exploratory. Weight sliders. A what-if on this browser. It does not change the official board. Reset to the official weights. Official weights for {year} week {week}. What-if for {year} week {week}. Official order unchanged. This week's published board isn't available in the browser yet. Loading the published board… |

## Not changed, open for review

- The positioning line, the tagline "How good they actually are.", Share Top 25, Copy citation, and the CollegeFootballData.com credit.
- PRODUCT.md still names the fan as the hero. This pass puts the table first and does not rewrite that frame.
- "The best G5 teams can crack the Top 15." is still on the methodology page. This pass did not check that claim against the stored weeks.
- Stored team rows still tag every FBS independent as Power 4, including teams that are not. The conference row is relabelled Mixed at display time. The week files on disk are not rewritten, and the rating math is unchanged.
- The Ohio State illustration is still a made-up game. Only the K and the arithmetic that depends on it were corrected.
