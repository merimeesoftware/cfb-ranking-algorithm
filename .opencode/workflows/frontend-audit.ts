/**
 * Frontend audit workflow — runs svelte-check and Impeccable-style quality checks.
 * Run: opencode run --workflow frontend-audit
 */
import { workflow } from "@opencode-ai/plugin/workflow";

export default workflow({
  name: "frontend-audit",
  description: "Run npm run check and frontend quality audit",
  args: {
    fix: { type: "boolean", default: false },
  },
  async run(ctx) {
    await ctx.pipeline([
      () =>
        ctx.agent({
          name: "typecheck",
          prompt: `Run: cd frontend && npm run check
Report any TypeScript/svelte-check errors. Do not fix unless fix=true.`,
        }),
      () =>
        ctx.agent({
          name: "api-layer-audit",
          prompt: `Audit frontend/src/lib/stores/rankings.ts and frontend/src/lib/api.ts:
- Is VITE_API_URL used correctly?
- Duplicate API layers?
- Missing /weeks endpoint usage?
- URL query params for year/week?
- Client-side cache/SWR?
Return prioritized backlog.`,
        }),
      () =>
        ctx.agent({
          name: "ux-audit",
          prompt: `Review frontend components for:
- Accessibility (contrast, focus states, aria labels)
- Mobile responsiveness
- Loading/error states
- Broken links (e.g. /about in Footer)
- Bundle size concerns (lazy loading modals)
Apply Impeccable design principles: avoid generic AI patterns, ensure interaction states.`,
        }),
    ]);

    ctx.log("Frontend audit workflow complete");
  },
});
