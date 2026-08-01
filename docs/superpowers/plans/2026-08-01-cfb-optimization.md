# CFB Optimization Implementation Plan

See the attached plan at `/opt/cursor/artifacts/plans/cfb_full_optimization_ab2110ee.plan.md` for the full specification.

## Completed Workstreams

### Phase 0: SDLC Foundation
- OpenCode + Minimax: `opencode.jsonc`, `.opencode/workflows/`
- gh-aw agentic workflows: `.github/workflows/*.md`
- CI hardening: pip-audit, npm audit, CodeQL, Dependabot, deploy-cloudflare.yml

### Phase 1: Audits
- `docs/superpowers/specs/2026-08-01-cfbd-api-audit.md`
- `docs/superpowers/specs/2026-08-01-frontend-audit.md`
- `docs/superpowers/specs/2026-08-01-data-memory-audit.md`
- `docs/superpowers/specs/2026-08-01-ops-cloudflare-runbook.md`
- `docs/superpowers/specs/2026-08-01-agentic-product-audit.md`

### Phase 2: Implementation
- API/cache: week-scoped fetches, priors cache, `/weeks`, invalidate_prefix fix
- Frontend: consolidated API layer, VITE_API_URL, URL params, SWR cache
- Cloudflare: Dockerfile, wrangler.toml, Pages config, deploy workflow
- Tests: 11 pytest tests, blocking in CI

### Phase 3: Agent Features
- `agent_service.py`: `/agent/explain`, `/agent/mcp/query`, `/agent/health`
- `AgentChatPanel.svelte` frontend component

## Verification

```bash
./venv/bin/pytest tests/ -v
./venv/bin/flake8 . --select=E9,F63,F7,F82 --exclude=frontend,node_modules,venv,.venv
cd frontend && npm run check && npm run build
```
