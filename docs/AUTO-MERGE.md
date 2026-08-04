# Auto-merge and AI review setup

One-time GitHub and Cursor configuration for this repo. The workflows are already in `.github/workflows/`.

## 1. Enable GitHub auto-merge

Repo → **Settings → General → Pull Requests**:

- [x] **Allow auto-merge**
- [x] **Automatically delete head branches** (recommended)

## 2. Branch protection on `main`

Repo → **Settings → Branches → Add rule** for `main`:

| Setting | Value |
|---------|-------|
| Require status checks | **Python**, **Frontend** |
| Require pull request reviews | **1** (for human/agent feature PRs) |
| Require review from Code Owners | off (unless you use CODEOWNERS) |

**Dependabot PRs:** if you require approving reviews, the built-in `GITHUB_TOKEN` cannot approve them. Options:

- **Simplest:** set required approving reviews to **0** and rely on CI checks only (Dependabot auto-merge works as-is).
- **Stricter:** add a PAT as `DEPENDABOT_AUTOMERGE_TOKEN` and extend the workflow to approve with that token (only if you need CODEOWNERS satisfied).

**Optional — Bugbot as a gate for feature PRs:** add required check **Cursor Bugbot** once Bugbot is enabled (see below). Do **not** require it for Dependabot-only flows if you want zero AI cost on dependency PRs.

## 3. What runs automatically

| PR type | Workflow | Merge when |
|---------|----------|------------|
| Dependabot (patch/minor/grouped) | `dependabot-automerge.yml` | Python + Frontend CI green |
| Dependabot (major) | — | Manual review |
| Feature PR with `automerge` label | `automerge.yml` | All required checks green |

Grouped Dependabot PRs have no semver `update-type`; they are treated as safe to auto-merge (group config is minor/patch only).

## 4. Cursor Bugbot (recommended AI review)

**Economics vs Copilot:** Bugbot is ~**$1–1.50 per review run** (usage-based). Copilot code review is bundled with Copilot subscription but uses AI credits and Actions minutes. For a low-volume repo like this, Bugbot with cost controls is usually cheaper than running a Cloud Agent per PR.

**Cost-saving Bugbot settings** ([Bugbot automations](https://cursor.com/automations/from-cursor/bugbot)):

1. Connect GitHub at [cursor.com/dashboard/integrations](https://cursor.com/dashboard/integrations)
2. Enable Bugbot for this repo
3. Turn on **Only once per PR** (skip re-review on every push)
4. Turn on **Incremental review** when available
5. Use **Default** effort level (not High)
6. Leave **Autofix off** unless you want extra Cloud Agent spend

Repo context for reviews: `.cursor/BUGBOT.md` (already in this repo).

**Suggested split:**

- **Dependabot PRs** → CI only, no Bugbot (saves ~$1–1.50 × 3/month)
- **Feature PRs** → Bugbot once, you review comments, merge manually or add `automerge` label after approval

## 5. Opt-in auto-merge for your PRs

After CI passes and you are happy with Bugbot/human review:

```
gh pr edit <number> --add-label automerge
```

Or add the label in the GitHub UI. The PR merges automatically once all required checks pass.

## 6. Enable on-demand usage (Bugbot billing)

Individuals: Bugbot uses included usage first, then on-demand. Teams: on-demand pool. Set spend limits at [cursor.com/dashboard/spending](https://cursor.com/dashboard/spending).
