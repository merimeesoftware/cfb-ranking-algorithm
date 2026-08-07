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

**You only need one production Worker to start.** Dev is optional.

| | Production (required) | Dev (optional) |
|---|------------------------|----------------|
| **When** | Live site on `main` | Staging / testing before prod |
| **Worker name** | `cfb-rankings` | `cfb-rankings-dev` |
| **URL** | `https://cfb-rankings.<account>.workers.dev` | `https://cfb-rankings-dev.<account>.workers.dev` |
| **How** | Workers Builds on `main` (automatic) or `npm run deploy` | Manual `npm run deploy:dev` only if you want a second Worker |

**Workers Builds (recommended):**
- **Production branch** (`main`) → deploys `cfb-rankings` automatically
- **Other branches** → preview versions (`wrangler versions upload`) on the same Worker — no second Worker required

You do **not** need two Workers unless you want a permanently separate staging URL with its own secrets.

---

## Secrets (dashboard — no CLI required)

`wrangler secret put` is optional. Prefer the dashboard:

1. **Workers & Pages** → `cfb-rankings` → **Settings** → **Variables and Secrets**
2. **Add** → type **Secret** → name `CFBD_API_KEY` → paste value → **Encrypt** → **Deploy**

Repeat for `MINIMAX_API_KEY` / `CACHE_CLEAR_SECRET` if needed. Values are encrypted and never shown again.

For `cfb-rankings-dev` (only if you use the dev Worker): same steps on that Worker, or use `wrangler secret put CFBD_API_KEY --env dev` once.

---

## Workers Builds settings (Cloudflare dashboard)

**Settings → Build** on your Worker:

| Setting | Value |
|---------|-------|
| Production branch | `main` |
| Build command | `npm run build` |
| Deploy command | `npx wrangler deploy` |

Root `npm ci` runs `postinstall`, which installs `frontend/` and `worker/` deps (fixes `vite: not found`).

**Runtime secrets** (for the live app): **Settings → Variables and Secrets** (not Build Variables).

| Secret | Required |
|--------|----------|
| `CFBD_API_KEY` | Yes (live rankings) |
| `MINIMAX_API_KEY` | Optional (`AI_MODE=live`) |
| `CACHE_CLEAR_SECRET` | Optional (protects `POST /api/cache/clear`) |

---

## One-time setup (local deploy alternative)

### Prerequisites (local deploy only)

- Cloudflare account with **Workers Paid** plan (required for Containers)
- Docker running locally (for `wrangler deploy` to build the API image)
- `wrangler login` once on your machine

### Deploy locally

```bash
npm ci   # installs root, frontend, and worker via postinstall
npm run deploy          # production
npm run deploy:dev      # optional second Worker
```

First deploy builds the Docker image and can take several minutes. The Worker may not serve traffic until containers are provisioned (~2–5 min).

### Verify

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
