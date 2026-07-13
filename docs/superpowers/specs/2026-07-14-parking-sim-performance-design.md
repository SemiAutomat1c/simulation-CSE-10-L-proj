# Parking Simulation Performance Design

**Date:** 2026-07-14  
**Project:** `parking-simulation` / `simulation-CSE-10-L-proj`  
**Status:** Approved for implementation planning  
**Priority:** Keep visual fidelity; speed up config/map changes and playback

## Problem

Changing scenario, map, or config parameters feels slow for three reasons that stack:

1. **Server re-run** — every `GET /api/simulation` runs SimPy and builds a dense timeline (~2–3s).
2. **Huge JSON** — full frame dumps are ~95–100MB with ~4k–5k frames for typical runs.
3. **Assets + playback** — map backgrounds are ~2.3MB PNGs each; cache-busting and full per-frame DOM/state work add lag when switching maps or animating.

Measured (local, 2026-07-14):

| Run | Wall time | Frames | JSON size |
|-----|-----------|--------|-----------|
| baseline / one_entrance_one_exit | ~2.7s | ~5466 | ~101MB |
| rush_hour / two_entrance_two_exit | ~2.2s | ~4176 | ~95MB |

**Constraint (user choice):** Option **A** — keep the current look (same map art and smooth animation). Speed comes from caching, thinner wire format, smarter reloads, and client interpolation — not a schematic redesign.

## Goals

- Same map PNGs and vehicle/slot visuals as today.
- Much smaller simulation payloads and faster repeat loads for the same config.
- Faster map switches after first page load (preload + browser cache).
- Smoother playback with fewer server samples via client interpolation.
- Preserve deterministic SimPy behavior and metrics for class demo / tests.

## Non-goals

- Redesigning map art or replacing the lot with pure CSS/canvas schematic look.
- Moving the SimPy model into the browser.
- Persistent disk/Redis cache across process restarts (v1 is in-memory only).
- Changing educational metrics semantics or scenario definitions.

## Approach (chosen)

**Primary: Smart cache + thinner timeline**  
**Secondary: Warm default combos** (5 scenarios × 4 maps) in memory.

Rejected for this pass: full client-side sim rewrite (too much risk of desync with SimPy and class-demo determinism).

---

## Architecture

```text
Browser                         FastAPI                         SimPy
  |                               |                               |
  |  GET /api/simulation?...      |                               |
  |------------------------------>|  cache key = normalized params|
  |                               |--hit--> return compact JSON   |
  |                               |--miss-> run_simulation() ---->|
  |                               |         compact frames        |
  |                               |         store in LRU cache    |
  |  compact timeline + metrics   |                               |
  |<------------------------------|                               |
  |  expand / interpolate + draw  |                               |
  |  map PNGs: preload + cache    |                               |
```

### Components

| Component | Responsibility |
|-----------|----------------|
| `run_simulation` | Unchanged discrete-event logic and metrics. Source of truth. |
| `timeline_compact` (new) | Full result → compact wire format; pure functions, unit-tested. |
| Result LRU cache | In-process cache of API results keyed by normalized params + format. |
| Default warmer | Fill compact results for 5×4 default scenario/map pairs (lazy or light startup). |
| Frontend expand | Compact → in-memory shape renderer expects; lerp between keyframes. |
| Asset layer | Preload map PNGs; long-cache static assets; no random query bust on images. |

---

## Data format (compact timeline)

### Why

Per-frame full car/slot objects × thousands of frames explodes JSON. Most fields are static or rarely change.

### Wire shape (compact)

**Once per run (not per frame):**

- `slots` — full slot definitions used for rendering.
- `vehicles` (or `roster`) — static vehicle props: id, type, color, entry/exit gate assignment, assigned slot id, etc.

**Keyframes only:**

- Emit a keyframe when something meaningful changes (vehicle state, gate flags, park/leave) **and** enforce a maximum gap (e.g. every 0.25–0.5 sim-minutes) so motion stays smooth.
- Each keyframe uses short keys and **deltas** (only vehicles that changed since the previous keyframe).

Example sketch:

```json
{
  "scenario": "baseline",
  "map": "one_entrance_one_exit",
  "format": "compact",
  "slots": [ /* static */ ],
  "vehicles": [ /* roster */ ],
  "timeline": {
    "start_minute": 0,
    "end_minute": 120,
    "interval_minutes": 0.25
  },
  "keyframes": [
    {
      "t": 12.5,
      "g": { "e": [1, 0], "x": [1] },
      "v": {
        "c3": { "s": "searching", "x": 0.42, "y": 0.61, "h": 90 }
      }
    }
  ],
  "metrics": { /* unchanged keys vs today */ }
}
```

Exact short-key mapping is an implementation detail but must be documented in code comments and tests.

### Client expansion

`expandTimeline(compact) → { frames or sample(t) API }` producing the same fields `renderFrame` / playback uses today so draw code stays mostly unchanged.

### Compatibility

- UI default: `format=compact` (or compact as API default).
- Debug/tests: `format=full` preserves today’s dense frame list when needed.
- Metrics object field names and meanings stay identical.

### Format success criteria

- Typical baseline compact payload **well under 10MB** (target **&lt; 2–5MB** if achievable without visual loss).
- Expanded path matches full timeline within a small position epsilon; discrete states and gate flags match at keyframe times.

---

## Frontend

### Map assets

- Keep existing map background PNGs as visual source of truth.
- Preload all map backgrounds once on page load.
- Use stable asset URLs; do **not** append `Date.now()` cache-busters to image URLs.
- Serve `/static/assets/` with long-lived `Cache-Control` where safe.
- Optional PNG recompression only if preload + HTTP cache still leave map switches slow; not required for v1 if those two fix the feel.

