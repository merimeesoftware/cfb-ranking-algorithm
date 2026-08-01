---
on:
  pull_request:
    types: [opened, synchronize, reopened]
  schedule:
    - cron: "0 16 * * 1"
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
  pull-requests: write
---

Run ranking regression validation:

1. Ensure CFBD_API_KEY is available in the environment
2. Start or connect to the Flask API (./venv/bin/python app.py on port 5001, or use deployed API_URL if set)
3. Fetch GET /rankings?year=2024&week=10
4. Validate response schema: team_rankings and conference_rankings arrays present
5. Verify top 10 teams have team_name, final_ranking_score, team_quality_score
6. Compare against any cached baseline in .cache/ if present; flag rank changes > 3 positions

Post a PR comment with:
- Pass/Fail status
- Top 10 teams list
- Any schema violations or stability warnings
- Response time in seconds

Do not modify application code unless a critical regression is found and explicitly documented.
