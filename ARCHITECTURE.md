# Architecture

Visitor requests for `/api/*` hit the edge Worker. Everything else is static.

## Request path

1. The Worker (`worker/src/index.ts`) receives the request.
2. `routeApiRequest` decodes the pathname once and produces one canonical path. A control character (`%00`–`%1F`, `%7F`, raw or decoded), an encoded slash or backslash, a backslash, a failed decode, or a path that changes on a second decode returns 400. That canonical path is the decoded value: a team name sent as `%20` or an accent is the decoded name. The container URL encodes that path again.
3. That same path is the route classifier, which limiter applies, the counter-header strip, and the path on the container URL. Visitor limits are keyed on `CF-Connecting-IP`. The URL builder must reproduce the path. A rewrite is a 400.
4. `/api/*` is limited per `CF-Connecting-IP`. Paths under `/agent/` also take the tighter agent limiter.
5. Paid calls ask the SpendBudget Durable Object (`spend-budget` on `CfbApiContainer`) before the provider runs. The object stores the daily counters and the `ai_kill` / `cfbd_kill` latch.
6. The Worker serves published `/rankings` and `/weeks` from static JSON. The container fetch uses the fixed origin `https://api.internal` plus the canonical path. Flask serves matchup, team pages, and `/agent/explain`.

`POST /api/spend/kill` is authorized with `SPEND_KILL_SECRET` from header `X-Spend-Kill-Secret` only. Unset, the route returns 403 and does not fall back to `CACHE_CLEAR_SECRET`. The secret stays on the Worker. DevSecOps provisions on Michael's yes (ruling D-20261019-174).

`POST /cache/clear` reads `CACHE_CLEAR_SECRET` from header `X-Cache-Secret` only and compares it with `hmac.compare_digest`. A `secret` query parameter is not forwarded to the container.

## Paid-call caps

Production `AI_MODE=live` (Workers AI) and `CFBD_OFFLINE=1`. Preview hostnames stay stub and offline unless `PREVIEW_AI_MODE` / `PREVIEW_CFBD_OFFLINE` are set.

| Control | Default |
|---|---|
| xAI | Hard 0 calls and off. Weekly dollar cap 0. |
| Workers AI | 100 calls/day, including when `AI_MAX_CALLS` is higher. Model `@cf/meta/llama-3.1-8b-instruct-fp8`. 80 output tokens, 4000 input characters, 58 Neurons per call, ceiling 8000. |
| CFBD | 4 live calls/day in production (code fallback 25). Provider `cfbd`, source `app`. |
| Visitor limits | 60/min on `/api/*`, 10/min on `/agent/*`, keyed on `CF-Connecting-IP`. The canonical path only picks which limiter. |
| Kill switches | `AI_KILL`, `XAI_KILL`, `WORKERS_AI_KILL`, and `CFBD_KILL` default off. A stored Durable Object latch still blocks the call after the env var is cleared. |

## Already-counted headers

`x-workers-ai-reserved` and `x-xai-week-reserved` mean the container already reserved that paid call on SpendBudget. The outbound handlers trust them only on the container's request to `ai.workers` and `ai.xai`. The edge deletes both headers from visitor requests before the container fetch, so a visitor cannot plant them.
