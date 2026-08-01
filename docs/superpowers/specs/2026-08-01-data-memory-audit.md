# CFB Ranking System — Data, Storage & Memory Audit

**Date:** 2026-08-01  
**Scope:** `cache.py`, `api_integration.py`, `data_processor.py`, `app.py` (+ supporting deployment context)  
**Purpose:** Inventory data flows, evaluate cache architecture, identify memory/multi-worker gaps, and define a Cloudflare migration path.

---

## Executive Summary

The CFB Ranking System uses a **two-tier cache** (in-process memory + pluggable persistence) to amortize expensive CFBD API calls and iterative ranking computation. The design is sound for single-process local dev but has **production gaps**:

| Area | Status | Risk |
|------|--------|------|
| CFBD game/team caching | Working | Medium — prefix index not populated |
| Computed rankings cache | Working | Medium — no prefix registration, 30m TTL only |
| Priors precompute | **Not cached** | **High** — 3 full historical ranking runs per cold miss |
| Multi-worker (gunicorn) | Per-worker memory | High — duplicate compute unless file/R2 hit |
| `invalidate_prefix` | Implemented, unused | Medium — selective bust impossible today |
| Stale-while-revalidate | **Absent** | Medium — hard expiry causes latency spikes |
| R2 backend | Partial | Medium — dual-write, local-only prefix index |
| `TTL_PRIORS` | **Defined, never used** | High — dead constant signals incomplete work |

Production runs on **Render** via `gunicorn app:app` (`render.yaml`) and is migrating toward **Cloudflare Containers** with `CACHE_BACKEND=r2` (`deploy-cloudflare.yml`).

---

## 1. Data Inventory

### 1.1 External Sources (CFBD API)

All HTTP traffic flows through `CFBDApiClient` (`api_integration.py`) against `https://api.collegefootballdata.com`.

| Endpoint | Method | Parameters | Used By | Cached? |
|----------|--------|------------|---------|---------|
| `/games` | `get_games()` | `year`, optional `week`, `seasonType` | `CFBDataProcessor.get_games_for_season()` | Yes |
| `/teams/fbs` | `get_team_info()` | — | **No active caller in app path** | Yes |
| `/teams` | `get_teams_with_logos()` | — | `CFBDataProcessor._initialize_conference_map()` | Yes |
| `/rankings` | `get_rankings()` | `year`, optional `week` | **No active caller in app.py/main ranking path** | Yes |
| `/lines` | `get_betting_lines()` | `year`, optional `week`, `seasonType=regular` | `main.py` (ATS mode only) | Yes |

**Startup behavior:** `app.py` instantiates `CFBDataProcessor` at import time, which immediately calls `get_teams_with_logos()` — one CFBD round-trip (or cache hit) per worker process on boot.

### 1.1.1 Fetch Patterns for `/rankings`

A typical cold `GET /rankings?year=2024&week=10` triggers:

```
Current season games (regular + postseason)     → 2 API calls (or cache hits)
Historical priors (Y-1, Y-2, Y-3)             → 3 × 2 = 6 API calls (or cache hits)
                                              → 3 full ranking algorithm runs (never cached)
Iterative solver (2 iterations)               → CPU-only, in-memory
Response enrichment (logos, FCS records)    → uses in-memory team_info_map
```

On a **cache miss** for computed rankings, wall-clock time is dominated by priors + solver, not raw API latency (assuming games are warm).

### 1.2 Transformations

#### API layer (`api_integration.py`)

| Step | Input | Output | Discarded |
|------|-------|--------|-----------|
| `_is_valid_game()` filter | Raw CFBD game dict | — | Games missing scores or team names |
| `_transform_game()` | Valid CFBD game | Internal game dict (`home_team_name`, `away_team_name`, scores, conferences, venue, date) | Original CFBD field names |
| `get_team_info()` | `/teams/fbs` list | `{school: conference}` | IDs, logos, colors |
| `get_teams_with_logos()` | `/teams` list | `{school: {id, conference, mascot, colors, logos, ...}}` | Non-FBS teams still stored |

#### Data processor (`data_processor.py`)

