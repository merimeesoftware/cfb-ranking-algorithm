/**
 * CFBD API audit workflow — traces cache misses and counts API calls per request.
 * Run: opencode run --workflow cfbd-audit
 */
import { workflow } from "@opencode-ai/plugin/workflow";

export default workflow({
  name: "cfbd-audit",
  description: "Trace cache misses, count CFBD calls, report optimization targets",
  args: {
    year: { type: "number", default: 2024 },
    week: { type: "number", default: 10 },
  },
  async run(ctx) {
    await ctx.parallel([
      () =>
        ctx.agent({
          name: "cache-stats",
          prompt: `Read cache.py and app.py. Summarize:
- Cache layers (memory, file, computed rankings)
- TTL values per data type
- Known bug: invalidate_prefix() with MD5 keys
- Estimated CFBD calls on /rankings cache miss (~8)`,
        }),
      () =>
        ctx.agent({
          name: "api-patterns",
          prompt: `Analyze api_integration.py and data_processor.py:
- Which CFBD endpoints are called
- Whether week param is passed to get_games()
- Whether priors are recomputed on every cache miss
- Whether cfbd SDK in requirements.txt is used
Return optimization priority list.`,
        }),
    ]);

    await ctx.agent({
      name: "mcp-evaluation",
      prompt: `Evaluate CFBD MCP servers (lenwood/cfbd-mcp-server, gedin-eth/cfb-mcp) vs direct REST:
- Batch ranking pipeline: keep REST
- Agent chat queries: adopt MCP
- CI validation: keep REST
Write recommendation matrix.`,
    });

    ctx.log("CFBD audit workflow complete");
  },
});
