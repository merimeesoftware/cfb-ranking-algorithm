# CFB Optimization Implementation Plan

See the attached plan at `/opt/cursor/artifacts/plans/cfb_full_optimization_ab2110ee.plan.md` for the full specification.

## Completed Workstreams

### Phase 0: SDLC Foundation
- CI hardening: pip-audit, npm audit, CodeQL, Dependabot, deploy-cloudflare.yml
- ~~OpenCode + gh-aw agentic workflows~~ — **removed from repo** (dev-only tooling; not used in production or active Actions). Re-add locally if needed; do not commit vendor skills.
- Impeccable frontend skill — **local/plugin only**; not committed (~3MB vendor tree).

### Phase 1: Audits
- `docs/superpowers/specs/2026-08-01-cfbd-api-audit.md`
- `docs/superpowers/specs/2026-08-01-frontend-audit.md`
- `docs/superpowers/specs/2026-08-01-data-memory-audit.md`
- `docs/superpowers/specs/2026-08-01-ops-cloudflare-runbook.md`
- `docs/superpowers/specs/2026-08-01-agentic-product-audit.md` (historical; OpenCode/gh-aw portions deferred)

### Phase 2: Implementation
- API/cache: week-scoped fetches, priors cache, `/weeks`, invalidate_prefix fix
- Frontend: consolidated API layer, same-origin `/api`, URL params, SWR cache
- Hybrid static rankings for archived weeks + slim list payloads
- Cloudflare: Dockerfile, wrangler.toml, Pages Git integration
- Tests: pytest suite, blocking in CI

### Phase 3: Agent Features (product, optional)
- `agent_service.py`: `/agent/explain`, `/agent/mcp/query`, `/agent/health` — requires `MINIMAX_API_KEY` in Cloudflare
- `AgentChatPanel.svelte` frontend component
- Not the same as OpenCode CI tooling

## Verification

```bash
./venv/bin/pytest tests/ -v
./venv/bin/flake8 . --select=E9,F63,F7,F82 --exclude=frontend,node_modules,venv,.venv
cd frontend && npm run check && npm run build
```
