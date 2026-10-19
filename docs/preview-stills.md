# Preview stills

Pull requests run [`.github/workflows/preview-stills.yml`](../.github/workflows/preview-stills.yml). The job has no secrets. It builds `frontend/`, serves that build on `127.0.0.1` with the offline fixtures in `design/comps/api/`, and captures each manifest route at **390×844** and **1440×900**.

A route **passes** only when a signed comp is within the pixel threshold. A route with no signed comp is **no comps**. That is a warning, not a pass. If every route is no comps, the job summary says the run is not a pass.

The job **fails** when:

- a signed comp differs by more than the max diff ratio (pixelmatch, not a selector check)
- the page requests `/api/agent/*`
- the page requests any origin other than the capture server
- Chrome's major version is not the pin in `scripts/visual/lib/visual-rules.mjs`

Chrome is launched with Playwright's sandbox left on. The workflow does not call a Workers preview. Preview versions of this Worker use production `AI_MODE`.

## Run locally

Chrome major **154** and Node 22:

```bash
npm ci --prefix scripts/visual
node scripts/visual/test-visual.mjs
npm ci --prefix frontend && npm run build --prefix frontend
node scripts/visual/visual-check.mjs \
  --build frontend/build \
  --manifest design/comps/manifest.json \
  --out preview-stills-out
```

`npm run test:visual` from the repo root runs the same self-test. The self-test plants three cases:

- `design/comps/planted/match.html` and `mismatch.html` share the same `data-check` elements and the same title text. The mismatch shifts and recolors a block. The gate must exit 1 on pixels.
- `nocomp.html` is reported as `no comps`.
- `offsite.html` calls `/api/agent/explain` and `https://api.collegefootballdata.com`. The gate must exit 1, and the fixture server must see zero `/api/agent` hits.

To fail a job the way the planted mismatch fails the gate:

```bash
node scripts/visual/test-visual.mjs --fail-job-on-planted-mismatch
```

That exits with the gate's status (1) after the proof.

## Add a comp

1. Capture unsigned stills. This does not sign anything:

   ```bash
   node scripts/visual/visual-check.mjs --build frontend/build --capture-only --out /tmp/stills
   ```

2. Review the PNG. Copy the one you are signing to `design/comps/renders/<route>-<width>.png`.
3. Record the checksum: `sha256sum design/comps/renders/<route>-<width>.png`.
4. Add an entry to `design/comps/manifest.json` `comps`:

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

`file` is relative to the manifest. `..` and absolute paths are ignored. A comp is signed only when the sha256 matches, `signed_by` is set, and `signoff` is an `https://github.com/merimeesoftware/cfb-ranking-algorithm/` URL (the design seat's sign-off comment). A file that is not listed, or whose hash does not match, is **no comps**, never a pass.

Sign-off belongs to the CFB design seat (`owner:dean-cfb`).

## Threshold and masks

Defaults (also the caps): pixelmatch `0.1`, max diff ratio `0.002` (0.2% of viewport pixels). The manifest cannot raise either past `0.2` / `0.02`.

`masks` is an optional list of `{ "x", "y", "width", "height" }` rectangles in viewport pixels. Those rectangles are painted the same color in both images before the diff, for a region that is allowed to move (a clock, a live count). Do not mask the part of the page the comp is meant to lock.

Stills freeze CSS animation and force the light theme before the screenshot. Sign comps from this command, not from a desktop screenshot.

## Offline API

`/` asks the client for the current week. The capture server answers `/api/rankings` and `/api/weeks` from `design/comps/api/rankings.json` and never forwards them. The fixture board is fixed on 2024 week 15 (four teams) so the still does not follow the calendar. A signed comp of `/` is that fixture board. `/2024/week/15` is the prerendered static week and does not call `/api/rankings`. Logo URLs on `cdn.collegefootballdata.com` and the Google Fonts stylesheets in the built HTML are rewritten to same-origin resources before the browser sees them. Any other off-site request still fails the run.

## Workers preview

`--url` exists for a later check against an allowlisted `*.true-rankings-cfb.merimeesoftware.workers.dev` host. It requires `--sha` and a `/build.json` whose `sha` matches. CI does not pass `--url`. Do not point stills at a preview until preview URLs are confirmed on this issue; those versions use production `AI_MODE`.
