# Preview stills

Pull requests run [`.github/workflows/preview-stills.yml`](../.github/workflows/preview-stills.yml). The job has no secrets. It builds `frontend/`, serves that build on `127.0.0.1` with the offline fixtures in `design/comps/api/`, and captures each manifest route at **390×844** and **1440×900**.

The workflow grants `contents: read` only. It does not grant `actions: write`. Both checkouts set `persist-credentials: false`, so the job does not leave a token in `.git/config`. Actions are pinned to a full commit SHA:

- `actions/checkout` `3d3c42e5aac5ba805825da76410c181273ba90b1` (v7.0.1)
- `actions/setup-node` `949feb2413d6458794dcd2491c4babbbce0c15c1` (v7.1.0)
- `actions/upload-artifact` `cf430e030ddbb5b0abf93d22962f4752f3646cd9` (v7.0.2)

`actions/upload-artifact` v7 publishes the stills with `contents: read`. The npm cache is not saved, because saving a cache needs `actions: write`.

## What the job trusts

The job checks out the pull request, then checks out `github.event.pull_request.base.sha` into `base-comps`. `ci-stills.mjs` reads `design/comps/manifest.json` and the PNGs under `design/comps/renders/` from that base tree only. A signature added on the pull request head is ignored. The pull request that adds a signature does not get credit until that signature is on the base branch.

Until the base SHA contains `design/comps/manifest.json`, the job writes a bootstrap manifest with `/`, `/methodology`, and `/2024/week/15` and an empty `comps` array. It does not copy the pull request's manifest. That bootstrap has zero signed comps.

Chrome is launched with Playwright's sandbox left on. The workflow does not call a Workers preview. Preview versions of this Worker use production `AI_MODE`.

## Exit codes

`visual-check.mjs` exits:

| Code | Meaning |
| --- | --- |
| 0 | Pass. Every captured route matched a signed comp. |
| 1 | Fail. Pixels differ, the request guard tripped, HTTP or capture failed, a mask covers more than 10% of the viewport, or a comp path resolves outside `design/comps/renders/`. |
| 2 | Bad input. |
| 3 | No comps. The route has no entry, the sha256 does not match, `signed_by` or `signoff` is missing, or the run was `--capture-only`. |

Exit 3 is not a pass. The self-test asserts exit 3 exactly for the missing-comp fixture and the bad-hash fixture.

`ci-stills.mjs` is what CI runs for the app build. It turns checker exit 3 into process exit 0 only while the trusted manifest has zero signed comps, and it prints that bootstrap state in the log and the job summary. Once any comp on the base manifest is signed, a no-comps route stays exit 3 and fails the job. A pixel failure, a guard failure, an oversized mask, or a path escape stays exit 1 even during bootstrap.

## Run locally

Chrome major **154** and Node 22:

```bash
npm ci --prefix scripts/visual
node scripts/visual/test-visual.mjs
npm ci --prefix frontend && npm run build --prefix frontend
node scripts/visual/ci-stills.mjs \
  --build frontend/build \
  --base . \
  --out preview-stills-out
```

`--manifest` is a local preview of a manifest file. CI does not pass it. `--base` is a checkout of the trusted tree; the checker reads `<base>/design/comps/manifest.json` and nothing from the pull request head.

`npm run test:visual` from the repo root runs the self-test. The self-test plants these cases and prints each exit code:

- `design/comps/planted/match.html` and `mismatch.html` share the same `data-check` elements and the same title text. The mismatch shifts and recolors a block. The gate exits 1 on pixels.
- `nocomp.html` with an empty `comps` array exits 3.
- A signed entry whose sha256 does not match the file exits 3.
- A second tree with a well-formed signature is ignored when `--base` points at a manifest with zero comps. That run exits 3.
- `ci-stills.mjs` on that same base exits 0 and prints the bootstrap line. The same wrapper exits 3 when the manifest has a signed comp and another route is no comps.
- A mask that covers the whole viewport exits 1 before pixelmatch.
- A `renders/../../` path and a symlink whose realpath leaves `design/comps/renders/` exit 1.
- `offsite.html` calls `/api/agent/explain`, `https://api.collegefootballdata.com`, and a same-host WebSocket. The gate exits 1. The fixture server sees zero `/api/agent` hits.

