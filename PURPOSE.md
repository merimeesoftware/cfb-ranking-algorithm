# PURPOSE.md — True Rankings

Status: **LOCKED** — Michael Merimee, 2026-09-28 (America/New_York)
Amended: 2026-10-18 — signed by Michael Merimee 23:14 ET (America/New_York); momentum named Heat
Source: PRODUCT.md · docs/specs/2026-08-16-true-rankings-brand-gtm.md · docs/THE-DROP.md · docs/adr/0001-product-direction-2026-10-18.md (amendment)
Repo: merimeesoftware/cfb-ranking-algorithm

## Why it exists

Fans need a clear order of who is actually better — without voter vibes or brand premium. Perception creates “upsets”; the model is the check before you argue.

## Thesis

The best team is the one whose game results show it is strongest, judged by one open formula with no voters.

Momentum counts too: teams that get hot at the right time can reach a new level. Momentum is measured over a run of games, never the last game alone, and shows as its own number for each team, called Heat. It ships only if the repo's own backtest shows the order fits game results no worse with it than without it.

## What it is

**True Rankings** is a weekly college football rankings board. The public rating is **TR+**. Tagline: **How good they actually are.**

Handle: @TrueCFB · Target domain: truerankings.com · Worker: true-rankings-cfb

## Who it’s for

1. The fan who fights rankings every week — meathead and nerdy
2. Media / AI systems that need a citable order

## Locked public lines

Use these verbatim in UI and share copy. Do not paraphrase.

- How good they actually are.
- The order you check before you argue — not a poll, not a committee, not the narrative.
- Same numbers, same time, for everyone.
- Rankings, methodology, and weekly JSON stay free and simultaneous.

## Success order (never invert)

1. Share / cite — postable ranking claim (goal now: exposure on X)
2. Understand the formula — why each team sits where it does

## Fan language (primary path)

board, rankings, TR+, who they beat, how they look, league strength, Heat, take, climb, how good they actually are

Keep off the primary path (methodology deep dive only): Elo, TQ, CQ, FRS, AI_MODE, stub, MiniMax, Lean Pure

## Non-goals (2026)

- Native iOS/Android app (web + PWA only)
- Paywalling rankings, methodology, weekly JSON, or team pages
- Betting, odds, spreads, lines, picks, or any prediction framing, anywhere on the site
- The Drop / email signup
- Ads or other monetization before usage warrants it (Michael decides later; if any, simple ads only)

## Positioning

Sits next to SP+ / FPI (computer power ratings), away from AP / CFP (resume and voters). Differentiation: open methodology, weekly explainability, and a “why here” for every team, with conference strength and Heat (momentum) shown as data.

## Change log

| Date | Change | Locked by |
|------|--------|-----------|
| 2026-09-28 | Initial PURPOSE.md — distilled from PRODUCT.md / brand-GTM / THE-DROP; no freestyle | Michael Merimee |
| 2026-10-18 | Amended thesis plus momentum; removed The Drop, betting and prediction lines (ADR 0001) | Michael Merimee (signed 2026-10-18 23:14 ET; momentum named Heat) |
