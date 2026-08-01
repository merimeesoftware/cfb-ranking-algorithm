# Cursor Cloud Secrets — where to enter API keys

**Do not put secrets in this repo.** Cursor injects them as environment variables at runtime from the dashboard.

## Add secrets in Cursor (one-time per environment)

1. Open your Cloud Agent environment:
   **https://cursor.com/dashboard/cloud-agents/environments/e/8a950cce-89fd-11f1-b532-320a589b8025**
2. Go to the **Secrets** tab.
3. Add each secret below. Use **Runtime Secret** for API keys (model cannot read the value).

| Secret name | Required? | Purpose |
|-------------|-----------|---------|
| `CFBD_API_KEY` | **Yes** (for rankings) | College Football Data API — [get free key](https://collegefootballdata.com/key) |
| `MINIMAX_API_KEY` | Optional | Agent workflows (`/agent/explain`, OpenCode, gh-aw) — [MiniMax platform](https://platform.minimax.io/user-center/basic-information/interface-key) |

After saving, restart the Cloud Agent. The backend reads these via `load_dotenv()` and standard env vars.

## Local development

Copy `.env.example` → `.env` and fill in the same keys locally:

```bash
cp .env.example .env
# edit .env — CFBD_API_KEY and optionally MINIMAX_API_KEY
```

## What you do NOT need in Cursor

| Not needed | Why |
|------------|-----|
| `CLOUDFLARE_API_TOKEN` | Use Cloudflare Pages **GitHub integration** (see `docs/DEPLOY-CLOUDFLARE.md`) — no per-repo Cloudflare token |
| `CLOUDFLARE_ACCOUNT_ID` | Same — configured once in Cloudflare dashboard when connecting GitHub |
| `VITE_API_URL` | Frontend uses same-origin `/api` proxy; no build-time URL secret |
| `CACHE_CLEAR_SECRET` | Optional admin-only; `/cache/clear` is disabled unless you explicitly set this |
