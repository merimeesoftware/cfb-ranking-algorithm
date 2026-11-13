# Committee source

Legal log D-20261112-15. Issue #174. The conditions below are copied as written. This change does not add a public table, route, or render.

1. The source of record is hand entry from the official weekly CFP release. Store only rank, team name, optional record and release date. No scraping, no release text or images, no raw CFBD JSON. The plan currently says CFBD GET /rankings; change it. CFBD is allowed only for test fixtures or a backfill, checked against the official list, and the published table is still cited to the CFP.
2. Plain-text CFP references only. No CFP or school logos, no official styling, no 'official' or 'endorsed' wording. Rename our own 'CFP Playoff (1-12)' legend before the committee column ships, and give Phil a copy slot for the new name.
3. Non-commercial for now.
Attribution line, exact: 'CFP selection committee ranking, released [DATE]. Source: collegefootballplayoff.com. Not affiliated with or endorsed by the College Football Playoff.'

## Stored rows

The ingest no longer uses CFBD GET /rankings as the source of record.

A committee file is a JSON list at `frontend/static/rankings/committee/{year}.json` when a later hand entry adds one. Each object stores `release_date`, `rank`, and `team_name`. `record` may be omitted. No other field is stored. Files do not carry `algo` or `ALGO_VERSION`. They are not named `week-N.json`, they are not listed in `manifest.json`, and they are not served from `/rankings/{year}/week-{week}.json`.

This PR commits fixtures under `tests/fixtures/committee/` only. It does not add a file under `frontend/static/rankings/committee/`. Names and dates in the fixture are examples, not a republished ranking. 2025 is refused.

## CFBD

A CFBD payload is not a committee file. The validator rejects it. A backfill may compare one CFBD fixture to the hand-entered rows for a single release and, when rank and team name match, keep the hand-entered rows. The comparison does not call CFBD. Week numbers are not stored and are not the join key.

## Citation

When a table is allowed, it uses this line, with `[DATE]` replaced by that release's date:

`CFP selection committee ranking, released [DATE]. Source: collegefootballplayoff.com. Not affiliated with or endorsed by the College Football Playoff.`

The line is not a fifth stored field.

## Use

Non-commercial for now.

## Phil copy slot

The gold-band legend rendered today is `CFP Playoff (1-12)`. Phil writes the new name in the empty cell. `frontend/src/lib/components/RankingsTable.svelte` stays as it is until that cell is filled and the committee column ships. The same empty cell is in `docs/design/phil-copy-table.md`.

| Slot | Rendered today | New name |
| --- | --- | --- |
| Gold 1-12 legend | CFP Playoff (1-12) | |
