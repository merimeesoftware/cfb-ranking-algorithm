# Deploy to Cloudflare Workers

**Goal:** One Worker deploy for the whole app — static SvelteKit frontend + Flask API container. Production secrets live **in Cloudflare**, not GitHub or Cursor.

See also: [SECRETS.md](./SECRETS.md)

---

## Architecture

```mermaid
flowchart LR
  Browser --> Worker["Worker (cfb-rankings)"]
  Worker -->|"/api/*"| Container["Flask Container"]
  Worker -->|"everything else"| Assets["Static assets (frontend/build)"]
  Container --> CFBD["collegefootballdata.com"]
```

| Path | Handled by |
|------|------------|
| `/api/*` | Worker → Cloudflare Container (Flask) |
| `/`, `/methodology`, etc. | Static assets (SPA fallback to `index.html`) |
| `/rankings/2024/*.json` | Static precomputed rankings |

One `wrangler deploy` uploads **both** the frontend build and the API container image.

---

## Environments (dev + prod)

| | Production | Dev |
|---|------------|-----|
| **Command** | `npm run deploy` | `npm run deploy:dev` |
| **Worker name** | `cfb-rankings` | `cfb-rankings-dev` |
| **URL** | `https://cfb-rankings.<account>.workers.dev` | `https://cfb-rankings-dev.<account>.workers.dev` |
| **Secrets** | `wrangler secret put CFBD_API_KEY` | `wrangler secret put CFBD_API_KEY --env dev` |

No separate Pages project. No `API_ORIGIN` variable — `/api` is same-origin by design.

---

## One-time setup

### 1. Prerequisites

- Cloudflare account with **Workers Paid** plan (required for Containers)
- Docker running locally (for `wrangler deploy` to build the API image)
- `wrangler login` once on your machine

### 2. Deploy

```bash
# From repo root
npm ci --prefix frontend
npm ci --prefix worker
npm ci   # root wrangler

npm run deploy          # production
npm run deploy:dev      # dev/staging
```

First deploy builds the Docker image and can take several minutes. The Worker may not serve traffic until containers are provisioned (~2–5 min).

### 3. Set secrets

```bash
npx wrangler secret put CFBD_API_KEY
npx wrangler secret put MINIMAX_API_KEY      # optional
npx wrangler secret put CACHE_CLEAR_SECRET   # optional

# Dev
npx wrangler secret put CFBD_API_KEY --env dev
```

Or: Dashboard → **Workers & Pages** → `cfb-rankings` → **Settings → Variables and Secrets**.

| Secret | Required |
|--------|----------|
| `CFBD_API_KEY` | Yes (live rankings) |
| `MINIMAX_API_KEY` | Optional (`AI_MODE=live`) |
| `CACHE_CLEAR_SECRET` | Optional (protects `POST /api/cache/clear`) |

### 4. Verify

```bash
WORKER_URL="https://cfb-rankings.<account>.workers.dev"
curl -sf "${WORKER_URL}/"
curl -sf --max-time 120 "${WORKER_URL}/api/rankings?year=2024&week=10" | head -c 200
```

Open the Worker URL in a browser — rankings for 2024 should load.

### 5. Connect GitHub (optional CI deploy)

**Workers & Pages** → **Workers** → **Create** → connect this repo, or use GitHub Actions:

Repository variables:
- `ENABLE_CLOUDFLARE_DEPLOY` = `true`
- `WORKER_URL` = your production Worker URL (for smoke tests)

Repository secrets:
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`

---

## Custom domain (Porkbun → Cloudflare)

Porkbun has no Cloudflare integration — DNS is manual.

### Recommended: Cloudflare DNS

1. Add your domain to Cloudflare; point Porkbun nameservers at Cloudflare
2. Worker → **Settings → Domains & Routes** → **Add** → **Custom Domain** → e.g. `rankings.yourdomain.com`
3. Cloudflare creates DNS records automatically

### Keep DNS at Porkbun

Worker → **Domains & Routes** → note the custom domain target, then at Porkbun add a **CNAME** for your subdomain.

After custom domain is live, set the `CORS_ORIGINS` secret to your domain.

---

## Local development

```bash
CFBD_OFFLINE=1 AI_MODE=stub ./venv/bin/python app.py   # :5001
cd frontend && npm run dev                              # :5173, proxies /api
```

---

## CI/CD

| Workflow | Role |
|----------|------|
| `ci.yml` | Lint, test, build — blocks merges |
| `deploy-cloudflare.yml` | Build + deploy when `ENABLE_CLOUDFLARE_DEPLOY=true` |

### Planned

- Playwright E2E against `cfb-rankings-dev.*.workers.dev`
- Impeccable frontend audit in CI
- Auto-promote dev → prod after tests pass

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| API 503 right after first deploy | Wait 2–5 min for container provisioning |
| Cold `/api/rankings` slow | Expected; use static 2024 JSON for UI work |
| `wrangler deploy` fails | Ensure Docker is running |
| CORS errors on custom domain | Set `CORS_ORIGINS` secret on the Worker |

---

## Cursor Cloud vs Cloudflare

| Place | Role |
|-------|------|
| **Cloudflare secrets** | Live production (and dev) Worker |
| **Cursor Secrets tab** | Cloud Agent VM only — [.cursor/SECRETS.md](../.cursor/SECRETS.md) |
| **GitHub secrets** | CI deploy tokens only |

Setting a key in Cursor does **not** deploy it to Cloudflare.
