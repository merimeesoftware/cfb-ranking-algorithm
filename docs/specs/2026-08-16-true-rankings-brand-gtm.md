# True Rankings — Brand, Product & GTM Spec

| Field | Value |
|-------|-------|
| Date | 2026-08-16 |
| Status | Approved for implementation |
| Brand | **True Rankings** |
| Rating | **TR+** (consumer name for Final Ranking Score / FRS) |
| Handle | **@TrueCFB** |
| Tagline | **How good they actually are.** |
| Primary domain (target) | `truerankings.com` (fallbacks: `truecfb.com`, `truerankings.football`) |
| Worker | `true-rankings-cfb` |

## Positioning

True Rankings is a predictive model of how good teams **actually** are — not a poll, not a committee, not the narrative. Perception creates “upsets”; the model is the order you check before you argue or bet.

Sits next to SP+ / FPI (predictive power ratings), away from AP / CFP (resume and voters). Differentiation: open methodology, weekly explainability, and model-vs-market lines on the same page.

### Brand architecture

| Layer | Name | Use |
|-------|------|-----|
| Site / citations | True Rankings | “True Rankings has Ohio State at 4” |
| Rating number | TR+ | Table column, share cards, matchup math |
| Weekly ritual | The Drop | Sunday/Monday release + email |
| Internal / methodology | FRS, Lean Pure | Docs and deep math only |

### Non-goals

- Native iOS/Android app in 2026 (web + PWA only)
- Paywalling rankings, methodology, weekly JSON, or team pages
- Selling “picks” as the brand — sell **disagreement with the market**

## Product surface (2026)

1. **Fans** — where is my team, and why?
2. **Media / AI** — cite this week’s order
3. **Bettors** — where does TR+ disagree with the market?

Default land: current season / current week. The ranking **is** the homepage.

### Routes

| Route | Job |
|-------|-----|
| `/` | This week’s board + Drop CTAs |
| `/{year}/week/{week}` | Canonical crawlable week page |
| `/teams/{slug}` | Team page (share/search/AI) |
| `/games/{slug}` | Matchup: TR+ vs market |
| `/methodology` | How it works |
| `/rankings/{year}/week-{n}.json` | Machine-readable rankings |
| `/llms.txt`, `/llms-full.txt` | AI crawler guidance |
| `/sitemap.xml`, `/robots.txt` | Search |

### CTA order (never invert)

1. Share / cite (growth)
2. Email The Drop (owned audience)
3. Open a book on *this* number (revenue)
4. Membership extras later — **not** the list

## Monetization (rankings stay free)

| Layer | Sell | Free |
|-------|------|------|
| Affiliates | Geo-gated click-out on model-vs-market | Ranking + implied number |
| Newsletter | One sponsor slot in The Drop | Same ranking in the email |
| Membership (later) | Alerts, unlimited why, what-if | List, methodology, JSON |
| B2B (later) | Embed + commercial API SLA | Fan HTML + public JSON |

Compliance when lines are shown: 21+ (18+ where required), state geo, affiliate disclosure, responsible-gambling links, “not affiliated with NCAA/CFP”.

## Distribution

- **Search:** prerendered HTML, unique titles, JSON-LD, sitemap
- **Social:** The Drop ritual — Top 25 card, movers, CFP-12 mismatch
- **AI:** `llms.txt`, stable JSON, citation snippet on every page

## Custom domain

Attach `truerankings.com` (or fallback) to Worker `true-rankings-cfb` in Cloudflare → Custom Domains. Keep `PUBLIC_SITE_URL` / canonical meta aligned with the live hostname.

## Implementation checklist

See plan todos: brand spine → citation routes → Drop ritual → lines/affiliates.
