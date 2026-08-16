# TECH_STACK

**As of:** 2026-08-16
**Repo:** merimeesoftware/cfb-ranking-algorithm
**Evidence:** committed files on `main` only. Gaps marked unknown.

## Universal target

Cursor + MCP + skills → GitHub Actions → Cloudflare (Pages/Workers) when practical.

## Current stack

| Layer | Current | Evidence | Alignment |
|-------|---------|----------|-----------|
| Agent surface | Cursor Cloud Agent config (install/start/terminals for Flask + SvelteKit dev); Bugbot review guidelines | `.cursor/environment.json`, `.cursor/BUGBOT.md`, `.cursor/SECRETS.md` | partial |
| Source + CI | Python 3.11 Flask API + ranking scripts; SvelteKit/Vite/Tailwind static frontend; TypeScript Cloudflare Worker; GitHub Actions: `ci.yml` (flake8 + pytest + frontend check/build), `deploy-cloudflare.yml`, `precompute-rankings.yml`, `precompute-blurbs.yml`, `codeql.yml`, `automerge.yml`, `dependabot-automerge.yml` | `app.py`, `requirements.txt`, `frontend/package.json`, `worker/src/index.ts`, `.github/workflows/` | aligned |
| Runtime / deploy | Cloudflare Worker `true-rankings-cfb` (optional `cfb-rankings-dev` via `env.dev`): static assets from `frontend/build`, `/api/*` → Flask container (Dockerfile + gunicorn) via Durable Object `CFB_API`; deploy via `npm run deploy` / `wrangler deploy`; GitHub deploy gated on repo var `ENABLE_CLOUDFLARE_DEPLOY`; deprecated Render blueprint retained (`autoDeploy: false`) | `wrangler.toml`, `Dockerfile`, `package.json`, `.github/workflows/deploy-cloudflare.yml`, `render.yaml`, `docs/DEPLOY-CLOUDFLARE.md` | partial |
| Data / storage | Precomputed rankings JSON under `frontend/static/rankings/`; CFBD REST API at runtime; file cache in container (`CACHE_BACKEND=file`, `/tmp/cfb-cache`); optional R2 backend in code (`CACHE_BACKEND=r2`); precompute workflows upload artifacts (auto-commit disabled) | `frontend/static/rankings/`, `cache.py`, `worker/src/index.ts`, `.github/workflows/precompute-rankings.yml`, `.github/workflows/precompute-blurbs.yml` | partial |
| Cursor / MCP / skills | `.cursor/` agent config present; deploy-watch skill documented under `docs/skills/` (not in `.cursor/skills/`); MCP mentioned in design docs as future agent UX, not committed repo config | `.cursor/`, `docs/skills/cloudflare-deploy-watch/SKILL.md`, `docs/superpowers/specs/` | partial |

## Target vs current

- **Alignment:** partial
- **Gaps:** no committed MCP server config; skills live under `docs/skills/` rather than `.cursor/skills/`; Cloudflare deploy from GitHub Actions requires `ENABLE_CLOUDFLARE_DEPLOY=true` (repo variable, value unknown from commits); deprecated `render.yaml` still present; precompute workflows do not auto-commit static rankings to `main` (`if: false` commit step)
- **Cutover notes:** remove `render.yaml` after prod Worker confirmed; `ENABLE_CLOUDFLARE_DEPLOY` is a repo variable (do not change it in this PR)

## Notes

- Production runtime secrets belong in the Cloudflare Worker dashboard (`CFBD_API_KEY`, optional `MINIMAX_API_KEY` / `CACHE_CLEAR_SECRET`), not GitHub or `.cursor/environment.json` — see `docs/DEPLOY-CLOUDFLARE.md` and `.cursor/SECRETS.md`.
- Root `package.json` requires Node ≥22 and ships `wrangler` with `deploy` / `deploy:dev` scripts.
- CI uses Python 3.11 and Node 22; deploy workflow runs only after successful CI on `main`.
- Worker routes static SPA paths to `frontend/build` and proxies `/api/*` to the Flask container class `CfbApiContainer`.
