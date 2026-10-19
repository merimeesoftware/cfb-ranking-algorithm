# True Rankings — Brand, Product & GTM Spec

| Field | Value |
|-------|-------|
| Date | 2026-08-16 |
| Status | Brand name, TR+, tagline, and routes still in force. The Drop, affiliates, and model-vs-market were removed (ADR 0001, 2026-10-18). |
| Brand | **True Rankings** |
| Rating | **TR+** (consumer name for Final Ranking Score / FRS) |
| Handle | **@TrueCFB** |
| Tagline | **How good they actually are.** |
| Primary domain (target) | `truerankings.com` (fallbacks: `truecfb.com`, `truerankings.football`) |
| Worker | `true-rankings-cfb` |

## Positioning

True Rankings is a ranking of how good teams **actually** are — not a poll, not a committee, not the narrative.

It sits away from AP / CFP (resume and voters). Differentiation: open methodology and a weekly board you can cite.

### Brand architecture

| Layer | Name | Use |
|-------|------|-----|
| Site / citations | True Rankings | “True Rankings has Ohio State at 4” |
| Rating number | TR+ | Table column, share cards, comparisons |
| Internal / methodology | FRS | Docs and deep math only |

### Non-goals

- Native iOS/Android app in 2026 (web + PWA only)
- Paywalling rankings, methodology, weekly JSON, or team pages
- Email signup, odds, spreads, picks, or sportsbook links

## Product surface (2026)

1. **Fans** — where is my team, and why?
2. **Media / AI** — cite this week’s order

Default land: current season / current week. The ranking **is** the homepage.

### Routes

| Route | Job |
|-------|-----|
| `/` | This week’s board |
| `/{year}/week/{week}` | Canonical crawlable week page |
| `/teams/{slug}` | Team page (share/search/AI) |
| `/games/{slug}` | Head-to-head of published TR+ ratings |
| `/methodology` | How it works |
| `/rankings/{year}/week-{n}.json` | Machine-readable rankings |
| `/llms.txt`, `/llms-full.txt` | AI crawler guidance |
| `/sitemap.xml`, `/robots.txt` | Search |

### CTA order

1. Share / cite
2. Read how it works

## Monetization

Nothing is sold on the board. Rankings, methodology, and weekly JSON stay free. Later ideas wait on usage (ADR 0001). There is no affiliate or newsletter path.

## Distribution

- **Search:** prerendered HTML, unique titles, JSON-LD, sitemap
- **Social:** Top 25 card and movers on X (@TrueCFB)
- **AI:** `llms.txt`, stable JSON, citation snippet on every page

## Custom domain

Attach `truerankings.com` (or fallback) to Worker `true-rankings-cfb` in Cloudflare → Custom Domains. Keep `PUBLIC_SITE_URL` / canonical meta aligned with the live hostname.

## Implementation checklist

Brand spine and citation routes are in the site. The Drop and lines were not shipped and are not to be added.
