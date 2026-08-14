# CFB Rankings — StoryBrand Plan (locked)

**Status:** BrandScript locked; Phase 1 copy approved; **implementation in progress on `cursor/storybrand-implement-66f9` (PR #64).**  
**Date:** 2026-08-14  
**Supersedes:** exploratory work on `cursor/fan-facing-copy-66f9` / PR #62 (reverted).

---

## Locked decisions

1. **SB7 frame** — confirmed (see BrandScript below).
2. **Primary CTA** — entice fans to open the **latest rankings** and **join the conversation / controversy**.
3. **Success order** — (1) share the take → (2) win the argument → (3) understand the formula.
4. **Code** — premature frontend rewrite reverted; messaging and structure land only after this plan.

---

## BrandScript (SB7)

### A character (Hero)

The college football fan who argues rankings every week — meathead *and* nerdy. They want a board they can trust enough to fight with.

### Has a problem

| Layer | Problem |
|-------|---------|
| **External** | Who is actually better? Who belongs higher this week? |
| **Internal** | If my take is wrong, I look clueless in the group chat / on X. |
| **Philosophical** | Rankings should reward the full body of work — not hype, voters, or black-box noise. |

### And meets a guide

**CFB Rankings** — empathy (“we know the fight”) + authority (“impartial board: who they beat, how they look, the league they live in”). The brand is the *guide*, never the hero.

### Who gives them a plan

1. Open this week’s board.  
2. Find your team (or scan the controversy at the top).  
3. Grab the take / path to climb.  
4. Jump into the argument — share, debate, dig only if you want the math.

### And calls them to action

| Type | CTA direction |
|------|----------------|
| **Primary** | See the latest rankings — join the conversation and the controversy. |
| **Secondary** | Share this take · Break down why · How the board works |

Exact button labels are written in Phase 1 copy (grunt-tested), not invented at build time.

### That helps them avoid failure

Opaque computer polls, voter vibes, spreadsheet dumps, and takes with no shareable backbone.

### And ends in success

1. **Share the take** — a clear, postable ranking claim.  
2. **Win the argument** — a board + reason strong enough to stand on.  
3. **Understand the formula** — optional depth for the nerdy path (never required to use the product).

---

## Grunt Test / 5-second rule

Donald Miller: in ~5 seconds a visitor must grunt answers to:

1. **What do you offer?**  
2. **How will it make my life better?**  
3. **What do I do next?**

Apply to **every page and major component**. Fail any question → rewrite hierarchy/copy; do not add chrome.

### Target grunt answers (home / first paint)

| Question | Target grunt |
|----------|----------------|
| What? | College football rankings — this week’s board. |
| Better life? | I can join the fight with a clear take, not vibes. |
| Next? | Open the latest rankings / jump into the controversy. |

### Caveman simplicity

- If a non-stats fan cannot grunt it, rewrite.  
- Primary path language: **board, rankings, who they beat, how they look, league, take, climb, debate.**  
- Keep off primary path: Elo, TQ, CQ, FRS, AI_MODE, stub, MiniMax, “methodology” as the hero word.  
- Methodology / score breakdown = progressive disclosure for the nerd cave.

---

## Surface map (story jobs)

| Surface | Story job | 5-second must grunt | Demote / cut if… |
|---------|-----------|---------------------|------------------|
| **Home first paint** | Hero + problem + guide + primary CTA | Latest board; join the controversy; what to click | Feels like an admin dashboard or Elo lecture |
| **Week story** | External problem this week (conflict) | What shook; who climbed/fell | Report voice, stub/AI disclaimers |
| **Board (table)** | The plan in action — the product | Who’s where; find my team | Metrics before team identity |
| **Team detail** | Guide + success #1–2 | Why here; share take; who’s above | Formula-first; “Ask AI” as hero label |
| **Path to climb** | Plan for the hero’s team | Who to chase; one plain gap; one next step | Levers, deltas, TQ/CQ |
| **Explain / chat** | Guide empathy + clarity | Why this rank, in fan words | Mode/API/stub talk |
| **Methodology** | Success #3 only | How the board decides, then the math | Math as the only headline |

---

## Experience sequence (story order)

1. **Arrive** — Promise the fight: latest rankings + join the controversy. One primary CTA. Brand is guide, not hero headline spam.  
2. **Orient** — Week story = short conflict (“what changed”), not a data dump.  
3. **Engage** — Board is the product. Rank, team, record first.  
4. **Deepen** — Take (share) → path to climb → break it down → math (optional).  
5. **Succeed** — Share → argue → optionally understand formula.

---

## Build phases (execution order — no code until Phase 1 copy is approved)

### Phase 0 — Hold the line (done)

- Revert premature UI rewrite (PR #62).  
- Lock BrandScript + decisions in this doc.

### Phase 1 — Messaging only

Deliverables (copy deck, not pixels):

- Grunt-tested **home** headline, one supporting line, primary CTA, secondary CTA.  
- **Week story** voice rules (headline + 2–4 short paragraphs).  
- **Team take** / climb / empty / error / loading microcopy rules.  
- Terminology glossary (fan primary / technical secondary).  
- 5-second pass/fail checklist for QA.

**Exit:** explicit approval of the copy deck.

### Phase 2 — Structure (shape)

- Wireframes / IA only: first paint composition, board hierarchy, team detail story order.  
- Impeccable `/shape` against this BrandScript.  
- No visual rebrand until messaging hierarchy is fixed.

**Exit:** confirmed surface brief.

### Phase 3 — Visual world

- Impeccable new-work / DESIGN.md only after Phase 2.  
- Distinctiveness allowed; must not bury the grunt-test answers.

### Phase 4 — Implement

- Frontend + narrative stubs/static stories aligned to BrandScript.  
- Tests assert fan-visible copy never leaks internal AI/mode language.  
- Manual 5-second grunt test on home, team modal, methodology.

### Phase 5 — Polish

- `/clarify`, `/delight` only where StoryBrand moments earn it (share success, week controversy, climb plan).  
- No whimsy on errors.

---

## Anti-goals

- Do not ship another “SaaS rankings dashboard” voice.  
- Do not lead with algorithm flex on first paint.  
- Do not treat methodology as the product.  
- Do not implement visual redesign before Phase 1 copy approval.  
- Do not invent pricing/paywall UI in this track (aspirational “would pay for” stays outcome framing only).

---

## Open for Phase 1 copy (not blocking the frame)

These are **wording** choices to resolve in the copy deck, not reopeners of SB7:

- Exact primary CTA string (must encode: latest rankings + join conversation/controversy).  
- Exact home headline / one-liner.  
- Product name stay **CFB Rankings** vs stronger proper name (separate brand decision).

---

## Reference

- Donald Miller, *Building a StoryBrand* — SB7; customer = hero; brand = guide.  
- Grunt Test / 5-second tip — offer, better life, next action.  
- Caveman simplicity — no insider vocabulary on the primary path.  
- Existing product hooks already StoryBrand-shaped: path-to-climb blurbs in `shareable_blurb.py` (keep aligned; do not expand jargon).