```bash
node scripts/visual/test-visual.mjs --fail-job-on-planted-mismatch
```

That exits with the planted mismatch status (1) after the proofs.

## Add a comp

1. Capture unsigned stills. This does not sign anything:

   ```bash
   node scripts/visual/visual-check.mjs --build frontend/build --capture-only --out /tmp/stills
   ```

2. Review the PNG. Copy the one you are signing to `design/comps/renders/<route>-<width>.png`.
3. Record the checksum: `sha256sum design/comps/renders/<route>-<width>.png`.
4. Add an entry to `design/comps/manifest.json` `comps` on the base branch:

   ```json
   {
     "route": "/",
     "width": "390",
     "file": "renders/home-390.png",
     "sha256": "<sha256sum>",
     "signed_by": "owner:dean-cfb",
     "signoff": "https://github.com/merimeesoftware/cfb-ranking-algorithm/issues/<n>#issuecomment-<id>",
     "masks": []
   }
   ```

`file` is relative to the manifest directory. The checker resolves it with `realpath` and fails the run when the file lands outside `design/comps/renders/`. Absolute paths, `..`, and symlinks that leave that directory are failures (exit 1), not unsigned comps. A missing file inside `renders/` is no comps (exit 3).

A comp is signed only when the sha256 matches, `signed_by` is set, and `signoff` is an `https://github.com/merimeesoftware/cfb-ranking-algorithm/` URL (the design seat's sign-off comment). A file that is not listed, or whose hash does not match, is **no comps**, never a pass.

Sign-off belongs to the CFB design seat (`owner:dean-cfb`). Putting the entry on a pull request does not sign the comp for that pull request. CI keeps reading the base SHA until the entry is merged.

## Threshold and masks

Defaults (also the caps): pixelmatch `0.1`, max diff ratio `0.002` (0.2% of viewport pixels). The manifest cannot raise either past `0.2` / `0.02`.

`masks` is an optional list of `{ "x", "y", "width", "height" }` rectangles in viewport pixels. Those rectangles are painted the same color in both images before the diff, for a region that is allowed to move (a clock, a live count). The sum of the rectangle areas may not exceed **10%** of the viewport. A larger total fails the still before pixelmatch, so a mask cannot hide a whole page.

Stills freeze CSS animation and force the light theme before the screenshot. Sign comps from this command, not from a desktop screenshot.

## Request guard

Capture uses `browserContext.route` for every request, `serviceWorkers: 'block'` on the context, and `routeWebSocket` to deny sockets. A socket is closed in the handler and is not connected upstream. `/api/agent` (with or without a suffix) and any other origin fail the run. `data:`, `blob:`, and `about:` URLs are not network.

## Offline API

`/` asks the client for the current week. The capture server answers `/api/rankings` and `/api/weeks` from `design/comps/api/rankings.json` and never forwards them. The fixture board is fixed on 2024 week 15 (four teams) so the still does not follow the calendar. A signed comp of `/` is that fixture board. `/2024/week/15` is the prerendered static week and does not call `/api/rankings`. Logo URLs on `cdn.collegefootballdata.com` and the Google Fonts stylesheets in the built HTML are rewritten to same-origin resources before the browser sees them. Any other off-site request still fails the run.

## Workers preview

`--url` exists for a later check against an allowlisted preview host. It requires `--sha` and a `/build.json` whose `sha` matches. CI does not pass `--url`. Do not point stills at a preview until preview URLs are confirmed on this issue; those versions use production `AI_MODE`.
