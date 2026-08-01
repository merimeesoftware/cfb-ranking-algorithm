---
on:
  schedule:
    - cron: "0 14 * * 6"
permissions:
  contents: read
---

Warm the rankings cache for the current CFB season and week.

Steps:
1. Determine current season year and week (Aug-Dec: in-season; Jan-Jul: previous year week 15)
2. Call GET ${API_URL:-http://localhost:5001}/rankings with year and week params
3. Log response status and top 3 teams
4. Call GET /cache/stats and log cache entry counts

This reduces cold-start latency for weekend traffic. Requires CFBD_API_KEY and a running API (set API_URL secret for deployed environments).