| Step | Input | Output | Discarded |
|------|-------|--------|-----------|
| `get_games_for_season()` | Transformed games | Merged regular + postseason list | — |
| Week filter (`through_week`) | Full season games | Subset ≤ week | Games after cutoff |
| `_process_raw_games()` | Raw/transformed games | Games + `home/away_conference_type` (Power 4 / Group of 5 / FCS) | Games failing validation |
| `filter_games(include_fcs=False)` | Processed games | FBS-only matchups | FCS-involved games |
| `enrich_games_with_betting_lines()` | Games + lines | Games with optional `spread_info` | Unmatched lines |
| `organize_games_by_week()` | Game list | `{week: [games]}` | — |

#### Ranking layer (`app.py` → `ranking_algorithm.py`)

| Step | Input | Output | Discarded |
|------|-------|--------|-----------|
| Historical prior runs | 3 prior seasons of games | Per-year `calculate_final_rankings()` results | Intermediate ranker state |
| `calculate_priors()` | History results (Y-1, Y-2 weighted) | `{team_name: prior_score}` | `history_data` list |
| Iterative solver (2×) | Games by week + priors + config | Converged team/conference scores | Per-iteration temp results (except reference ranks) |
| `normalize_scores()` | Raw rankings | 0–100 normalized scores | — |
| Logo/color enrichment | `team_info_map` | Rankings with `logo`, `color`, etc. | — |
| FCS record aggregation | `ranker.team_stats` | Conference-level FCS W-L | — |
| FBS filter (`all_divisions=false`) | Full rankings | FBS-only team list | FCS teams in response |

### 1.3 Stored Artifacts

| Artifact | Location | Key Scheme | TTL | Size Estimate |
|----------|----------|------------|-----|---------------|
| Transformed games | `.cache/{md5}.json` or R2 `cache/{md5}.json` | `md5("games:(year, week, season_type):{}")` | 1h (current) / 7d (historical) | 50–500 KB/season |
| Team info (logos) | Same | `md5("teams_with_logos:():{}")` | 24h | ~200 KB |
| Team conferences (FBS) | Same | `md5("team_info:():{}")` | 24h | ~10 KB |
| CFBD poll rankings | Same | `md5("rankings:(year, week):{}")` | Same as games TTL | Variable |
| Betting lines | Same | `md5("betting_lines:(year, week):{}")` | Same as games TTL | Variable |
| **Computed rankings** | Same | `md5("rankings_computed:():sorted kwargs")` | 30m | 100 KB–2 MB |
| Prefix index | `.cache/_index.json` (local only) | `{prefix: [key, ...]}` | Persistent | Small |
| In-process memory | `_memory_cache` dict | Same MD5 keys | Per-entry `expires_at` | Duplicates hot entries |

### 1.4 Discarded / Never Persisted

- Raw CFBD JSON after transformation and cache write
- **Priors dict** — recomputed every rankings cache miss
- **Historical season ranking runs** (Y-1, Y-2, Y-3) — recomputed every miss
- Ranker internal state (`team_stats`, weekly scores) — ephemeral per request
- `/rankings/team/<name>` response — built on the fly, never cached
- Invalid/expired cache files — deleted on read (lazy expiry)

---

## 2. Cache Layer Analysis

