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

- **Production (deployed app):** store `CFBD_API_KEY` / optional `MINIMAX_API_KEY` in **Cloudflare** (API service secrets). See [docs/SECRETS.md](docs/SECRETS.md).
- **This Cloud Agent VM only:** Cursor Secrets tab — [.cursor/SECRETS.md](.cursor/SECRETS.md). Cursor secrets do not sync to Cloudflare.

### CFBD_API_KEY is required for real data
- Both `app.py` and the CLI instantiate the CFBD API client **at import/startup time**. Import/startup succeeds even with a missing/invalid key, but every data request then returns empty results, so `GET /rankings` responds `404 {"error": "No game data found ..."}` instead of rankings.
- A valid `CFBD_API_KEY` (from collegefootballdata.com) must be present as an environment variable for the core ranking feature to work. `app.py` calls `load_dotenv()`, so a real env var takes precedence and a repo-root `.env` also works locally.
- Network egress to `https://api.collegefootballdata.com` is available from the VM; an invalid key surfaces as a `401` in the backend logs.
- Start the backend with the key in the environment, e.g. `CFBD_API_KEY=... ./venv/bin/python app.py`.

### Running / testing caveats
- Run backend and frontend in separate long-lived shells (tmux). Start backend first (`./venv/bin/python app.py` → :5001), then frontend (`cd frontend && npm run dev` → :5173).
- First `/rankings` request for a season is slow: the backend also pulls prior seasons to compute priors and runs an iterative solver. Results are cached under `.cache/` (file + memory), so repeat requests are fast. Archived weeks prefer static JSON when present.
- There are **automated tests** in `tests/`; `pytest` is blocking in CI. Lint is the other meaningful gate: `flake8` blocking check is `--select=E9,F63,F7,F82`; the full flake8 pass and frontend `npm run lint` (ESLint) report many pre-existing style issues and are **non-blocking** in CI (`--exit-zero` / `continue-on-error`). `frontend/npm run check` (svelte-check) is clean and is enforced.
