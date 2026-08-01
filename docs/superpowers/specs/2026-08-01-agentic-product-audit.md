# Agentic Product Integration Architecture

**CFB Ranking System — Product Audit & Integration Spec**

| Field | Value |
|-------|-------|
| Date | 2026-08-01 |
| Status | Draft |
| Scope | OpenCode/Minimax CI, CFBD MCP sidecar, ranking explainer API, frontend chat, auth/rate limits, rollout |

---

## Executive Summary

The CFB Ranking System today has three entry points (Flask API, SvelteKit frontend, CLI) and an emerging **agentic dev layer** (OpenCode + MiniMax + gh-aw). This spec defines how to extend that foundation into a **product-facing agent experience** without compromising the ranking hot path.

**Core principle:** Rankings computation stays synchronous, cached, and REST-first. Agent capabilities run on a **sidecar path** that reads precomputed rankings and optionally enriches answers via CFBD MCP — never blocking or replacing `GET /rankings`.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         HOT PATH (unchanged)                            │
│  Browser/CLI ──► GET /rankings ──► cache ──► TeamQualityRanker (V5.1)  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                      AGENT PATH (new, async-capable)                    │
│  Chat UI ──► POST /agent/explain ──► Explainer orchestrator             │
│                    │                                                    │
│                    ├──► GET /rankings (cached, read-only)               │
│                    ├──► GET /rankings/team/:name (structured factors) │
│                    └──► CFBD MCP sidecar (optional enrichment)          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 1. OpenCode + MiniMax Integration (CI / Dev)

### 1.1 Current State

The repo already ships:

| Asset | Purpose |
|-------|---------|
| `opencode.jsonc` | OpenCode config: `minimax/MiniMax-M2.7`, Anthropic-compatible base URL, MCP/bash/edit permissions |
| `.opencode/workflows/*.ts` | Local agent workflows (`ranking-qa`, `cfbd-audit`, `frontend-audit`, `deploy-smoke`) |
| `.github/workflows/*.md` | gh-aw source workflows compiled to `.lock.yml` |
| `.github/skills/agentic-workflows/SKILL.md` | Dispatcher conventions for authoring gh-aw workflows |

**Model routing:**

```jsonc
// opencode.jsonc (existing)
{
  "model": "minimax/MiniMax-M2.7",
  "provider": {
    "minimax": {
      "options": {
        "apiKey": "{env:MINIMAX_API_KEY}",
        "baseURL": "https://api.minimax.io/anthropic"
      }
    }
  }
}
```

