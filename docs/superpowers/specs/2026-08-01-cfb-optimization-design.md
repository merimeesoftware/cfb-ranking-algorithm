# CFB Ranking System — Optimization Design Spec

Date: 2026-08-01

## Goal

Optimize the CFB Ranking System for performance, SDLC maturity, Cloudflare deployment, and agentic workflows (OpenCode + MiniMax + CFBD MCP).

## Architecture

- **Hot path:** Direct CFBD REST API with multi-layer caching (memory, file/R2, computed rankings, priors)
- **Agent path:** CFBD MCP sidecar + MiniMax via `/agent/explain` (not on ranking hot path)
- **Frontend:** SvelteKit static SPA on Cloudflare Pages
- **Backend:** Flask/gunicorn on Cloudflare Containers (hybrid Render fallback during cutover)
- **CI/CD:** GitHub Actions + gh-aw agentic workflows + OpenCode local workflows

## Key Decisions

1. Keep REST for batch ranking; MCP for agent queries only
2. Hybrid Cloudflare migration: Pages first, then Containers
3. OpenCode for CI/dev tooling first; product agent chat in Phase 3
4. Retire Render after 1 week stable Cloudflare ops

## Deliverables

See individual audit specs in this directory and implementation plan at `docs/superpowers/plans/2026-08-01-cfb-optimization.md`.

## Audit Reports

- [CFBD API Audit](./2026-08-01-cfbd-api-audit.md)
- [Frontend Audit](./2026-08-01-frontend-audit.md)
- [Data/Memory Audit](./2026-08-01-data-memory-audit.md)
- [Ops/Cloudflare Runbook](./2026-08-01-ops-cloudflare-runbook.md)
- [Agentic Product Audit](./2026-08-01-agentic-product-audit.md)
