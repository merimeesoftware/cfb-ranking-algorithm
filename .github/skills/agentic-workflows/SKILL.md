# GitHub Agentic Workflows dispatcher skill
# Generated for gh-aw SDLC integration

When creating or editing agentic workflows in `.github/workflows/*.md`:

1. Use YAML frontmatter with `on`, `engine`, `imports`, `network`, and `permissions`
2. Set `engine: opencode` with MiniMax via `sst/opencode/.github/workflows/opencode-engine.md`
3. Add `api.minimax.io` to `network.allowed` when using MiniMax
4. Compile with `gh aw compile` before committing
5. Commit both `.md` source and generated `.lock.yml` files

Required secrets: `CFBD_API_KEY` (repo + Cursor). Optional: `MINIMAX_API_KEY` (Cursor Secrets tab). Cloudflare deploy uses Git integration — no Cloudflare tokens in GitHub. See `docs/DEPLOY-CLOUDFLARE.md`.
