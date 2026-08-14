# CFB Rankings — Phase 1 Copy Deck (grunt-tested)

**Status:** Approved for implementation (build brief).  
**Product name:** CFB Rankings (rename deferred).  
**Rules:** Caveman primary path. Grunt Test on every surface. Success order: share take → win argument → understand formula.

---

## Glossary

| Fan (primary UI) | Technical (methodology / disclosure only) |
|------------------|---------------------------------------------|
| the board / rankings | model, algorithm, FRS |
| how they look | Team Quality, Elo |
| who they beat | Resume, SoV, SoS |
| league strength | Conference Quality, CQ |
| take | blurb |
| climb / path to climb | primary_lever, delta, contrib |
| Break it down / Why here? | Ask AI |
| How it works | Methodology |

**Never in fan-visible copy:** `AI_MODE`, stub, MiniMax, TQ, CQ, Elo (unless inside methodology deep dive).

---

## Home / first paint

| Element | Copy |
|---------|------|
| Brand | CFB Rankings |
| Headline | Who belongs higher? |
| Supporting line | This week’s board — clear takes for the fight, not voter vibes. |
| Primary CTA | See this week’s rankings |
| Primary CTA subtext (optional) | Jump into the controversy |
| Secondary CTA | How the board works |
| Board tab | The Board |
| Conferences tab | Conferences |
| Loading | Building the board… |
| Error title | Couldn’t load this week’s rankings. |
| Error action | Reload board |

**5-second grunt:** Rankings board · join the fight with a clear take · click See this week’s rankings / scan the board.

---

## Filters

| Element | Copy |
|---------|------|
| Views | National · Group of 5 · Power 4 · FCS |
| Season | Season |
| Week | Week |
| Refresh | Refresh board |
| Search label | Find your team |
| Search placeholder | Ohio State, SEC, Boise… |
| Conference | Conference / All conferences |

---

## Nav / footer

| Element | Copy |
|---------|------|
| Nav home | The Board |
| Nav methodology | How it works |
| Footer data | Game data from College Football Data. The board is ours. |
| Footer GitHub | GitHub (real repo URL) |
| Disclaimer | © {year} CFB Rankings. Not affiliated with the NCAA or College Football Playoff. |

---

## Week story

- Headline: conflict-first (`Team jumps N spots — Leader still owns #1`).
- Body: risers, heat, playoff-band shakeup, top 5 + debate hook.
- No stub/AI disclaimers.

---

## Team detail (story order)

1. Take (shareable) → **Copy take** / **Share link**  
2. Path to climb  
3. **Why here?** (break down)  
4. Why this spot (plain labels: how they look / who they beat / league strength)  
5. Key games / math disclosure  

| Element | Copy |
|---------|------|
| Why CTA | Why here? |
| Share link | Share link / Link copied |
| Take meta | {n}/280 · ready to post |
| Copy take | Copy take / Take copied |
| Breakdown heading | Why this spot |
| TQ label | How good they look |
| Resume label | Who they beat |
| CQ label | League strength |
| Total | Board score |
| Path heading | Path to climb |
| Empty QW | No quality wins on the ledger yet. |
| Empty bad losses | Clean sheet — no bad losses. |
| Loading details | Pulling game details… |

---

## Explain / chat

| Element | Copy |
|---------|------|
| Title | Why {team}? |
| Label | Ask anything (optional) |
| Placeholder | Why is {team} here — and who should be mad? |
| Submit | Break it down / Breaking it down… |
| Error | Couldn’t break down this ranking right now. |

---

## Methodology

| Element | Copy |
|---------|------|
| Title | How the board works |
| Intro | Meathead version: who they beat + how they look + the league they live in. Nerdy version below — every weight, bonus, and floor. |
| Formula heading | The mix |
| Formula line | Board score = (0.65 × how they look) + (0.27 × who they beat) + (0.08 × league strength) |
| Cards | How they look (65%) · Who they beat (27%) · League strength (8%) |
| Expand | Open the math / Show less |
| Back | Back to the board |

---

## QA — 5-second checklist

- [ ] Home: offer / better life / next action grunt-able  
- [ ] Week story: what shook this week  
- [ ] Team modal: why here + share take before formula  
- [ ] Methodology: how board decides before math  
- [ ] No AI_MODE / MiniMax / TQ / CQ on primary path  
