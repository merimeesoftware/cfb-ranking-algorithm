# Cursor Cloud Secrets — for Cloud Agent VMs only

These secrets let a **Cursor Cloud Agent** run the Flask API while coding.  
They are **not** production. Once the app is deployed, put the same keys in **Cloudflare** — see [docs/SECRETS.md](../docs/SECRETS.md).

```
Cursor Secrets  →  agent VM (dev)
Cloudflare      →  deployed API (production)   ← source of truth for live traffic
```

## Add secrets for this Cloud Agent environment

1. Open:
   **https://cursor.com/dashboard/cloud-agents/environments/e/8a950cce-89fd-11f1-b532-320a589b8025**
2. **Secrets** tab → add as **Runtime Secret**:

| Secret name | Required for agent VM? | Purpose |
|-------------|------------------------|---------|
| `CFBD_API_KEY` | Yes (to exercise rankings) | [collegefootballdata.com/key](https://collegefootballdata.com/key) |
| `MINIMAX_API_KEY` | Optional | Product `/agent/explain` endpoint (optional feature) |

3. Restart the Cloud Agent after saving.

## After you deploy

Set the **same** keys on the Cloudflare API service (dashboard → Variables and Secrets, or `wrangler secret put`).  
Cursor and Cloudflare do not sync automatically — that is intentional (dev vs prod).

## Local laptop

```bash
cp .env.example .env
# edit CFBD_API_KEY / MINIMAX_API_KEY
```

## Not needed in Cursor

| Not needed | Why |
|------------|-----|
| `CLOUDFLARE_API_TOKEN` | Pages uses GitHub integration; secrets for the *app* go in Cloudflare |
| `CLOUDFLARE_ACCOUNT_ID` | Same |
| `VITE_API_URL` | Frontend uses `/api` proxy |
| `CACHE_CLEAR_SECRET` | Optional prod-only admin; set in Cloudflare if you want it |
