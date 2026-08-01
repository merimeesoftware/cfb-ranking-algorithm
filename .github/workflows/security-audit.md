---
on:
  schedule:
    - cron: "0 12 * * 6"
engine: opencode
imports:
  - sst/opencode/.github/workflows/opencode-engine.md@v1.2.14
network:
  allowed:
    - defaults
    - api.minimax.io
    - api.collegefootballdata.com
permissions:
  contents: read
  issues: write
---

Perform weekly security audit:

1. Review latest CI artifacts for Bandit (bandit-report.json) and pip-audit results
2. Review npm audit output from scan-frontend job
3. Check for:
   - Open /cache/clear without CACHE_CLEAR_SECRET
   - CORS origins=["*"] in app.py
   - Hardcoded API URLs in frontend
   - Missing rate limiting on /rankings
4. Summarize findings by severity (critical/high/medium/low)
5. Create or update a security audit issue titled "Weekly Security Audit — {date}"

Do not auto-fix code; report findings only.
