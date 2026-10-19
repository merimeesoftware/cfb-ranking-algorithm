# ADR 0001: Product direction, 2026-10-18

- **Status:** Accepted by Michael Merimee, 2026-10-18 (10:47 PM ET)
- **Proposed path:** `docs/adr/0001-product-direction-2026-10-18.md` (the repo has no `docs/adr/` or `docs/decisions/` folder yet; this is the first ADR)
- **Decided by:** Michael Merimee (owner), relayed by OS
- **Related:** #93 (hardening, incl. PR2 removal of The Drop and betting), #94 (preview stills check), #96, #97, #98, #99, #100, PURPOSE.md amendment (pending signature)

## Context

True Rankings (repo `merimeesoftware/cfb-ranking-algorithm`) publishes a weekly college football ranking (TR+). On main @ 37f6ef0 the published score is 0.80 Elo team strength + 0.15 resume + 0.05 conference strength, built only from final scores, venue, conference tier and game notes. There is no time decay: games are applied in week order, so any "hot team" effect is only implicit in Elo's path dependence.

The locked PURPOSE.md (2026-09-28) aimed partly at bettors ("check before you argue or bet", model vs market, affiliate) and made The Drop email list the second success goal. The site still carries a `/drop/subscribe` endpoint and signup UI, a matchup "implied spread", and a CLI `--ats` / `/lines` path. The ask-the-AI endpoint takes free text and makes uncapped paid calls (#93).

On 2026-10-18 Michael set new product direction.

## Decision

1. **Thesis (amended).** The best team is the one whose game results show it is strongest, judged by one open formula with no voters. **Plus momentum:** teams that get hot at the right time reach a new level, and Elo was chosen partly to capture that. Momentum becomes an explicit, explainable part of the model.
   - Momentum gets its own visible number per team.
   - It is defined so it cannot reduce to chasing the last game (for example a decay half-life or weighted window, a minimum-games floor and a cap on any one game's share).
   - It ships only if it passes the gate on #96 (issuecomment-6258649874): Elo plus form is compared against Elo alone, judged by a paired bootstrap by week on the validate (2023) and holdout (2024) Brier, with tuning on 2019–2022 only, point estimate ≤ 0 on both splits. If the result is inconclusive (95% CI upper bound above +0.001), momentum gets weight 0 in the ordering and is still shown as its own number. FRS before/after is reported, not the bar. It's an internal fit check, never presented as a prediction.
2. **The Drop is out.** `/drop/subscribe`, the signup UI and the email-list goal are removed. (Done in the #93 PR2 that follows this ADR.)
3. **Gambling and prediction are out.** The matchup implied spread, the `--ats` / lines code, and any odds, picks or prediction framing are removed and not to return. Michael: "I don't want gambling anywhere near this." (Done in the #93 PR2 that follows this ADR. The `/games` page remains a head-to-head of published ratings.)
4. **Core product.** Engagement comes from fans debating the rankings:
   1. Make the algorithm crystal clear: explain and visualize it so a fan grasps it fast. (#97)
   2. A team "why here" view: click any team to see why it sits where it does (factors, key wins and losses, schedule strength, momentum). (#98)
   3. Conference rankings with the conference rating system, framed as evidence (for example, the Big 12 is called weak but holds up against other conferences; show the data). (#99)
   4. Ask-the-AI questions about the rankings, free or very cheap and hard-capped: a fixed question set with cached answers, consistent with #93. (#100)
5. **Monetization later.** Only if usage warrants it. Michael doesn't love ads; simple ones may be OK. Nothing is built for it now.
6. **Goal now: exposure on X** (@TrueCFB).
7. **Sequence:** #93 hardening first, then #96–#100, then an ideas round with the house team.

## Consequences

- PURPOSE.md must be amended (thesis plus momentum; remove bettor audience, "or bet" wording, model-vs-market, The Drop success goal and affiliate goal). Draft prepared for Michael's signature; the locked public line "Predictive order you check before you argue or bet…" changes, which only Michael can approve.
- `PRODUCT.md`, the brand spec, the README, and the public LLM notes were updated with the removal. `docs/THE-DROP.md` is deleted. PURPOSE.md is still the 2026-09-28 lock and still contains the bettor lines and The Drop goal; only Michael can change those locked lines. Open PR #69 "Betting layer on V5.3 Elo (GREEN / LEAN / PASS)" is left untouched and conflicts with decision 3. August 2026 audit notes still describe the old `/lines` path as history.
- The internal eval stays a next-week Brier backtest. It is used as an internal fit check only and is never presented publicly as predictions.
- Adding a momentum term changes the published formula, the cache key and the methodology page. The doc/code gaps in `/methodology` and `ALGORITHM_BREAKDOWN.md` (stale weights, K, HFA, prior fade) are fixed as part of #97 before any new visuals.
- No new paid calls (MiniMax, CFBD) on visitor paths until #93's caps are merged. Ask-the-AI (#100) depends on #93.
- All UI work waits for Dean's signed comps and the #94 preview stills check; user-facing copy needs a Phil consult against the amended PURPOSE.md.
- Conference evidence must report what the data shows. If the Big 12 does not hold up in a given season, the page says so.
