/**
 * Ranking QA workflow — validates /rankings response schema and top-10 stability.
 * Run: opencode run --workflow ranking-qa
 */
import { workflow } from "@opencode-ai/plugin/workflow";

export default workflow({
  name: "ranking-qa",
  description: "Fetch /rankings, validate schema, compare top-10 stability",
  args: {
    year: { type: "number", default: 2024 },
    week: { type: "number", default: 10 },
    api_url: { type: "string", default: "http://localhost:5001" },
  },
  async run(ctx) {
    const { year, week, api_url } = ctx.args;

    await ctx.agent({
      name: "fetch-rankings",
      prompt: `Fetch GET ${api_url}/rankings?year=${year}&week=${week} and validate:
1. Response is JSON with team_rankings and conference_rankings arrays
2. Each team has team_name, final_ranking_score, team_quality_score
3. Top 10 teams are listed with ranks 1-10
4. Report any schema violations or missing fields
Return a structured JSON report with status (pass/fail), top10, and issues.`,
      schema: {
        type: "object",
        properties: {
          status: { type: "string" },
          top10: { type: "array" },
          issues: { type: "array" },
        },
        required: ["status", "top10", "issues"],
      },
    });

    await ctx.agent({
      name: "stability-check",
      prompt: `If a prior rankings snapshot exists in .cache/, compare top-10 team names
for year=${year} week=${week}. Report any rank changes > 3 positions.
If no prior snapshot, note that baseline will be established on next run.`,
    });

    ctx.log("Ranking QA workflow complete");
  },
});
