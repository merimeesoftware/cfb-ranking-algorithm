/**
 * Deploy smoke test workflow — hits health and rankings endpoints post-deploy.
 * Run: opencode run --workflow deploy-smoke
 */
import { workflow } from "@opencode-ai/plugin/workflow";

export default workflow({
  name: "deploy-smoke",
  description: "Hit health + rankings endpoints post-deploy",
  args: {
    api_url: {
      type: "string",
      default: process.env.API_URL || "http://localhost:5001",
    },
    year: { type: "number", default: 2024 },
    week: { type: "number", default: 10 },
  },
  async run(ctx) {
    const { api_url, year, week } = ctx.args;

    await ctx.agent({
      name: "health-check",
      prompt: `Run curl -sf ${api_url}/ and verify JSON response with message "CFB Ranking API is running".
Report status code and response body. Fail if non-200.`,
    });

    await ctx.agent({
      name: "rankings-check",
      prompt: `Run curl -sf "${api_url}/rankings?year=${year}&week=${week}" with a 120s timeout.
Verify 200 response with team_rankings array length > 0.
Report response time and top 3 teams.`,
    });

    await ctx.agent({
      name: "cache-stats-check",
      prompt: `Run curl -sf ${api_url}/cache/stats and verify memory_entries and file_entries fields exist.`,
    });

    ctx.log("Deploy smoke test complete");
  },
});
