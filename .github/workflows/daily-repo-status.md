---
on:
  schedule:
    - cron: "0 14 * * *"
engine: opencode
imports:
  - sst/opencode/.github/workflows/opencode-engine.md@v1.2.14
network:
  allowed:
    - defaults
    - api.minimax.io
permissions:
  contents: read
  issues: write
---

Summarize the repository status for today:

1. List open issues and their labels
2. List recent pull requests (last 7 days) and their CI status
3. Note any failing CI checks on main
4. Highlight ranking-related changes in the last week

Create a concise daily status issue titled "Daily Repo Status — {date}" with sections for Issues, PRs, CI Health, and Notable Changes. Do not modify code.
