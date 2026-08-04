# AGENTS.md

## Cursor Cloud specific instructions

Product: **CFB Ranking System** — an algorithmic college football ranking app. It has three entry points that all share the same Python data/algorithm modules:

- **Flask API backend** — `app.py`, serves rankings JSON on port **5001**.
- **SvelteKit frontend** — `frontend/`, dev server on port **5173** (Vite). In dev, calls backend via `/api` proxy → `:5001`.
- **CLI** — `main.py` (optional; prints/saves rankings, generates charts).

Standard commands live in `README.md`, `frontend/package.json`, and `.github/workflows/ci-cd.yml`. Notes below are the non-obvious caveats.

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

- **Production (deployed app):** store `CFBD_API_KEY` / optional paygo `MINIMAX_API_KEY` in **Cloudflare**. See [docs/SECRETS.md](docs/SECRETS.md).
- **This Cloud Agent VM only:** Cursor Secrets tab — [.cursor/SECRETS.md](.cursor/SECRETS.md). Cursor secrets do not sync to Cloudflare.

### Local spend guards (prefer over live APIs)

- Free CFBD tier is **1,000 calls/month**. Local default: `CFBD_OFFLINE=1` (also default when `FLASK_ENV=development` if unset) — no live CFBD; use `.cache/` and `frontend/static/rankings/`.
- `AI_MODE=stub` (dev default) returns template explanations with **no MiniMax** call. `off` returns `explanation: null`. `live` needs a paygo MiniMax key (not Coding Plan).
- **Hard caps in development** (even if you enable live): `CFBD_MAX_CALLS` and `AI_MAX_CALLS` default to **25**. Override in `.env`.
- `AGENT_RATE_LIMIT` caps `/agent/explain` per IP (default 50/hour in dev).
- Check live counters: `GET /agent/health` → `cfbd_calls`, `ai_live_calls`, budgets.
- See `.env.example`.

### CFBD_API_KEY for live data
- Needed only when `CFBD_OFFLINE=0` and cache/static miss. Import/startup can succeed offline; rankings for archived weeks should come from static JSON.
- Network egress to `https://api.collegefootballdata.com` is available from the VM; an invalid key surfaces as a `401` in the backend logs.
- Start offline-first: `CFBD_OFFLINE=1 AI_MODE=stub FLASK_ENV=development ./venv/bin/python app.py`.

### Running / testing caveats
- Run backend and frontend in separate long-lived shells (tmux). Start backend first (`./venv/bin/python app.py` → :5001), then frontend (`cd frontend && npm run dev` → :5173).
- First live `/rankings` for a season is slow (priors + solver). Prefer static 2024 weeks for UI work. Results cache under `.cache/`.
- There are **automated tests** in `tests/`; `pytest` is blocking in CI. Lint blocking check: `flake8 --select=E9,F63,F7,F82`. `frontend/npm run check` is enforced.
