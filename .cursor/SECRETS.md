# Cursor Cloud Secrets — for Cloud Agent VMs only

These secrets let a **Cursor Cloud Agent** run the Flask API while coding.  
They are **not** production. Once the app is deployed, put the same keys in **Cloudflare** — see [docs/SECRETS.md](../docs/SECRETS.md).

```
Cursor Secrets  →  agent VM (dev)
Cloudflare      →  deployed API (production)   ← source of truth for live traffic
```

## Do not put secrets in `environment.json`

`.cursor/environment.json` is committed to git. It configures install/start/terminals only.  
**Never** put `CFBD_API_KEY` / `MINIMAX_API_KEY` (or any credential) in that file.

## Where secrets actually live

This repo uses a **repo-file environment** (`source: Repository` from `.cursor/environment.json`).  
That auto environment's dashboard page often has **no Secrets tab** — that is normal.

Secrets for this project are configured on the **Cloud Agents Secrets** page (user / team), the same place `CFBD_API_KEY` already comes from:

1. Open **[Cloud Agents dashboard → Secrets](https://cursor.com/dashboard/cloud-agents)** (Secrets / Credentials section — **not** the per-environment Builds page).
2. Add as **Runtime Secret** (redacted from the model transcript; still available as an env var to processes):

| Secret name | Scope | Purpose |
|-------------|-------|---------|
| `CFBD_API_KEY` | **Personal** (you) or **Team** (shared) | Live CFBD pulls when `CFBD_OFFLINE=0` |
| `MINIMAX_API_KEY` | Same as CFBD | Paygo MiniMax for `AI_MODE=live` only |

3. **Start a new Cloud Agent** (or restart this one). Secrets inject at **VM boot**, not when you restart Flask alone.

### Personal vs environment vs team scope

| Scope | Who gets it | When to use |
|-------|-------------|-------------|
| **Personal** | Only your agents | Fine for solo keys; matches how many people already store `CFBD_API_KEY` |
| **Team** | Everyone on the Cursor team | Best permanent shared setup for this repo |
| **Environment-scoped** | Only agents using one **saved** dashboard environment | Use if you create a named multi-repo / staging environment with its own Secrets UI. **Not** available on the thin repo-observed environment page |

For this CFB repo: prefer **Team** Runtime Secrets (or Personal if you are solo). Do not chase Secrets UI on the repo-file environment page.

### Optional: saved dashboard environment

If you want environment-scoped secrets + Builds UI in one place:

1. [Create an environment](https://cursor.com/dashboard/cloud-agents#environments) for `merimeesoftware/cfb-ranking-algorithm`
2. Add Runtime Secrets there
3. Launch agents **into that environment**

You can keep `.cursor/environment.json` for install/start so the team still gets the same terminals/ports.

## Local spend defaults

Use `.env.example`: `CFBD_OFFLINE=1`, `AI_MODE=stub`. Browse committed `frontend/static/rankings/2024/` without burning CFBD or MiniMax.

## After you deploy

Set the **same** keys on the Cloudflare Worker (dashboard → Variables and Secrets, or `wrangler secret put`).  
Cursor and Cloudflare do not sync automatically — that is intentional (dev vs prod).

## Local laptop

```bash
cp .env.example .env
# edit CFBD_API_KEY / MINIMAX_API_KEY
```

## Not needed in Cursor

| Not needed | Why |
|------------|-----|
| `CLOUDFLARE_API_TOKEN` | Pages/Worker deploy uses GitHub integration; app secrets go in Cloudflare |
| `CLOUDFLARE_ACCOUNT_ID` | Same |
| `VITE_API_URL` | Frontend uses `/api` proxy |
| `CACHE_CLEAR_SECRET` | Optional prod-only admin; set in Cloudflare if you want it |
