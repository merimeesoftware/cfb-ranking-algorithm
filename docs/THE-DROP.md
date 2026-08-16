# The Drop — weekly ritual & social cadence

**Product:** True Rankings  
**Ritual name:** The Drop  
**Target window:** Sunday 8:00pm ET *or* Monday 8:00am ET (pick one and never move it)  
**Channels (2026):** X + Bluesky first; Threads/IG as image-only  

## Hard rules

1. Same numbers, same time, for everyone — no early access for paying users.  
2. Rankings stay free in the email.  
3. CTA order in every post: cite/share → Get The Drop → model-vs-market (if a clear delta).  

## Weekly checklist

1. Confirm week JSON + story published under `frontend/static/rankings/{year}/week-{n}.*`  
2. Canonical URL: `https://truerankings.com/{year}/week/{n}`  
3. Generate share card (Top 25 + movers) — until automated, screenshot the week page OG title + board  
4. Post pack (copy templates below)  
5. Send The Drop email (Top 25, three movers, one CFP 1–12 mismatch, cite line)  
6. Optional: one podcast/newsletter ping with embed + “data via True Rankings”  

## Post templates

### A — Top 25 drop

```
True Rankings · {year} Week {n} is live.

How good they actually are — not a poll.

1. …
2. …
3. …
4. …
5. …

Full board (free): https://truerankings.com/{year}/week/{n}
Cite: True Rankings, {year} Week {n}, https://truerankings.com/{year}/week/{n}
```

### B — Biggest movers

```
Week {n} movers (TR+):

↑ {team} +{n} → #{rank}
↑ …
↓ {team} {n} → #{rank}

The Drop: https://truerankings.com/#the-drop
```

### C — CFP 1–12 mismatch

```
Perception vs TR+:

Into our CFP 1–12: {team}
Out of our CFP 1–12: {team}

Committee / AP can disagree. The model is the check.
https://truerankings.com/{year}/week/{n}
```

### D — Model vs market (only when delta ≥ 3 pts)

```
The market is buying the brand. TR+ is buying the team.

{favorite} TR+ -{x.x} vs market -{y.y} (Δ {z.z})

https://truerankings.com/games/{slug}
```

## Email (The Drop)

- Subject: `The Drop · Week {n} — {headline}`  
- Body: Top 25 table or list, three movers, one CFP band note, citation line, one sponsor slot max in-season  
- Footer: unsubscribe + 21+ / RG link if any affiliate present  

## Ops wiring

- Signup endpoint: `POST /api/drop/subscribe` `{ "email": "…" }`  
- Production: set `DROP_WEBHOOK_URL` in Cloudflare to your ESP  
- Dev: valid emails return `mode: accepted` without storing PII  