### 2.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Request (Flask route / CFBDApiClient)                      │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Cache (singleton, thread-safe RLock)                       │
│  ┌─────────────────┐    ┌──────────────────────────────┐  │
│  │ _memory_cache   │───▶│ CacheBackend (pluggable)      │  │
│  │ Dict[key→entry] │◀───│ FileCacheBackend | R2Cache    │  │
│  └─────────────────┘    └──────────────────────────────┘  │
│  ┌─────────────────┐                                        │
│  │ _prefix_index   │  ← local _index.json only             │
│  └─────────────────┘                                        │
└─────────────────────────────────────────────────────────────┘
```

**Factory:** `create_cache_backend()` reads `CACHE_BACKEND` env (`file` default, `r2` optional).

**Entry shape (all layers):**

```json
{
  "data": <payload>,
  "expires_at": <unix timestamp>,
  "created_at": <unix timestamp>
}
```

### 2.2 Memory Layer (`Cache._memory_cache`)

| Property | Behavior |
|----------|----------|
| Scope | Process-local; not shared across gunicorn workers |
| Thread safety | `threading.RLock` on all operations |
| Read path | Memory → backend → repopulate memory |
| Write path | Memory + backend (write-through) |
| Eviction | Lazy — expired entries removed on `get()` |
| **Bug/gap** | On backend hit, memory repopulation uses hardcoded `TTL_RANKINGS` (30m) regardless of original TTL |

```python
# cache.py lines 190-195 — memory TTL not preserved from backend entry
self._memory_cache[key] = {
    'data': data,
    'expires_at': time.time() + TTL_RANKINGS,  # always 30m
}
```

**Impact:** A historical games entry cached for 7 days on disk may expire from memory after 30 minutes, causing unnecessary disk reads (minor) or inconsistent behavior if memory and disk diverge on custom TTLs.

### 2.3 File Layer (`FileCacheBackend`)

| Property | Value |
|----------|-------|
| Directory | `CACHE_DIR` env or `{repo}/.cache` |
| File naming | `{md5_key}.json` |
| Expiry | Checked on read; expired files deleted |
| Error handling | Corrupt files deleted silently |
| `clear_all()` | Deletes all `*.json` except `_index.json` |

**Strengths:** Simple, survives process restarts, shared across workers on same filesystem (Render persistent disk if mounted; otherwise ephemeral).

**Weaknesses:** No atomic writes (partial write on crash → corrupt entry deleted on next read); no size limits; prefix index separate from data files.

### 2.4 R2 Layer (`R2CacheBackend`)

| Property | Behavior |
|----------|----------|
| Activation | `CACHE_BACKEND=r2` + `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_ENDPOINT_URL`, `R2_BUCKET_NAME` |
| Read order | R2 → local file fallback |
| Write order | R2 + local file (dual-write) |
| Local dir | `/tmp/cfb-cache` (ephemeral on Containers) |
| Dependency | `boto3` (not in `requirements.txt` today) |

**Gaps:**

1. **Prefix index (`_index.json`) is never synced to R2** — `invalidate_prefix()` and `get_stats()` only work on local disk.
2. **Dual-write without read-repair** — R2 and local can diverge if one write fails.
3. **No listing/prefix scan on R2** — cannot rebuild index from R2 objects alone.
4. **`boto3` missing from requirements** — R2 silently falls back to local-only with a print statement.

### 2.5 Computed Rankings Cache

**Location:** `app.py` `GET /rankings`

**Cache key includes all ranking-affecting query params:**

```python
cache_params = {
    'year', 'week', 'all_divisions',
    'power_conf_initial', 'group5_initial', 'fcs_initial',
    'base_factor', 'team_quality_weight', 'conference_weight',
    'record_weight', 'prior_strength',
}
cache_key = cache._generate_key('rankings_computed', **cache_params)
```

| Property | Value |
|----------|-------|
| TTL | `TTL_RANKINGS` = 30 minutes |
| Prefix registration | **No** — `cache.set(cache_key, data, TTL_RANKINGS)` omits `prefix=` |
| Hit path | Returns cached JSON immediately |
| Miss path | Full `calculate_rankings_logic()` including priors |

**`/rankings/team/<team_name>` does not use this cache** — it always calls `calculate_rankings_logic()` directly, multiplying compute cost for team drill-down traffic.

### 2.6 Priors — Computed but Not Cached

`TTL_PRIORS = 7 * 24 * 60 * 60` is defined in `cache.py` but **never referenced**.

Priors computation in `app.py`:

```python
for h_year in range(year - 1, year - 4, -1):
    h_games = data_processor.get_games_for_season(h_year)  # cached games
    h_ranker = TeamQualityRanker(h_config)
    # ... process all weeks ...
    history_data.append(h_ranker.calculate_final_rankings())  # NOT cached

