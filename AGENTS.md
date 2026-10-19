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

- Free CFBD tier is **1,000 calls/month**. Local default: `CFBD_OFFLINE=1` (also default when `FLASK_ENV=development` if unset) — no live CFBD; use `.cache/` and `frontend/static/rankings/`.
- `AI_MODE=stub` (local, preview, and production default) returns template explanations with no live provider call. `off` returns `explanation: null`. `live` uses xAI (`XAI_API_KEY`, Worker-only) or Workers AI (the `[ai]` binding).
- **Hard caps when the vars are unset:** `XAI_MAX_CALLS` and `WORKERS_AI_MAX_CALLS` **0/day**, `CFBD_MAX_CALLS` **25/day**. Unset is never unlimited. Production `wrangler.toml` sets both AI caps to `0` and `CFBD_MAX_CALLS=4` so the free CFBD tier stays under 900 calls/month. The Worker stores that global counter on the `CfbApiContainer` instance `spend-budget`; Flask repeats the same numbers per process. `AI_KILL` stops both providers. `XAI_KILL` and `WORKERS_AI_KILL` stop one.
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