**Required secrets:** `MINIMAX_API_KEY`, `CFBD_API_KEY`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`

### 1.2 Architecture: Two-Tier Agent Execution

```
                    ┌──────────────────────┐
                    │   Developer laptop   │
                    │  opencode run --wf   │
                    └──────────┬───────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
  .opencode/workflows/   opencode.jsonc      Local Flask :5001
  (TypeScript DSL)       (MiniMax provider)   + CFBD_API_KEY

                    ┌──────────────────────┐
                    │   GitHub Actions     │
                    │   gh aw compile/run  │
                    └──────────┬───────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
  .github/workflows/*.md   opencode-engine.md    Deployed API_URL
  (YAML frontmatter)       (sst/opencode import)  (optional)
```

**Tier 1 — Local dev (`.opencode/workflows/`):** Fast iteration, full shell access, direct API calls. Used for ranking QA, CFBD audits, frontend quality checks, deploy smoke tests.

**Tier 2 — CI (gh-aw `.github/workflows/*.md`):** Scheduled and PR-triggered agent jobs with constrained network (`api.minimax.io`, `api.collegefootballdata.com`) and read-only repo permissions by default.

### 1.3 gh-aw Workflow Conventions

All gh-aw sources follow this frontmatter contract (from existing `ranking-regression.md`):

```yaml
---
on:
  pull_request:
    types: [opened, synchronize, reopened]
  schedule:
    - cron: "0 16 * * 1"
engine: opencode
imports:
  - sst/opencode/.github/workflows/opencode-engine.md@v1.2.14
network:
  allowed:
    - defaults
    - api.minimax.io
    - api.collegefootballdata.com
permissions:
  contents: read
  pull-requests: write
---
```

**Compile-before-commit rule:** Run `gh aw compile` locally; commit both `.md` source and generated `.lock.yml`.

### 1.4 Existing Workflow Inventory

| Workflow | Location | Trigger | Role |
|----------|----------|---------|------|
| `ranking-qa` | `.opencode/workflows/ranking-qa.ts` | Manual / CI mirror | Schema validation, top-10 stability |
| `cfbd-audit` | `.opencode/workflows/cfbd-audit.ts` | Manual | Cache/API call analysis, MCP evaluation |
| `frontend-audit` | `.opencode/workflows/frontend-audit.ts` | Manual | svelte-check, API layer audit, UX review |
| `deploy-smoke` | `.opencode/workflows/deploy-smoke.ts` | Post-deploy | Health + rankings + cache stats |
| `ranking-regression` | `.github/workflows/ranking-regression.md` | PR + weekly cron | CI regression gate with PR comment |
| `daily-repo-status` | `.github/workflows/daily-repo-status.md` | Daily cron | Issue/PR/CI summary |
| `cache-warm` | `.github/workflows/cache-warm.md` | Saturday cron | Pre-warm rankings cache |

### 1.5 Recommended CI/Dev Extensions

Add these workflows in Phase 1 (see §7):

| New workflow | Type | Purpose |
|--------------|------|---------|
| `agent-explain-qa` | `.opencode/workflows/agent-explain-qa.ts` | Golden-set tests for `POST /agent/explain` |
| `mcp-sidecar-health` | `.github/workflows/mcp-sidecar-health.md` | Verify CFBD MCP sidecar responds; no hot-path coupling |
| `explain-regression` | `.github/workflows/explain-regression.md` | PR comment with sample explain responses |

**Local dev command reference:**

```bash
# Start backend (required for ranking workflows)
CFBD_API_KEY=... ./venv/bin/python app.py

# Run OpenCode workflows
opencode run --workflow ranking-qa --year 2024 --week 10
opencode run --workflow cfbd-audit
opencode run --workflow frontend-audit
opencode run --workflow deploy-smoke --api_url http://localhost:5001

# Compile gh-aw sources
gh aw compile
```

---

## 2. CFBD MCP Sidecar Architecture

### 2.1 Design Constraint: Not Hot Path

The ranking pipeline (`data_processor.py` → `TeamQualityRanker`) must **continue using direct CFBD REST** via `CFBDataProcessor`. Reasons:

- Batch season fetches (~8 CFBD calls on cache miss) are optimized for throughput, not MCP tool granularity.
- MCP adds process hop latency unsuitable for first `/rankings` request (30–120s cold start).
- Existing file + memory cache (`cache.py`, TTL_RANKINGS=30min) assumes deterministic REST keys.

**MCP is for agent enrichment only:** game narratives, injury/roster context, schedule lookups, historical head-to-head — data not already in rankings JSON.

### 2.2 Sidecar Topology

```
┌─────────────────────────────────────────────────────────────────┐
│ Flask API (app.py) — port 5001                                  │
│                                                                 │
│  GET /rankings          ──► HOT PATH (REST → cache → ranker)   │
│  GET /rankings/team/:n  ──► HOT PATH (reuses cached rankings)  │
│  POST /agent/explain    ──► AGENT PATH (orchestrator)          │
└───────────────────────────────┬─────────────────────────────────┘
                                │ HTTP (localhost only)
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ CFBD MCP Sidecar — port 5100 (separate process/container)       │
│                                                                 │
│  Transport: stdio MCP wrapped by mcp-proxy OR native HTTP MCP   │
│  Server candidates:                                             │
│    • lenwood/cfbd-mcp-server (games, teams, rankings metadata)  │
│    • gedin-eth/cfb-mcp (broader CFB context)                    │
│                                                                 │
│  Env: CFBD_API_KEY (same key, separate rate-limit bucket)       │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
                    api.collegefootballdata.com
```

### 2.3 Sidecar Deployment Options

| Environment | Pattern |
|-------------|---------|
| Local dev | `docker compose up cfbd-mcp` or `npx @modelcontextprotocol/server-*` in tmux session `:5100` |
| Render (API host) | Second web service or background worker; internal URL `http://cfbd-mcp:5100` |
| Cloudflare Workers | **Not recommended** for MCP sidecar — use Render/Fly sidecar; Workers host frontend only |

### 2.4 MCP Tool Allowlist (Agent Path Only)

The explainer orchestrator may call only these MCP tools:

| Tool category | Example tools | Use case |
|---------------|---------------|----------|
| Games | `get_games`, `get_game_team_stats` | Recent results, MOV context |
| Teams | `get_team_records`, `get_roster` | Record verification, narrative |
| Calendar | `get_calendar` | Week boundaries, bye weeks |
| **Blocked** | `get_rankings` (polls), bulk season export | Duplicates hot-path REST; high cost |

### 2.5 Fallback Strategy

```
POST /agent/explain
    │
    ├─► Step 1: Always fetch structured data from Flask (cached rankings + team breakdown)
    │
    ├─► Step 2: If MCP sidecar healthy → enrich with 1–3 targeted tool calls
    │           Else → return explanation from structured data only (degraded mode)
    │
    └─► Step 3: LLM synthesis (MiniMax) with citations to structured factors
```

**Health check:** `GET /agent/health` returns `{ "mcp_sidecar": "up"|"down", "rankings_cache": "warm"|"cold" }`.

### 2.6 Rate-Limit Isolation

Maintain separate CFBD quota tracking:

- **Hot path bucket:** Existing cache-first REST (unchanged).
- **Agent bucket:** Max 10 MCP tool calls per explain request; max 100/hour per API key globally for sidecar.

---

## 3. Ranking Explainer API — `POST /agent/explain`

### 3.1 Endpoint Contract

```
POST /agent/explain
Content-Type: application/json
Authorization: Bearer <token>   (Phase 2+)
X-Request-Id: <uuid>            (optional, for tracing)
```

### 3.2 Request Schema

```json
{
  "intent": "rank_explanation | compare_teams | week_over_week",
  "params": {
    "year": 2024,
    "week": 10,
    "team": "Ohio State",
    "rank": 3,
    "teams": ["Ohio State", "Oregon"],
    "compare_with": "Texas",
    "prior_week": 9
  },
  "context": {
    "locale": "en-US",
    "verbosity": "concise | detailed",
    "include_mcp_enrichment": true
  },
  "conversation_id": "uuid-or-null"
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `intent` | Yes | Routes to workflow handler (§5) |
| `params.year` | Yes | Season year |
| `params.week` | Conditional | Required except postseason "all" |
| `params.team` | For rank_explanation | Canonical team name (case-insensitive match) |
| `params.teams` | For compare_teams | 2–4 team names |
| `params.prior_week` | For week_over_week | Defaults to `week - 1` |

### 3.3 Response Schema

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "intent": "rank_explanation",
  "answer": {
    "summary": "Ohio State is ranked #3 primarily due to...",
    "markdown": "## Why Ohio State is #3\n\n...",
    "confidence": "high | medium | low"
  },
  "structured": {
    "team": {
      "name": "Ohio State",
      "rank": 3,
      "final_score": 1842.5,
      "formula_breakdown": {
        "tq_contribution": 1197.6,
        "rec_contribution": 412.3,
        "cq_contribution": 98.1
      }
    },
    "comparisons_ahead": [],
    "comparisons_behind": [],
    "rank_delta": null
  },
  "citations": [
    { "source": "rankings", "endpoint": "/rankings/team/Ohio State", "year": 2024, "week": 10 },
    { "source": "methodology", "section": "V5.1 weights (65/27/8)" }
  ],
  "mcp_enrichment": {
    "used": true,
    "tools_called": ["get_games"],
    "latency_ms": 340
  },
  "meta": {
    "model": "minimax/MiniMax-M2.7",
    "latency_ms": 2100,
    "cached_rankings": true,
    "degraded_mode": false
  }
}
```

### 3.4 Server Architecture

New module: `agent/explainer.py`

```
agent/
├── __init__.py
├── explainer.py          # Orchestrator entry point
├── intents/
│   ├── rank_explanation.py
│   ├── compare_teams.py
│   └── week_over_week.py
├── mcp_client.py         # Sidecar HTTP/stdio bridge
├── prompts/
│   └── system.md         # Grounded explanation system prompt
└── schemas.py            # Pydantic request/response models
```

**Orchestration flow:**

1. **Validate** request (Pydantic); resolve team name aliases via `data_processor.team_info_map`.
2. **Fetch structured data** — call internal functions (not HTTP loopback in-process):
   - `calculate_rankings_logic()` or cache read for `year`/`week`
   - Reuse `build_comparison()` logic from `GET /rankings/team/<team_name>` (extract to shared `ranking_breakdown.py`)
3. **Optional MCP enrichment** — 1–3 tool calls based on intent.
4. **LLM synthesis** — MiniMax via Anthropic-compatible API; system prompt requires citing `structured` fields only (no hallucinated scores).
5. **Return** combined JSON; log `request_id` + token usage.

### 3.5 Extraction Refactor (Prerequisite)

Move comparison logic from `app.py` `get_team_breakdown()` into:

```python
# ranking_breakdown.py
def get_team_breakdown(rankings_data: dict, team_name: str) -> dict: ...
def compare_teams(rankings_data: dict, team_names: list[str]) -> dict: ...
def week_over_week_delta(year: int, week: int, team_name: str, ...) -> dict: ...
```

Both `GET /rankings/team/:name` and `POST /agent/explain` call these functions — single source of truth.

### 3.6 LLM Guardrails

| Rule | Implementation |
|------|----------------|
| Grounding | System prompt: "Only cite numbers present in `structured` JSON" |
| Refusal | If team not found → 404 with suggested fuzzy matches |
| Timeout | 30s total; LLM call capped at 20s |
| Token budget | Max 4K input, 1K output per request |
| No re-ranking | Agent must never recompute or adjust scores |

### 3.7 Additional Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/agent/health` | GET | Sidecar + cache status |
| `/agent/intents` | GET | List supported intents and param schemas (OpenAPI discovery) |

---

## 4. Frontend Chat Panel Architecture

### 4.1 UX Placement

Add a collapsible **"Ask about rankings"** panel to the main rankings page (`frontend/src/routes/+page.svelte`), not a separate route initially.

```
┌────────────────────────────────────────────────────────────┐
│ Header + FilterControls (year/week)                        │
├──────────────────────────────────┬─────────────────────────┤
│ RankingsTable                    │ AgentChatPanel (drawer) │
│ (existing)                       │ ┌─────────────────────┐ │
│                                  │ │ Suggested prompts   │ │
│                                  │ ├─────────────────────┤ │
│                                  │ │ Message thread      │ │
│                                  │ ├─────────────────────┤ │
│                                  │ │ Input + Send        │ │
│                                  │ └─────────────────────┘ │
└──────────────────────────────────┴─────────────────────────┘
         ▲ mobile: bottom sheet overlay
```

### 4.2 Component Tree

```
frontend/src/lib/
├── components/
│   └── agent/
│       ├── AgentChatPanel.svelte      # Shell: open/close, responsive layout
│       ├── AgentMessageList.svelte    # Renders user + assistant messages
│       ├── AgentMessage.svelte        # Single bubble; markdown rendering
│       ├── AgentInput.svelte          # Text input + submit
│       ├── AgentSuggestedPrompts.svelte
│       └── AgentStructuredCard.svelte # Inline formula breakdown / comparison table
├── stores/
│   └── agentChat.ts                   # Writable store: messages, loading, error
└── api/
    └── agent.ts                       # postExplain(), parseIntent from NL (Phase 3)
```

### 4.3 State Model

```typescript
// frontend/src/lib/stores/agentChat.ts
interface AgentMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;           // markdown
  structured?: TeamBreakdown | ComparisonResult | WeekDelta;
  citations?: Citation[];
  timestamp: string;
}

interface AgentChatState {
  isOpen: boolean;
  messages: AgentMessage[];
  isLoading: boolean;
  error: string | null;
  conversationId: string | null;
}
```

**Context injection:** When user opens chat from `TeamDetailModal`, pre-fill:

```typescript
agentChat.openWithContext({
  intent: 'rank_explanation',
  params: { team: selectedTeam.team_name, rank: selectedRank, year, week }
});
```

### 4.4 API Client

```typescript
// frontend/src/lib/api/agent.ts
const AGENT_BASE = import.meta.env.DEV
  ? 'http://localhost:5001'
  : (import.meta.env.VITE_API_URL || 'https://cfb-rankings-api.onrender.com');

export async function postExplain(body: ExplainRequest): Promise<ExplainResponse> {
  const response = await fetch(`${AGENT_BASE}/agent/explain`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(import.meta.env.VITE_AGENT_TOKEN && {
        Authorization: `Bearer ${import.meta.env.VITE_AGENT_TOKEN}`
      })
    },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(35000)
  });
  // ...
}
```

### 4.5 Rendering Strategy

| Response field | UI treatment |
|----------------|--------------|
| `answer.markdown` | Render via `marked` or lightweight markdown component |
| `structured.formula_breakdown` | Reuse score bar visuals from `TeamDetailModal.svelte` |
| `structured.comparisons_*` | Compact comparison cards (same diff coloring logic) |
| `citations` | Footnote links to `/methodology` + "View team breakdown" |
| `meta.degraded_mode` | Banner: "Live game data unavailable; explanation based on rankings only" |

### 4.6 Natural Language → Intent (Phase 3)

Initial Phase 1 uses **explicit intents** via suggested prompts (§5). Phase 3 adds lightweight intent classification:

```
User: "Why is Oregon #2?"
  → intent: rank_explanation, params: { team: "Oregon", rank: 2 }

User: "Compare Ohio State and Texas"
  → intent: compare_teams, params: { teams: ["Ohio State", "Texas"] }
```

Options: client-side regex/heuristics first; server-side MiniMax classifier if needed.

### 4.7 Accessibility & Performance

- Panel toggle: keyboard shortcut `?` (with `aria-expanded`)
- Focus trap when open on mobile
- Lazy-load agent components: `import('./AgentChatPanel.svelte')` on first open
- Stream responses (Phase 4): SSE `GET /agent/explain/stream` for token streaming

---

## 5. Workflow Definitions

### 5.1 Intent: "Why is Team X ranked #Y?"

**Intent key:** `rank_explanation`

**Trigger examples:**
- Suggested prompt: "Why is {team} ranked #{rank}?"
- Team modal action: "Explain this ranking"
- OpenCode product workflow (local QA)

**Data pipeline:**

```
1. GET /rankings?year=&week=          → locate team at rank Y (verify rank matches)
2. get_team_breakdown(team)           → formula + comparisons_ahead/behind
3. MCP (optional): get_games(team, last 3) → recent game context
4. LLM: synthesize narrative from structured factors
```

**OpenCode workflow definition** (`.opencode/workflows/explain-rank.ts`):

```typescript
export default workflow({
  name: "explain-rank",
  description: "Golden-path test for rank explanation intent",
  args: {
    team: { type: "string", default: "Ohio State" },
    rank: { type: "number", default: 3 },
    year: { type: "number", default: 2024 },
    week: { type: "number", default: 10 },
    api_url: { type: "string", default: "http://localhost:5001" },
  },
  async run(ctx) {
    const { team, rank, year, week, api_url } = ctx.args;
    await ctx.agent({
      name: "explain-rank",
      prompt: `POST ${api_url}/agent/explain with body:
{
  "intent": "rank_explanation",
  "params": { "year": ${year}, "week": ${week}, "team": "${team}", "rank": ${rank} },
  "context": { "verbosity": "detailed" }
}
Validate:
1. Response mentions team name and rank
2. structured.formula_breakdown totals match structured.team.final_score (±1)
3. answer cites TQ/Record/CQ contributions
4. No hallucinated teams in top 5 comparisons
Return pass/fail with excerpt.`,
    });
  },
});
```

**Acceptance criteria:**
- Names all three score components with correct weights (65/27/8)
- Identifies primary factor vs teams ranked immediately above/below
- Response time < 5s when rankings cached

---

### 5.2 Intent: "Compare teams"

**Intent key:** `compare_teams`

**Trigger examples:**
- "Compare Ohio State vs Oregon"
- Multi-select from rankings table → "Compare selected"

**Data pipeline:**

```
1. GET /rankings?year=&week=
2. For each team: extract rank, final_score, TQ, record_score, CQ, SOS, SoV
3. compare_teams([A, B, ...])  → pairwise factor diffs
4. MCP (optional): get_games head-to-head if played this season
5. LLM: side-by-side narrative with winner per category
```

**Request example:**

```json
{
  "intent": "compare_teams",
  "params": {
    "year": 2024,
    "week": 10,
    "teams": ["Ohio State", "Oregon"]
  },
  "context": { "verbosity": "detailed" }
}
```

**Structured output extension:**

```json
{
  "structured": {
    "teams": [
      { "name": "Ohio State", "rank": 3, "final_score": 1842.5, ... },
      { "name": "Oregon", "rank": 2, "final_score": 1856.1, ... }
    ],
    "pairwise": [
      {
        "team_a": "Oregon",
        "team_b": "Ohio State",
        "rank_diff": -1,
        "score_diff": 13.6,
        "deciding_factors": [
          { "factor": "Team Quality (Elo)", "advantage": "Oregon", "contribution": 8.2 }
        ]
      }
    ],
    "head_to_head": { "played": true, "result": "Oregon 35, Ohio State 28", "week": 7 }
  }
}
```

**OpenCode workflow** (`.opencode/workflows/explain-compare.ts`):

```typescript
await ctx.agent({
  name: "compare-teams",
  prompt: `POST /agent/explain with intent compare_teams for ["Ohio State", "Oregon"].
Verify pairwise deciding_factors present, rank order consistent with score_diff sign.`,
});
```

---

### 5.3 Intent: "Week-over-week changes"

**Intent key:** `week_over_week`

**Trigger examples:**
- "What changed for Georgia from week 9 to 10?"
- "Biggest movers this week"

**Data pipeline:**

```
1. GET /rankings?year=&week=N        → current snapshot
2. GET /rankings?year=&week=N-1      → prior snapshot (cache likely warm)
3. week_over_week_delta(team)        → rank_delta, score_delta, component deltas
4. Identify driver: TQ change (game result) vs field movement
5. MCP (optional): get_games(team, week=N) → specific game that moved TQ
6. LLM: explain causality
```

**Request example:**

```json
{
  "intent": "week_over_week",
  "params": {
    "year": 2024,
    "week": 10,
    "team": "Georgia",
    "prior_week": 9
  }
}
```

**Structured output:**

```json
{
  "structured": {
    "team": "Georgia",
    "current": { "week": 10, "rank": 5, "final_score": 1810.2 },
    "prior": { "week": 9, "rank": 7, "final_score": 1795.8 },
    "delta": {
      "rank": +2,
      "final_score": +14.4,
      "team_quality_score": +22.0,
      "record_score": +3.1,
      "conference_quality_score": 0.0
    },
    "field_context": {
      "teams_passed": ["Alabama", "Missouri"],
      "teams_fell_below": ["LSU"]
    }
  }
}
```

**Bulk variant** (Phase 3): omit `team` param → return top 10 movers by `|rank_delta|`.

**OpenCode workflow** (`.opencode/workflows/explain-wow.ts`):

```typescript
await ctx.agent({
  name: "week-over-week",
  prompt: `POST /agent/explain with intent week_over_week for Georgia week 9→10.
Verify delta.rank matches prior/current ranks. Explain must mention TQ delta if |delta.team_quality_score| > 10.`,
});
```

---

## 6. Rate Limiting and Auth Recommendations

### 6.1 Threat Model

| Risk | Mitigation |
|------|------------|
| LLM cost abuse | Rate limits + auth on `/agent/*` |
| CFBD quota exhaustion via MCP | Sidecar bucket limits; MCP allowlist |
| Prompt injection | Grounding rules; structured data boundary |
| Cache stampede | Agent path reads cache only; never bypasses cache |
| Data exfiltration | No raw CFBD key in frontend; MCP sidecar internal-only |

### 6.2 Authentication Tiers

| Tier | Audience | Mechanism | Routes |
|------|----------|-----------|--------|
| Public read | All users | None | `GET /rankings`, `GET /rankings/team/*` |
| Agent (anonymous) | Frontend visitors | Optional `X-Anonymous-Id` fingerprint | `POST /agent/explain` — strict limits |
| Agent (authenticated) | Logged-in / API partners | `Authorization: Bearer <JWT or API key>` | Higher limits |
| Admin | Operators | `X-Cache-Secret` or `ADMIN_API_KEY` | `/cache/clear`, sidecar admin |

**Phase 1:** No auth; IP-based rate limiting only (dev/staging).

**Phase 2:** Cloudflare Turnstile or anonymous session cookie + backend token for production frontend.

**Phase 3:** API keys for programmatic access (header `X-API-Key`).

### 6.3 Rate Limit Recommendations

Implement via Flask middleware or Cloudflare WAF rules in front of API:

| Endpoint | Anonymous | Authenticated | Window |
|----------|-----------|---------------|--------|
| `GET /rankings` | 60/min/IP | 300/min/key | Sliding |
| `GET /rankings/team/*` | 30/min/IP | 150/min/key | Sliding |
| `POST /agent/explain` | 5/min/IP, 20/day/IP | 30/min/key, 500/day/key | Sliding |
| MCP sidecar (internal) | 100 calls/hour global | — | Fixed |

**Response headers:**

```
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 3
X-RateLimit-Reset: 1690891200
Retry-After: 42          # on 429
```

**429 body:**

```json
{
  "error": "rate_limit_exceeded",
  "message": "Agent explain limit reached. Try again in 42 seconds.",
  "retry_after": 42
}
```

### 6.4 Secret Management

| Secret | Where | Notes |
|--------|-------|-------|
| `CFBD_API_KEY` | Backend + MCP sidecar only | Never expose to frontend |
| `MINIMAX_API_KEY` | Backend explainer + CI only | Never expose to frontend |
| `AGENT_API_KEY` | Optional frontend embed (Phase 2) | Scoped, rotatable; prefer server-side proxy |
| `CACHE_CLEAR_SECRET` | Existing | Keep for `/cache/clear` |

### 6.5 CORS Policy Update

Current: `CORS(app, origins=["*"])`. For production:

```python
CORS(app, origins=[
    "https://cfb-rankings.pages.dev",      # Cloudflare Pages
    "http://localhost:5173",                  # Dev frontend
], supports_credentials=True)
```

Add `POST /agent/explain` to allowed methods explicitly.

### 6.6 Logging & Observability

Log per explain request:

- `request_id`, `intent`, `year`, `week`, `team(s)`
- `latency_ms`, `llm_tokens`, `mcp_tools_called`
- `cached_rankings`, `degraded_mode`
- **Never log:** full prompts with PII, API keys

Metrics (Prometheus or structured logs):

- `agent_explain_requests_total{intent, status}`
- `agent_explain_latency_seconds{intent}`
- `mcp_sidecar_calls_total{tool}`

---

## 7. Phased Rollout Plan

### Phase 0 — Foundation (Current → Week 1)

**Goal:** Dev/CI agent infrastructure stable; no product changes.

| Task | Owner | Done when |
|------|-------|-----------|
| Document this spec | Eng | Spec merged |
| Verify `opencode.jsonc` + all 4 local workflows run | Eng | `ranking-qa` passes against local API |
| Compile gh-aw: `ranking-regression`, `daily-repo-status` | Eng | `.lock.yml` committed |
| Extract `ranking_breakdown.py` from `app.py` | Eng | `/rankings/team` unchanged; unit-ready functions |

**Exit criteria:** CI green; no regression on `/rankings`.

---

### Phase 1 — Explainer API (Weeks 2–3)

**Goal:** Backend `POST /agent/explain` for all three intents; no MCP yet.

| Task | Deliverable |
|------|-------------|
| Add `agent/` module with Pydantic schemas | `POST /agent/explain` returns structured + LLM answer |
| Implement `rank_explanation`, `compare_teams`, `week_over_week` handlers | Golden JSON fixtures in `tests/fixtures/agent/` |
| Add `GET /agent/health`, `GET /agent/intents` | OpenAPI snippet in README |
| OpenCode workflow `agent-explain-qa.ts` | Local QA command documented |
| gh-aw `explain-regression.md` (PR comment, non-blocking) | Compiled lock file |
| IP rate limiting on `/agent/*` | 5/min default |

**Exit criteria:** All three intents return grounded responses in < 5s (cached rankings); OpenCode QA workflow passes.

---

### Phase 2 — Frontend Chat Panel (Weeks 4–5)

**Goal:** Ship chat UI on rankings page with suggested prompts.

| Task | Deliverable |
|------|-------------|
| `AgentChatPanel.svelte` + store + API client | Panel opens from header + team modal |
| Suggested prompts wired to explicit intents | Three prompts from §5 |
| `AgentStructuredCard` reusing TeamDetailModal visuals | Breakdown renders inline |
| Feature flag: `VITE_AGENT_CHAT_ENABLED` | Default off in prod until Phase 2 complete |
| Mobile bottom-sheet UX | Responsive QA pass |

**Exit criteria:** User can ask "Why is X #Y?" from UI and see markdown + structured card; svelte-check clean.

---

### Phase 3 — CFBD MCP Sidecar (Weeks 6–7)

**Goal:** Optional enrichment; degraded mode proven.

| Task | Deliverable |
|------|-------------|
| Deploy MCP sidecar (Docker Compose locally; Render service prod) | `GET /agent/health` shows `mcp_sidecar: up` |
| `agent/mcp_client.py` with allowlist | Max 3 tools per request |
| Enrichment for rank_explanation + week_over_week | Game context in citations |
| Separate CFBD rate-limit bucket | Monitoring dashboard |
| gh-aw `mcp-sidecar-health.md` weekly cron | Alert on sidecar down |

**Exit criteria:** Explain responses include game context when sidecar up; identical structured scores when sidecar down.

---

### Phase 4 — Auth, Streaming, NL Intent (Weeks 8–10)

**Goal:** Production hardening and UX polish.

| Task | Deliverable |
|------|-------------|
| Cloudflare Turnstile + session tokens | Anonymous tier with fair limits |
| API key tier for partners | Admin key rotation runbook |
| SSE streaming for long answers | `GET /agent/explain/stream` |
| Client-side NL → intent heuristics | Free-text input supported |
| Bulk week_over_week (top movers) | Suggested prompt: "Biggest movers this week" |

**Exit criteria:** Production deploy with auth + rate limits; streaming chat UX; no CFBD quota incidents over 1 week.

---

### Rollout Risk Matrix

| Risk | Phase | Mitigation |
|------|-------|------------|
| LLM hallucinates scores | 1 | Grounding prompt + structured citation requirement |
| Cold rankings double latency | 1 | Agent path reads cache; warn in `meta` if cache miss |
| MCP sidecar SPOF | 3 | Degraded mode default; health check |
| Cost overrun | 2+ | Rate limits before public launch |
| CORS/auth misconfiguration | 2 | Staging environment with prod-like CORS first |

---

## Appendix A: Environment Variables

| Variable | Required by | Description |
|----------|-------------|-------------|
| `CFBD_API_KEY` | Flask, MCP sidecar | CollegeFootballData API |
| `MINIMAX_API_KEY` | Explainer, OpenCode CI | LLM provider |
| `MCP_SIDECAR_URL` | Flask agent module | Default `http://localhost:5100` |
| `AGENT_RATE_LIMIT_PER_MIN` | Flask | Default `5` |
| `AGENT_API_KEY` | Flask (Phase 3+) | Bearer token validation |
| `VITE_AGENT_CHAT_ENABLED` | Frontend | Feature flag |
| `VITE_AGENT_TOKEN` | Frontend (optional) | Pre-issued anonymous token |

---

## Appendix B: File Additions Summary

```
agent/
├── __init__.py
├── explainer.py
├── mcp_client.py
├── schemas.py
├── intents/
│   ├── rank_explanation.py
│   ├── compare_teams.py
│   └── week_over_week.py
└── prompts/
    └── system.md

ranking_breakdown.py              # Extracted from app.py

.opencode/workflows/
├── explain-rank.ts
├── explain-compare.ts
├── explain-wow.ts
└── agent-explain-qa.ts

.github/workflows/
├── explain-regression.md
└── mcp-sidecar-health.md

frontend/src/lib/
├── api/agent.ts
├── stores/agentChat.ts
└── components/agent/
    ├── AgentChatPanel.svelte
    ├── AgentMessageList.svelte
    ├── AgentMessage.svelte
    ├── AgentInput.svelte
    ├── AgentSuggestedPrompts.svelte
    └── AgentStructuredCard.svelte

docker-compose.yml                # cfbd-mcp sidecar service (Phase 3)
```

---

## Appendix C: Decision Log

| Decision | Rationale | Alternatives rejected |
|----------|-----------|----------------------|
| MCP as sidecar, not in Flask process | Isolates CFBD quota; avoids blocking GIL; independent restart | In-process MCP SDK |
| MiniMax for product + CI | Already configured in `opencode.jsonc`; single vendor | Separate model for prod |
| Structured-first, LLM-second | Prevents hallucination; reuses existing breakdown logic | Pure LLM over raw rankings JSON |
| Explicit intents in Phase 1 | Predictable testing; lower cost | Full NLU from day one |
| POST not GET for explain | Complex body; not cacheable; avoids query-length limits | `GET /agent/explain?q=...` |

---

*End of spec.*