priors = TeamQualityRanker.calculate_priors(history_data)  # NOT cached
```

**Cost model (cache miss):**

| Step | Cached? | Relative Cost |
|------|---------|---------------|
| Fetch Y-1..Y-3 games | Yes (after first fetch) | Low (I/O) |
| Run ranking algorithm ×3 for history | **No** | **Very High (CPU)** |
| Blend priors | No | Trivial |
| Run iterative solver for target year | No | High (CPU) |

Priors for `(year)` depend only on historical game data and default config — **not** on request query params (weights, `all_divisions`). They are highly cacheable.

### 2.7 Prefix Index & `@cached` Decorator

The `Cache` class supports prefix-grouped invalidation via `_prefix_index` persisted to `_index.json`.

**Registration requires `prefix=` on `set()`:**

```python
cache.set(key, result, ttl, prefix=prefix)  # only in @cached decorator
```

**Current usage:**

| Caller | Passes `prefix=`? | Indexed? |
|--------|---------------------|----------|
| `api_integration.py` (all methods) | **No** | **No** |
| `app.py` computed rankings | **No** | **No** |
| `@cached` decorator | Yes | **Unused** — decorator not applied anywhere |

**`invalidate_prefix()` is dead code in practice** — nothing populates the index except the unused decorator.

**`get_stats()` undercounts:**

```python
file_count = len(prefix_index['games']) + len(prefix_index['rankings_computed'])
```

Most cache entries (teams, betting lines, unindexed games) are invisible to stats.

### 2.8 Historical vs Current Season TTL Logic

```python
def is_historical_season(year):
    # Past calendar years → historical
    # Current year before August → historical (offseason = prior season complete)
    # Current year Aug+ → current (in-season)

def get_games_ttl(year):
    return TTL_GAMES_HISTORICAL (7d) if historical else TTL_GAMES_CURRENT (1h)
```

This correctly treats completed seasons as immutable and current season as volatile. The same logic applies to CFBD poll rankings and betting lines caches.

---

## 3. Memory System Gaps

### 3.1 Gunicorn Multi-Worker Isolation

**Deployment:** `gunicorn app:app --bind 0.0.0.0:$PORT` (Render, CI validation).

Default gunicorn worker count is **1** unless `--workers N` is set. Each worker is a separate process with:

- Its own `Cache()` singleton and `_memory_cache`
- Its own `CFBDataProcessor` and `team_info_map` (~200 KB+)
- Its own cold-start CFBD fetch for teams on import

**Failure modes with multiple workers:**

| Scenario | Symptom |
|----------|---------|
| Worker A warms memory, Worker B serves next request | B misses memory → disk/R2 read (OK) or full recompute (if disk ephemeral) |
| Ephemeral filesystem (Cloudflare Containers `/tmp`) | Every worker restart = full cold path |
| Concurrent first request per worker | Thundering herd: N × priors computation + CFBD fetches |
| Memory cache repopulated with wrong TTL | Hot entries churn faster than intended |

**Recommendation:** Explicitly set `--workers 1` until shared cache is proven, or use shared R2/KV backend and accept memory duplication as a minor cost.

### 3.2 Priors Precompute Gap

**Problem:** The most expensive CPU work (3 historical full-season ranking runs) runs on every computed-rankings cache miss, even when historical game data is unchanged.

**Missing capabilities:**

- No `priors:{year}` cache key
- No `history_rankings:{year}` intermediate cache
- No background precomputation job (scheduled cache warm only hits `/rankings`, not isolated priors)
- No dependency chain: busting current-week games should bust current-week rankings but **not** historical priors

**Suggested key design:**

```
priors:v1:{target_year}           → Dict[str, float]     TTL 7d (or season-aware)
history_rankings:v1:{hist_year}   → ranking result dict  TTL 7d (immutable after season)
```

### 3.3 `invalidate_prefix` Non-Functional

Infrastructure exists but is not wired:

1. `api_integration.py` must pass `prefix='games'`, `prefix='teams'`, etc. on `cache.set()`
2. `app.py` must pass `prefix='rankings_computed'` on rankings cache write
3. Bust triggers needed: admin endpoint, post-weekend CFBD refresh, manual ops

**Example invalidation policy:**

| Event | Action |
|-------|--------|
| New week of games finalized | `invalidate_prefix('rankings_computed')` for current year only (needs finer granularity) |
| CFBD data correction | `invalidate_prefix('games')` + rankings |
| Algorithm version bump | `clear_all()` or versioned key prefix `rankings_computed:v5.1:` |

**Limitation:** Current prefix index is all-or-nothing per prefix — cannot invalidate `games` for `year=2024` only without key versioning or sub-prefix design.

### 3.4 Stale-While-Revalidate (SWR) Absent

Current behavior is **hard expiry**:

```
if expires_at <= now:
    delete entry
    return None  → full recomputation
```

**User-visible effect:** Every 30 minutes (rankings TTL) or 1 hour (current-week games), the next request pays full cold-start latency — potentially 30–120+ seconds for `/rankings`.

**Missing SWR pattern:**

```
if expired but within stale_window:
    return stale_data immediately
    trigger async refresh (background thread / queue)
