# CFB Ranking System — Optimization Design Spec

Date: 2026-08-01

## Goal

Optimize the CFB Ranking System for performance, SDLC maturity, Cloudflare deployment, and optional product agent features (`/agent/explain` via MiniMax).

## Architecture

- **Hot path:** Direct CFBD REST API with multi-layer caching (memory, file, computed rankings, priors) + static JSON for archived weeks
- **Agent path (optional product):** MiniMax via `/agent/explain` — not on the ranking hot path; not OpenCode CI
- **Frontend:** SvelteKit static SPA on Cloudflare Pages
- **Backend:** Flask/gunicorn on Cloudflare Containers
- **CI/CD:** Real GitHub Actions only (`*.yml`) — ci-cd, CodeQL, Pages build validate, precompute

## Key Decisions

1. Keep REST for batch ranking; optional MCP only for agent queries
2. Hybrid Cloudflare migration: Pages first, then Containers
3. Do **not** commit vendor AI skills (Impeccable) or unused OpenCode/gh-aw sources — local/plugin only
4. Product MiniMax (`agent_service.py`) is independent of OpenCode tooling

## Repo hygiene (what ships)

| Commit | Do not commit |
|--------|----------------|
| App code, `frontend/`, tests, real `.github/workflows/*.yml` | `.cursor/skills/` (Impeccable etc.) |
| `docs/`, `AGENTS.md`, `.cursor/environment.json`, `.cursor/SECRETS.md` | `opencode.jsonc`, `.opencode/`, `.github/skills/` |
| Precomputed `frontend/static/rankings/**/*.json` | gh-aw `*.md` / `*.lock.yml` workflows |
| | Secrets, `venv/`, `.cache/`, `static_rankings/` |
