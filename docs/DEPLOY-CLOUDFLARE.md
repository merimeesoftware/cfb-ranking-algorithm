# Deploy to Cloudflare (simple pattern)

**Goal:** One Cloudflare account + GitHub connected once. Production secrets live **in Cloudflare**, not in GitHub or Cursor.

See also: [SECRETS.md](./SECRETS.md) for the full secrets architecture.

## Recommended: Cloudflare Pages Git integration

Cloudflare builds and deploys when you push to `main`. GitHub Actions only validates (lint/test/build); it does not deploy.

### One-time account setup

1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com) → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**.
2. Authorize the **Cloudflare GitHub App** for your org/user (one-time).
3. Select this repository.

### Per-project settings (in Cloudflare UI)

| Setting | Value |
|---------|-------|
| Production branch | `main` |
| Root directory | `frontend` |
| Build command | `npm ci && npm run build` |
| Build output | `build` |
| Node version | 20 |

No `CLOUDFLARE_API_TOKEN` or `CLOUDFLARE_ACCOUNT_ID` in GitHub.

### API routing (frontend → backend)

The frontend calls **`/api/*`** (same origin). Cloudflare proxies via `frontend/static/_redirects`:

```
/api/*  https://YOUR-API-HOST/:splat  200
```

Update that host when the API moves (Render → Cloudflare Containers, etc.).

---

## Production secrets (Cloudflare — do this after deploy)

**This is the primary place for production keys.**

1. Deploy / create the API service (Cloudflare Containers, or Render during hybrid cutover).
2. In Cloudflare Dashboard → that service → **Settings → Variables and Secrets**.
3. Add:

| Secret | Required |
|--------|----------|
| `CFBD_API_KEY` | Yes |
| `MINIMAX_API_KEY` | Optional (agent explain) |

Or from a machine where you have run `wrangler login` once:

```bash
wrangler secret put CFBD_API_KEY
wrangler secret put MINIMAX_API_KEY
```

Pages (frontend) needs **no** secrets — only the `_redirects` proxy target.

---

## Cursor Cloud vs Cloudflare

| Place | Role |
|-------|------|
| **Cloudflare secrets** | Live production app |
| **Cursor Secrets tab** | Only so Cloud Agents can run the API while coding ([.cursor/SECRETS.md](../.cursor/SECRETS.md)) |
| **GitHub secrets** | Prefer none for production; CI can mock CFBD |

Setting a key in Cursor does **not** put it in Cloudflare. After first deploy, set production secrets in Cloudflare.

---

## Hybrid cutover (optional)

Until the API runs on Cloudflare Containers, you can keep the Flask API on Render and point `_redirects` at it. Set `CFBD_API_KEY` in Render's dashboard for that interim. When Containers are ready, move the secret to Cloudflare and update `_redirects`.