elif expired beyond stale_window:
    blocking refresh
```

**Where SWR matters most:**

| Cache | Hard TTL | Suggested SWR |
|-------|----------|---------------|
| Computed rankings | 30m | Serve stale up to 2h; async refresh at 30m |
| Current-week games | 1h | Serve stale up to 6h during game days; refresh hourly |
| Historical games | 7d | SWR unnecessary (immutable) |
| Teams/logos | 24h | Serve stale up to 7d |

No background task runner, queue, or `threading` refresh exists today.

### 3.5 Additional Gaps

| Gap | Detail |
|-----|--------|
| `@cached` decorator unused | Duplicates manual cache logic in `api_integration.py` |
| `get_team_info()` orphaned | Cached but no caller — wasted index space if ever indexed |
| `get_rankings()` (CFBD polls) orphaned in app path | Cached API data never consumed by ranking algorithm |
| No cache size bounds | `.cache/` grows unbounded; no LRU eviction |
| No observability | `/cache/stats` undercounts; no hit/miss metrics, latency, or entry sizes |
| `CFBDataProcessor` at import | Fails fast on missing API key in dev; blocks worker boot |
| Team breakdown uncached | `/rankings/team/*` always triggers full pipeline |
| CI/cache warm | Scheduled warm (`cache-warm.md`) helps but doesn't isolate priors or use SWR |

---

## 4. Cloudflare Migration Plan

### 4.1 Target Architecture

```
┌──────────────────┐     ┌─────────────────────────────────────────┐
│ Cloudflare       │     │ Shared Storage                          │
│ Container        │     │                                         │
│ (gunicorn/flask) │────▶│ R2 Bucket: large JSON payloads          │
│ ephemeral /tmp   │     │   cache/games/{hash}.json                 │
└──────────────────┘     │   cache/rankings/{hash}.json              │
                         │   cache/priors/{year}.json                │
                         │                                         │
                         │ KV Namespace: metadata & indexes            │
                         │   idx:prefix:{name} → [keys]              │
                         │   meta:teams_with_logos → JSON (small)    │
                         │   version:algorithm → "v5.1"              │
                         └─────────────────────────────────────────┘
```

### 4.2 Pluggable Backend Design

Extend `CacheBackend` ABC with three implementations:

#### Phase 1 — Harden `R2CacheBackend` (exists today)

| Task | Detail |
|------|--------|
| Add `boto3` to `requirements.txt` | Required for production R2 |
| Structured keys | `cache/{prefix}/{key}.json` instead of flat `cache/{key}.json` |
| Single source of truth | R2 primary; local `/tmp` as optional L1 only |
| Read path | R2 → miss → CFBD/compute (skip unreliable local) |
| Conditional writes | Include `algorithm_version` in key to avoid cross-version pollution |

#### Phase 2 — `KVCacheBackend` for metadata

| Use Case | KV Key | Value | TTL |
|----------|--------|-------|-----|
| Prefix index | `idx:games` | JSON list of keys | None (explicit delete) |
| Prefix index | `idx:rankings_computed` | JSON list of keys | None |
| Team map | `teams_with_logos:v1` | Full team dict | 86400 |
| Priors | `priors:v1:{year}` | Prior dict | 604800 |
| Cache stats | `stats:hits` | Counter | — |

KV limits (256 KB/value) suit indexes and priors; **not** full season game lists — those stay in R2.

#### Phase 3 — `TieredCacheBackend` (composite)

```
get(key):
  1. memory (process L1)
  2. KV (if key in KV_ALLOWLIST)
  3. R2 (default persistence)
  4. miss

set(key, data, ttl, prefix):
  1. memory
  2. route by size/prefix → KV or R2
  3. update prefix index in KV
```

**Factory:**

```python
def create_cache_backend() -> CacheBackend:
    backend = os.environ.get('CACHE_BACKEND', 'file').lower()
    if backend == 'r2':
        return TieredCacheBackend(r2=R2CacheBackend(), kv=KVCacheBackend())
    if backend == 'kv':
        return KVCacheBackend()
    return FileCacheBackend()
```

### 4.3 Cloudflare-Specific Considerations

| Concern | Mitigation |
|---------|------------|
| Ephemeral container disk | Never rely on `_index.json` locally; move to KV |
| Multi-instance containers | Shared R2 + KV; memory L1 is best-effort only |
| Egress to CFBD | Cache aggressively; SWR to reduce burst fetches |
| R2 eventual consistency | Use versioned keys; avoid read-after-write races on same key |
| Workers vs Containers | API stays on Containers (Flask/gunicorn); Pages serves static frontend |
| Secrets | `CFBD_API_KEY`, R2 credentials via Cloudflare secrets / GitHub Actions |
| Cache warm | Cron Trigger or GitHub scheduled workflow → `GET /rankings` + new `POST /cache/warm-priors` |

### 4.4 Environment Variables (Target)

| Variable | Purpose |
|----------|---------|
| `CACHE_BACKEND` | `file` \| `r2` \| `tiered` |
| `CACHE_DIR` | Local fallback path (`/tmp/cfb-cache`) |
| `R2_*` | Existing R2 credentials |
| `KV_NAMESPACE_ID` | Cloudflare KV binding ID |
| `CACHE_ALGORITHM_VERSION` | Key namespace bump on algo changes |
| `CACHE_CLEAR_SECRET` | Protect `/cache/clear` |
| `CACHE_SWR_STALE_SECONDS` | Enable SWR window (0 = disabled) |

---

## 5. TTL Policy Recommendations

### 5.1 Current TTLs

| Constant | Value | Used? |
|----------|-------|-------|
| `TTL_TEAMS` | 24h | Yes |
| `TTL_GAMES_HISTORICAL` | 7d | Yes |
| `TTL_GAMES_CURRENT` | 1h | Yes |
| `TTL_RANKINGS` | 30m | Yes (also wrongly applied to memory reload) |
| `TTL_PRIORS` | 7d | **No** |

### 5.2 Recommended TTLs

| Data Class | TTL (fresh) | Stale Window (SWR) | Rationale |
|------------|-------------|---------------------|-----------|
| Historical games (completed season) | **30d** | ∞ (immutable) | Scores never change; longer TTL reduces R2 reads |
| Current-season games (in-season) | **15m** on Sat/Sun, **1h** weekdays | 6h | Balance freshness vs API load during game days |
| Postseason games | 1h until season complete, then 30d | — | Transition to historical after championship |
| Teams / logos | **7d** | 30d | Rarely changes mid-season |
| Priors (`year`) | **7d** | 30d | Recompute only if historical games bust |
| History rankings (`hist_year`) | **30d** | ∞ | Immutable after season |
| Computed rankings (default params) | **15m** in-season | **2h** | Weekend traffic spike protection |
| Computed rankings (custom params) | **5m** | 30m | Lower hit rate; shorter freshness |
| CFBD poll rankings (if used later) | Same as games | — | — |
| Betting lines | **30m** in-season | 2h | Lines move; only matters for ATS |

### 5.3 Season-Aware TTL Function

Replace binary `is_historical_season()` check with explicit phases:

```python
def get_cache_phase(year: int) -> str:
    """Returns: 'historical' | 'offseason' | 'in_season' | 'game_day'"""
```

- **`game_day`:** Saturday/Sunday during Aug–Jan → shortest games/rankings TTL
- **`in_season`:** Weekday Aug–Jan → moderate TTL
- **`offseason`:** Feb–Jul for prior year → historical TTLs
- **`historical`:** `year < current_season_year` → long/immutable TTLs

### 5.4 TTL Implementation Fixes

1. **Preserve TTL on memory reload** — store `expires_at` from backend entry, not `time.time() + TTL_RANKINGS`
2. **Wire `TTL_PRIORS`** — apply to priors cache once implemented
3. **Separate memory TTL from disk TTL** — memory can be shorter (L1) without affecting persistence
4. **Version keys** — include `CACHE_ALGORITHM_VERSION` in all computed keys to avoid serving stale algo results after deploy

---

## 6. Prioritized Migration Steps

### P0 — Quick wins (1–2 days, no infra change)

| # | Task | Impact |
|---|------|--------|
| 1 | Pass `prefix=` in all `cache.set()` calls (`api_integration.py`, `app.py`) | Enables `invalidate_prefix` |
| 2 | Fix memory reload TTL bug in `Cache.get()` | Correct L1 behavior |
| 3 | Cache `/rankings/team/*` via same `rankings_computed` key + post-process | Eliminates duplicate compute |
| 4 | Add `boto3` to `requirements.txt` | R2 works in production |
| 5 | Document/set `gunicorn --workers 1` explicitly in `render.yaml` | Predictable memory until shared cache |

### P1 — Priors & performance (3–5 days)

| # | Task | Impact |
|---|------|--------|
| 6 | Implement `priors:v1:{year}` cache in `calculate_rankings_logic()` | **Largest CPU savings** on cache miss |
| 7 | Implement `history_rankings:v1:{year}` intermediate cache | Avoids triple recompute when priors bust |
| 8 | Add `POST /cache/warm-priors?year=` admin endpoint | Scheduled pre-warm before weekends |
| 9 | Include `CACHE_ALGORITHM_VERSION` in computed ranking keys | Safe deploys |

### P2 — R2 production hardening (1 week)

| # | Task | Impact |
|---|------|--------|
| 10 | R2 structured keys `cache/{prefix}/{hash}.json` | Operability, prefix listing |
| 11 | Move `_prefix_index` to KV (or R2 manifest file) | Multi-instance invalidation |
| 12 | Remove dual-write divergence — R2 authoritative, local optional L1 | Consistency |
| 13 | Expand `/cache/stats` — entry counts by prefix, backend health | Observability |
| 14 | Deploy Cloudflare Containers with `CACHE_BACKEND=r2` + secrets | Production parity with migration target |

### P3 — Stale-while-revalidate (1 week)

| # | Task | Impact |
|---|------|--------|
| 15 | Add `stale_until` field to cache entries | SWR data model |
| 16 | `Cache.get()` returns stale within window; flags `needs_refresh` | Latency stability |
| 17 | Background refresh via `threading.Thread` (dev) or Cloudflare Queue (prod) | Async revalidation |
| 18 | Season-aware TTL helper | Smarter expiry |

### P4 — Tiered KV + operational maturity (2 weeks)

| # | Task | Impact |
|---|------|--------|
| 19 | Implement `KVCacheBackend` + `TieredCacheBackend` | Cloudflare-native architecture |
| 20 | Selective invalidation by year sub-prefix (`games:2024:*`) | Surgical busts |
| 21 | Hit/miss metrics (Prometheus or CF Analytics) | Capacity planning |
| 22 | Cache size caps + LRU eviction for file backend | Dev machine hygiene |
| 23 | Refactor `api_integration.py` to use `@cached` decorator | DRY, consistent prefix registration |

---

## Appendix A — Cache Key Reference

| Prefix | Args / Kwargs | Example Logical Key |
|--------|---------------|---------------------|
| `games` | `(year, week, season_type)` | `games:(2024, None, 'regular')` |
| `team_info` | `()` | `team_info:():{}` |
| `teams_with_logos` | `()` | `teams_with_logos:():{}` |
| `rankings` | `(year, week)` | CFBD poll data |
| `betting_lines` | `(year, week)` | Lines data |
| `rankings_computed` | sorted query params | Full API response |

All keys are hashed: `md5(f"{prefix}:{args}:{sorted(kwargs)}")`.

---

## Appendix B — Files Reviewed

| File | Role |
|------|------|
| `cache.py` | Cache backends, TTL constants, memory layer, prefix index |
| `api_integration.py` | CFBD client, API response caching |
| `data_processor.py` | Game fetch, transform, conference classification |
| `app.py` | Flask routes, rankings pipeline, computed rankings cache |
| `render.yaml` | Production gunicorn deployment |
| `.github/workflows/deploy-cloudflare.yml` | R2 cache backend flag |
| `.github/workflows/cache-warm.md` | Scheduled cache warm spec |

---

## Appendix C — Decision Log

| Decision | Choice | Alternatives Considered |
|----------|--------|-------------------------|
| Primary shared store for Cloudflare | R2 | D1 (schema overhead for blob JSON), R2 + KV tiered (chosen for P4) |
| Priors cache granularity | Per target year | Per (target year, config) — rejected; priors use default config only |
| SWR first target | Computed rankings | Games cache — rankings miss hurts most UX |
| Worker count until tiered cache | 1 | N workers + shared R2 — defer until P2 complete |

---

*End of audit.*
