# AGENTS.md

## Cursor Cloud specific instructions

Product: **True Rankings** (CFB Ranking System) — algorithmic college football rankings (**TR+**). Three entry points share the same Python data/algorithm modules:

- **Flask API backend** — `app.py`, serves rankings JSON on port **5001**.
- **SvelteKit frontend** — `frontend/`, dev server on port **5173** (Vite). In dev, calls backend via `/api` proxy → `:5001`.
- **CLI** — `main.py` (optional; prints/saves rankings, generates charts).

Standard commands live in `README.md`, `frontend/package.json`, and `.github/workflows/ci.yml`. Notes below are the non-obvious caveats.

### What belongs in git vs local-only

| Commit | Do not commit |
|--------|----------------|
| App code, tests, real Actions (`*.yml`), Dependabot | Vendor Cursor skills (Impeccable under `.cursor/skills/`) |
| `docs/`, this file, `.cursor/environment.json`, `.cursor/SECRETS.md` | OpenCode (`opencode.jsonc`, `.opencode/`) — not used on the deployed site |
| Slim static rankings under `frontend/static/rankings/` | gh-aw markdown workflows / `.github/skills/` |
| | Secrets, `venv/`, `.cache/`, host `static_rankings/` |

Impeccable / OpenCode are fine to install **locally or via Cursor plugins** for design/CI experiments; they are not part of the product ship.

### Python environment
- Python deps are installed into a repo-local virtualenv at `venv/` (created by the update script). Run backend/lint/test tools via `./venv/bin/...` (e.g. `./venv/bin/python app.py`, `./venv/bin/flake8`, `./venv/bin/pytest`). There is no global project install.
- Dev/lint/test tools (`flake8`, `bandit`, `pytest`, `pytest-cov`) are installed on top of `requirements.txt`; they are NOT in `requirements.txt`. Do not use `requirements-dev.txt` — it pins older/conflicting versions (e.g. `pydantic<2`) and is not what CI uses.

### Secrets

- **Production (deployed app):** store `CFBD_API_KEY` in **Cloudflare**. `XAI_API_KEY` is provisioned by DevSecOps on Michael's yes. See [docs/SECRETS.md](docs/SECRETS.md).
- **This Cloud Agent VM only:** Cursor Secrets tab — [.cursor/SECRETS.md](.cursor/SECRETS.md). Cursor secrets do not sync to Cloudflare.

### Local spend guards (prefer over live APIs)

- Free CFBD tier is **1,000 calls/month**, shared with the agent/dev MCP server (#115). This app is provider `cfbd`, source `app`, ceiling **700/month** (cron + live). 150 is reserved for MCP via #115. 50 is margin. Local default: `CFBD_OFFLINE=1` (also default when `FLASK_ENV=development` if unset) — no live CFBD; use `.cache/` and `frontend/static/rankings/`.
- `AI_MODE=stub` (local and preview default) returns template explanations with no live provider call. Production `wrangler.toml` `[vars]` is `AI_MODE=live` (Workers AI) with `CFBD_OFFLINE=1`. `off` returns `explanation: null`. `live` uses xAI (`XAI_API_KEY`, Worker-only) or Workers AI (the `[ai]` binding). Both go through AI Gateway `true-rankings` for logging. `CF_ACCOUNT_ID` and `AI_GATEWAY_ID` are non-secret vars. The `spend-budget` instance remains the budget. Production keeps xAI off (`XAI_ENABLED=0`, `XAI_MAX_CALLS=0`).
- **Hard caps when the vars are unset:** xAI is hard **0/day** and `XAI_ENABLED` defaults off, so a key does not start a call. `XAI_WEEKLY_USD_CAP` defaults to **0**. The week estimate is input and output tokens times `config/xai-usd.json`. CI fails when that cap plus CFBD's paid tier reaches **$5** a week ($0.23 only when `CFBD_TIER=1`). `AI_MAX_CALLS` is the Workers AI cap, **100/day** (worst case 58 Neurons × 100 = 5800, ceiling 8000). `CFBD_MAX_CALLS` **25/day** in code, **4/day** in production. Unset is never unlimited. The Worker stores the daily counter and the xAI week dollars on the `CfbApiContainer` instance `spend-budget`; Flask repeats the same numbers per process. `AI_KILL` stops both providers. `XAI_KILL` and `WORKERS_AI_KILL` stop one.
- `AI_KILL=1` / `CFBD_KILL=1` stop live paid calls. Preview hostnames use `AI_MODE=stub` and `CFBD_OFFLINE=1` unless `PREVIEW_AI_MODE` / `PREVIEW_CFBD_OFFLINE` are set.
- `AGENT_RATE_LIMIT` caps `/agent/*` per `CF-Connecting-IP` (default 50/hour in dev, 30/hour in production). The edge limiter is separate and also ignores `X-Forwarded-For`.
- `GET /agent/health` and `GET /cache/stats` do not expose budgets or counters.
- See `.env.example`.

### CFBD_API_KEY for live data
- Needed only when `CFBD_OFFLINE=0` and cache/static miss. Import/startup can succeed offline; rankings for archived weeks should come from static JSON.
- Network egress to `https://api.collegefootballdata.com` is available from the VM; an invalid key surfaces as a `401` in the backend logs.
- Start offline-first: `CFBD_OFFLINE=1 AI_MODE=stub FLASK_ENV=development ./venv/bin/python app.py`.

### Running / testing caveats
- Run backend and frontend in separate long-lived shells (tmux). Start backend first (`./venv/bin/python app.py` → :5001), then frontend (`cd frontend && npm run dev` → :5173).
- First live `/rankings` for a season is slow (priors + solver). Prefer static 2024 weeks for UI work. Results cache under `.cache/`.
- There are **automated tests** in `tests/`; `pytest` is blocking in CI. Lint blocking check: `flake8 --select=E9,F63,F7,F82`. `frontend/npm run check` is enforced.
