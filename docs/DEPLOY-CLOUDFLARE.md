# Deploy to Cloudflare (simple pattern)

**Goal:** One Cloudflare account + GitHub connected once. No per-project Cloudflare API tokens in GitHub.

## Recommended: Cloudflare Pages Git integration

This is the standard pattern — Cloudflare builds and deploys when you push to `main`. GitHub Actions only validates (lint/test/build); it does not deploy.

### One-time account setup

1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com) → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**.
2. Authorize the **Cloudflare GitHub App** for your org/user (one-time).
3. Select this repository.

### Per-project settings (in Cloudflare UI, not GitHub secrets)

| Setting | Value |
|---------|-------|
| Production branch | `main` |
| Root directory | `frontend` |
| Build command | `npm ci && npm run build` |
| Build output | `build` |
| Node version | 20 |

No `CLOUDFLARE_API_TOKEN` or `CLOUDFLARE_ACCOUNT_ID` in GitHub.

### API routing (no `VITE_API_URL` secret)

The frontend calls **`/api/*`** (same origin). Cloudflare proxies to your backend via `frontend/static/_redirects`:

```
/api/*  https://YOUR-API-HOST/:splat  200
```

Edit that one line when your API host changes (Render during cutover, Cloudflare Containers after).

Alternatively, set a **Bulk Redirect / Transform Rule** in the Cloudflare dashboard instead of editing the file.

### Backend secrets (Cloudflare Containers or Render)

Set **`CFBD_API_KEY`** in the backend host's environment (Cloudflare Container secrets or Render dashboard) — not in the frontend build.

Optional: **`MINIMAX_API_KEY`** for `/agent/explain` on the API service only.

## What GitHub still needs

| Secret | Scope | Notes |
|--------|-------|-------|
| `CFBD_API_KEY` | Repo | CI validation + backend deploy target |

That's it for a minimal setup. Org-level secrets can reuse the same `CFBD_API_KEY` across repos if desired.

## Advanced: wrangler in CI (not recommended for most projects)

Only use `cloudflare/wrangler-action` + `CLOUDFLARE_API_TOKEN` if you need programmatic deploy from GitHub Actions instead of Cloudflare's Git integration. Prefer the Git integration above.