### Config / map / scenario changes

- Clear loading status while fetching.
- Request compact simulation JSON.
- Client-side memory cache keyed the same way as the server (identical params → instant, no network).
- Debounce rapid custom-parameter changes (~150–250ms) to avoid request storms while dragging sliders.

### Playback

- Expand compact keyframes once, or sample on the fly:
  - Continuously advancing clock as today.
  - Lerp `x`, `y`, heading between surrounding keyframes.
  - Snap discrete fields (`state`, gate open flags) at keyframe boundaries.
- Prefer `requestAnimationFrame` for the draw loop if not already fully rAF-driven.
- Avoid full DOM rebuilds every tick: reuse vehicle/slot nodes; update transforms/classes only for entities that changed.

### Compare view

- Keep metrics-only `/api/compare` and existing metrics cache behavior.
- Compare must not download full vehicle timelines.

### Errors and memory

- On invalid payload / expand failure: show error status; keep last good run visible if available.
- Client cache: LRU or max N entries (e.g. 8–12).
- Server cache: max entries (e.g. 40) LRU.

---

## Backend cache and API

### Cache key

Normalized:

```text
(map, scenario, total_cars, slot_count, entry_service, exit_service, base_search, seed, format)
```

`None`/default params must normalize the same way `ParkingSimulationConfig` / `run_simulation` already resolve defaults so keys match real work.

### Values

Store the response-ready dict (compact or full) so hits skip both SimPy and re-compaction when possible. Compaction cost is small vs SimPy; either store post-compact or cache full + compact on demand — prefer store **post-transform** for the requested format.

### Warming

- 5 scenarios × 4 maps with default parameters in **compact** format.
- Lazy warm (background after first request) preferred so server cold start stays light; optional eager warm is acceptable if fast enough on local dev.

### Endpoints

| Endpoint | Behavior |
|----------|----------|
| `GET /api/simulation` | `format=compact` default; `format=full` optional. Cache lookup → miss runs SimPy → compact if needed → store → return. |
| `GET /api/scenarios` | Unchanged. |
| `GET /api/compare` | Unchanged contract; metrics-only; keep/reuse metrics cache. |
| Static `/static/assets/*` | Long cache headers. HTML may remain no-cache for easy deploys. |

### Module layout (suggested)

- `app/timeline_compact.py` — pure compact/expand (or expand only on client; server compact only).
- `app/api.py` — cache, format query param, static cache headers, optional warm.
- `app/simulation.py` — no behavior change required beyond exporting structures needed to compact.
- `app/static/app.js` — fetch compact, expand, preload maps, client cache, debounce, playback lerp.

### Concurrency

Single-worker local uvicorn: plain dict/LRU is enough. Multi-worker = per-process cache only (acceptable for class demo / Vercel constraints).

---

## Testing

| Area | Verification |
|------|----------------|
| Compact fidelity | Expand(compact(full)) ≈ full positions within epsilon; states/gates match at keyframes |
| Determinism | Same config → identical compact payload and metrics twice |
| Cache hit | Second identical API call does not call `run_simulation` again (counter/spy) |
| API formats | Default/UI compact shape; `format=full` still available |
| Metrics | Same keys/values as current path for fixed seeds |
| Frontend static | Preload/expand/cache helpers present; asset URLs not randomly busted |
| Regression | Existing unit tests still pass |

---

## Success criteria (ship bar)

1. Typical baseline compact response **≪ 10MB** (aim **&lt; 2–5MB**).
2. Second load of identical params feels instant (server cache hit, on the order of **&lt; ~100ms**).
3. Cold custom run still ~2–3s sim cost; not worse than today.
4. After first page load, map switches do not multi-second-stall on image fetch.
5. Playback not jankier than today; cars/gates look the same.
6. Same map PNGs and vehicle visuals — no schematic downgrade.

---

## Implementation order (for planning)

1. Add compact/expand pure module + fidelity tests (can use existing full `to_dict()` as oracle).
2. Wire `format` on `/api/simulation` + server LRU cache + default warming.
3. Frontend: consume compact, expand, client cache, debounce.
4. Frontend: map preload + static cache headers + remove image cache-bust.
5. Playback interpolation / rAF / DOM update thrash reduction as needed for jank.
6. Benchmark payload size and repeat-hit latency; adjust keyframe gap if needed.
7. Update README briefly (performance notes / `format` param).

---

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Over-aggressive keyframes cause visual jumps | Max gap + state-change triggers; epsilon tests vs full frames |
| Cache key mismatch with defaults | Shared normalize function used by API and tests |
| Memory growth from large caches | Hard LRU caps client + server |
| Vercel cold start | In-memory only; first request may still pay sim cost; warm after first hit |
| Expand bugs break demo | Keep `format=full` fallback; last-good-run UI |

---

## Decisions log

| Decision | Choice |
|----------|--------|
| Quality vs speed | Keep look (option A) |
| Primary strategy | Cache + compact timeline + client interp |
| Defaults | Warm 5×4 scenario/map compact results |
| Persistence | In-memory only for v1 |
| Sim engine | Stay server-side SimPy |

---

## References

- Local clone: `/Users/ryandeniega/repos/Repo/parking-simulation`
- Remote: `https://github.com/SemiAutomat1c/simulation-CSE-10-L-proj`
- Architecture overview: `docs/architecture.md`
- Hot path: `app/api.py`, `app/simulation.py`, `app/static/app.js`
