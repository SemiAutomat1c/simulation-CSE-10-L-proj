# Parking Simulation Performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make scenario/map/config changes and playback feel fast while keeping the same map art and vehicle visuals, by compacting the ~100MB timeline, caching results, and preloading map assets.

**Architecture:** Keep SimPy as the source of truth. After each run, convert the dense frame list into a compact delta-keyframe payload. Cache compact (and full) API responses in an in-memory LRU keyed by normalized params. The browser expands compact payloads into playback frames (keyframes with full car objects), interpolates between them (already supported), preloads map PNGs, and caches identical client requests. Defaults (5 scenarios × 4 maps) warm into the server cache lazily.

**Tech Stack:** Python 3, FastAPI, unittest, vanilla JS (no new npm deps), existing SimPy model in `app/simulation.py`.

## Global Constraints

- Keep visual fidelity (same map PNGs and vehicle CSS sprites) — no schematic redesign.
- Do not move SimPy into the browser.
- Metrics field names and meanings stay unchanged.
- Deterministic: same config → same metrics and same compact payload.
- v1 cache is in-process memory only (no Redis/disk).
- Existing `run_simulation(...).to_dict()` stays **full** frames for unit tests in `tests/test_simulation.py`.
- API default for the dashboard becomes `format=compact`; `format=full` remains for debug and compatibility tests.
- Typical baseline compact JSON must be **≪ 10MB** (target **&lt; 2–5MB**).
- Spec: `docs/superpowers/specs/2026-07-14-parking-sim-performance-design.md`.

## File structure

| File | Responsibility |
|------|----------------|
| `app/timeline_compact.py` | **Create.** Pure functions: compact full result dict ↔ expand to playback frames; keyframe selection; short-key encode/decode. |
| `app/cache.py` | **Create.** Small LRU dict with get/set/maxsize; optional run counter for tests. |
| `app/api.py` | Wire `format`, cache, clamp/normalize key, compact path, static asset cache headers, lazy default warm. |
| `app/simulation.py` | Touch only if needed (e.g. include `map` on result); prefer no behavior change. |
| `app/static/app.js` | Fetch compact, expand, client LRU, debounce, map preload, stable image URLs, time-aware playback if needed. |
| `app/static/index.html` | Bump `app.js`/`style.css` query version only if static tests require it. |
| `tests/test_timeline_compact.py` | **Create.** Fidelity, size, determinism for compact/expand. |
| `tests/test_api.py` | Compact default, full format, cache hit. |
| `tests/test_frontend_static.py` | Strings for expand/preload/format=compact/no image Date.now bust. |
| `README.md` | Short note on performance / `format` query param. |

---

### Task 1: Compact/expand pure module (TDD)

**Files:**
- Create: `app/timeline_compact.py`
- Create: `tests/test_timeline_compact.py`

**Interfaces:**
- Consumes: full `ParkingSimulationResult.to_dict()` shape (`scenario`, `defaults`, `timeline`, `slots`, `frames`, `metrics`).
- Produces:
  - `compact_simulation(full: dict, *, max_gap_minutes: float = 0.25) -> dict`
  - `expand_simulation(compact: dict) -> dict` returning a **full-shaped** dict with `frames` (one frame per keyframe, cars fully hydrated — not sparse deltas).

**Compact wire format (lock this):**

```python
{
  "format": "compact",
  "scenario": str,
  "defaults": dict,
  "timeline": {
    "snapshot_interval_minutes": float,  # original sim interval (for reference)
    "end_minute": float,
    "keyframe_max_gap_minutes": float,
  },
  "slots": [...],  # same as full top-level slots (static layout)
  "roster": [  # static per vehicle; first-seen props
    {
      "id": int,
      "vehicle_type": str,
      "exit_lane": str,
      "exit_layout": str,
      "entrance": str,
    },
    ...
  ],
  "keyframes": [
    {
      "t": float,  # time_minutes
      "g": {"e": bool, "x": bool},  # entry_gate_open, exit_gate_open
      "q": {"e": int, "x": int, "p": int, "a": int, "d": int, "c": int},
      # current_entry_queue, current_exit_queue, parked_count,
      # available_slots, denied_count, completed_count
      "s": {  # slot id -> state only when changed vs previous keyframe
        "C1": "occupied",
      },
      "v": {  # vehicle id str -> delta fields only
        "0": {"s": "searching", "x": 12.3, "y": 45.6, "h": 90.0, "p": "merge", "sid": "C3", "qa": False},
      },
    },
  ],
  "metrics": dict,  # unchanged
}
```

Vehicle delta keys: `s` state, `x`, `y`, `h` heading, `p` exit_phase, `sid` slot_id, `qa` queue_arrived.  
Omit a vehicle id if none of those fields changed since previous keyframe.  
Always include full vehicle state on first keyframe for every car that exists in that full frame.

**Keyframe rule:** keep frame `i` if any of:
1. `i == 0` or last frame,
2. any car `state` or `exit_phase` or `slot_id` changed vs previous kept frame,
3. gate open flags changed,
4. time since last kept frame ≥ `max_gap_minutes`.

Positions/headings on kept frames are taken from the full frame (already spaced by SimPy).

- [ ] **Step 1: Write failing tests**

Create `tests/test_timeline_compact.py`:

```python
import json
import unittest

from app.simulation import ParkingSimulationConfig, run_simulation
from app.timeline_compact import compact_simulation, expand_simulation


class TimelineCompactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.full = run_simulation(
            ParkingSimulationConfig(scenario="baseline", map="one_entrance_one_exit")
        ).to_dict()

    def test_compact_is_much_smaller_than_full(self) -> None:
        compact = compact_simulation(self.full)
        full_size = len(json.dumps(self.full, separators=(",", ":")))
        compact_size = len(json.dumps(compact, separators=(",", ":")))
        self.assertEqual(compact["format"], "compact")
        self.assertLess(compact_size, full_size * 0.15)
        self.assertLess(compact_size, 5_000_000)

    def test_expand_restores_keyframes_with_full_car_fields(self) -> None:
        compact = compact_simulation(self.full)
        expanded = expand_simulation(compact)
        self.assertIn("frames", expanded)
        self.assertGreater(len(expanded["frames"]), 10)
        self.assertLess(len(expanded["frames"]), len(self.full["frames"]))
        car0 = expanded["frames"][0]["cars"][0]
        for key in ("id", "vehicle_type", "state", "x", "y", "heading", "slot_id"):
            self.assertIn(key, car0)

    def test_expand_matches_full_at_keyframe_times(self) -> None:
        compact = compact_simulation(self.full, max_gap_minutes=0.25)
        expanded = expand_simulation(compact)
        full_by_t = {round(f["time_minutes"], 2): f for f in self.full["frames"]}
        for frame in expanded["frames"]:
            t = round(frame["time_minutes"], 2)
            self.assertIn(t, full_by_t)
            truth = full_by_t[t]
            self.assertEqual(frame["entry_gate_open"], truth["entry_gate_open"])
            self.assertEqual(frame["exit_gate_open"], truth["exit_gate_open"])
            truth_cars = {c["id"]: c for c in truth["cars"]}
            for car in frame["cars"]:
                tc = truth_cars[car["id"]]
                self.assertEqual(car["state"], tc["state"])
                self.assertEqual(car["exit_phase"], tc["exit_phase"])
                self.assertEqual(car["slot_id"], tc["slot_id"])
                self.assertAlmostEqual(car["x"], tc["x"], places=2)
                self.assertAlmostEqual(car["y"], tc["y"], places=2)

    def test_metrics_and_scenario_preserved(self) -> None:
        compact = compact_simulation(self.full)
        self.assertEqual(compact["metrics"], self.full["metrics"])
        self.assertEqual(compact["scenario"], self.full["scenario"])
        expanded = expand_simulation(compact)
        self.assertEqual(expanded["metrics"], self.full["metrics"])

    def test_compact_is_deterministic(self) -> None:
        a = compact_simulation(self.full)
        b = compact_simulation(self.full)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests — expect fail**

```bash
cd /Users/ryandeniega/repos/Repo/parking-simulation
python3 -m unittest tests.test_timeline_compact -v
```

Expected: `ModuleNotFoundError: app.timeline_compact` or import errors.

- [ ] **Step 3: Implement `app/timeline_compact.py`**

Implement `compact_simulation` and `expand_simulation` per the wire format above. Pseudocode for compact:

```python
def compact_simulation(full: dict, *, max_gap_minutes: float = 0.25) -> dict:
    frames = full["frames"]
    keep_indices = _select_keyframe_indices(frames, max_gap_minutes)
    roster = _build_roster(frames)
    keyframes = []
    prev_car_state = {}
    prev_slot_state = {}
    for i in keep_indices:
        frame = frames[i]
        kf = {"t": frame["time_minutes"], "g": {...}, "q": {...}, "v": {}, "s": {}}
        # delta cars vs prev_car_state; update prev_car_state
        # delta slots vs prev_slot_state (by id -> state)
        keyframes.append(kf)
    return {
        "format": "compact",
        "scenario": full["scenario"],
        "defaults": full.get("defaults", {}),
        "timeline": {
            "snapshot_interval_minutes": full["timeline"]["snapshot_interval_minutes"],
            "end_minute": full["timeline"]["end_minute"],
            "keyframe_max_gap_minutes": max_gap_minutes,
        },
        "slots": full["slots"],
        "roster": roster,
        "keyframes": keyframes,
        "metrics": full["metrics"],
    }
```

Expand rebuilds each keyframe into a full frame dict: merge roster + cumulative vehicle state, merge slot states from static `slots` + deltas, set aggregate fields from `q`/`g`.

- [ ] **Step 4: Run tests — expect pass**

```bash
python3 -m unittest tests.test_timeline_compact -v
```

Expected: all OK. If size assertion fails, lower max gap only if fidelity fails; prefer tighter short keys / more aggressive deltas. If fidelity fails on times, ensure kept frames use the same `round(time_minutes, 2)` as full frames.

- [ ] **Step 5: Commit**

```bash
git add app/timeline_compact.py tests/test_timeline_compact.py
git commit -m "feat: compact simulation timeline encode/decode"
```

---

### Task 2: LRU cache helper

**Files:**
- Create: `app/cache.py`
- Create: `tests/test_cache.py`

**Interfaces:**
- Produces: `class LRUCache` with `get(key)`, `set(key, value)`, `clear()`, `__len__`, `maxsize`, and `hits` / `misses` counters (ints).

- [ ] **Step 1: Write failing test**

```python
import unittest
from app.cache import LRUCache

class LRUCacheTests(unittest.TestCase):
    def test_evicts_oldest(self) -> None:
        c = LRUCache(maxsize=2)
        c.set("a", 1)
        c.set("b", 2)
        c.set("c", 3)
        self.assertIsNone(c.get("a"))
        self.assertEqual(c.get("b"), 2)
        self.assertEqual(c.get("c"), 3)
        self.assertEqual(c.misses, 1)
        self.assertEqual(c.hits, 2)

    def test_get_refreshes_recency(self) -> None:
        c = LRUCache(maxsize=2)
        c.set("a", 1)
        c.set("b", 2)
        c.get("a")
        c.set("c", 3)
        self.assertEqual(c.get("a"), 1)
        self.assertIsNone(c.get("b"))
```

- [ ] **Step 2: Run — expect fail**

```bash
python3 -m unittest tests.test_cache -v
```

- [ ] **Step 3: Implement**

Use `collections.OrderedDict`: on `get` move_to_end; on `set` if over maxsize popitem(last=False).

- [ ] **Step 4: Run — expect pass**

- [ ] **Step 5: Commit**

```bash
git add app/cache.py tests/test_cache.py
git commit -m "feat: add in-memory LRU cache helper"
```

---

### Task 3: API format + server cache + asset headers

**Files:**
- Modify: `app/api.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Consumes: `compact_simulation`, `LRUCache`, `run_simulation`, `ParkingSimulationConfig`
- Produces: `GET /api/simulation?format=compact|full` (default **compact**); cache key function; metrics cache unchanged for compare.

**Normalize cache key** as a tuple/string of:

```python
(
  map_name,
  scenario,
  total_cars,      # after clamp, may be None
  slot_count,
  entry_service,
  exit_service,
  base_search,
  seed,
  format_name,     # "compact" | "full"
)
```

- [ ] **Step 1: Update API tests first (failing)**

Replace/extend `tests/test_api.py`:

```python
def test_simulation_default_is_compact(self) -> None:
    response = self.client.get("/api/simulation?scenario=baseline")
    payload = response.json()
    self.assertEqual(response.status_code, 200)
    self.assertEqual(payload.get("format"), "compact")
    self.assertIn("keyframes", payload)
    self.assertIn("roster", payload)
    self.assertIn("metrics", payload)
    self.assertNotIn("frames", payload)

def test_simulation_full_format_still_available(self) -> None:
    response = self.client.get("/api/simulation?scenario=baseline&format=full")
    payload = response.json()
    self.assertEqual(response.status_code, 200)
    self.assertIn("frames", payload)
    self.assertIn("cars", payload["frames"][0])
    self.assertIn("vehicle_type", payload["frames"][0]["cars"][0])

def test_simulation_cache_hit_skips_second_run(self) -> None:
    from app import api as api_module
    api_module._simulation_cache.clear()
    # Patch run counter: wrap run_simulation
    calls = {"n": 0}
    original = api_module.run_simulation

    def counting(config):
        calls["n"] += 1
        return original(config)

    api_module.run_simulation = counting
    try:
        r1 = self.client.get("/api/simulation?scenario=baseline&map=one_entrance_one_exit")
        r2 = self.client.get("/api/simulation?scenario=baseline&map=one_entrance_one_exit")
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r1.json(), r2.json())
        self.assertEqual(calls["n"], 1)
    finally:
        api_module.run_simulation = original

def test_static_assets_have_long_cache_headers(self) -> None:
    response = self.client.get("/static/assets/generated/custom-parking-background.png")
    self.assertEqual(response.status_code, 200)
    cache = response.headers.get("cache-control", "").lower()
    self.assertTrue("max-age" in cache or "public" in cache)
```

Keep existing scenarios/compare tests. Remove or rewrite `test_simulation_endpoint_returns_payload_shape` to match compact default + full optional.

- [ ] **Step 2: Run API tests — expect fail**

```bash
python3 -m unittest tests.test_api -v
```

- [ ] **Step 3: Implement API changes**

In `app/api.py`:

1. Import `compact_simulation`, `LRUCache`.
2. Module-level `_simulation_cache = LRUCache(maxsize=40)`.
3. Add `format: str = "compact"` query param; normalize unknown to `compact`.
4. On simulation endpoint: build key → cache get → else `run_simulation` → `to_dict()` → if compact then `compact_simulation` → `set` → return.
5. For static assets with long cache: either mount a custom route for `/static/assets/...` with headers, or subclass/wrap `StaticFiles`. Minimal approach that passes the test:

```python
from fastapi.responses import FileResponse

@app.get("/static/assets/{asset_path:path}")
def cached_asset(asset_path: str) -> FileResponse:
    path = STATIC_DIR / "assets" / asset_path
    if not path.is_file() or not str(path.resolve()).startswith(str((STATIC_DIR / "assets").resolve())):
        from fastapi import HTTPException
        raise HTTPException(404)
    return FileResponse(
        path,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
```

**Order matters:** register this **before** or instead of relying on the catch-all StaticFiles for assets. Keep `app.mount("/static", ...)` for js/css, but note that more specific routes take precedence in Starlette if declared first — put the assets route **before** the mount.

6. Lazy warm (optional in this task, required before Task 6 done): function `warm_default_cache()` that loops SCENARIOS × MAPS and fills compact entries. Call it from a background thread on first simulation request if cache empty, or from `create_app` via `threading.Thread(target=warm, daemon=True).start()`. Prefer **daemon thread on create_app** so first UI clicks often hit warm cache without blocking import of tests too hard — tests that clear cache remain valid.

**Test isolation:** `create_app` should not make tests wait for full 20-run warm. Use:

```python
def create_app(*, warm_defaults: bool = False) -> FastAPI:
    ...
    if warm_defaults:
        threading.Thread(target=_warm_defaults, daemon=True).start()
```

Production/local `app.main` can pass `warm_defaults=True`. Tests use default `False`.

Check `app/main.py` — set `app = create_app(warm_defaults=True)` if that is the uvicorn entry.

- [ ] **Step 4: Run full unit suite for API + compact**

```bash
python3 -m unittest tests.test_api tests.test_timeline_compact tests.test_cache -v
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add app/api.py app/main.py tests/test_api.py
git commit -m "feat: compact API default with LRU response cache"
```

---

### Task 4: Frontend expand + client cache + compact fetch

**Files:**
- Modify: `app/static/app.js`
- Modify: `tests/test_frontend_static.py`
- Modify: `app/static/index.html` (bump `?v=` on app.js if present)

**Interfaces:**
- Consumes: compact API payload
- Produces: after load, `simulationData` in **expanded full shape** (`frames`, `slots`, `metrics`, …) so existing `renderFrame` / `resetPlayback` keep working.

- [ ] **Step 1: Extend static tests**

In `tests/test_frontend_static.py` add assertions that `app.js` contains:

- `format=compact`
- `expandCompactSimulation` (or the exact name you implement — use **`expandCompactSimulation`**)
- `clientSimulationCache`
- `preloadMapBackgrounds`
- Does **not** use `Date.now()` on map background URLs (MAP_BACKGROUNDS entries must not contain `?v=` cache busters, or use stable versions only — remove `?v=3` from map PNG URLs per design)
- Still may use cache-bust on API if desired, but prefer cache key without timestamp; **remove `&t=${Date.now()}` from `/api/simulation` fetch** so client cache and HTTP cache can work; use client cache key instead.

- [ ] **Step 2: Run frontend static tests — expect fail**

```bash
python3 -m unittest tests.test_frontend_static -v
```

- [ ] **Step 3: Implement expand + load path in `app.js`**

Add (near top-level helpers):

```javascript
const clientSimulationCache = new Map(); // key -> expanded payload; max 12 entries
const CLIENT_CACHE_MAX = 12;

function simulationCacheKey(map, scenario, customQuery) {
  return `${map}|${scenario}|${customQuery}|compact`;
}

function expandCompactSimulation(payload) {
  if (!payload || payload.format !== "compact") return payload;
  const rosterById = new Map((payload.roster || []).map((r) => [r.id, r]));
  const frames = [];
  const carState = new Map();
  const slotState = new Map((payload.slots || []).map((s) => [s.id, { ...s, state: s.state || "free" }]));

  for (const kf of payload.keyframes || []) {
    for (const [id, delta] of Object.entries(kf.v || {})) {
      const numId = Number(id);
      const prev = carState.get(numId) || { ...(rosterById.get(numId) || { id: numId }) };
      const next = { ...prev };
      if (delta.s !== undefined) next.state = delta.s;
      if (delta.x !== undefined) next.x = delta.x;
      if (delta.y !== undefined) next.y = delta.y;
      if (delta.h !== undefined) next.heading = delta.h;
      if (delta.p !== undefined) next.exit_phase = delta.p;
      if (delta.sid !== undefined) next.slot_id = delta.sid;
      if (delta.qa !== undefined) next.queue_arrived = delta.qa;
      next.id = numId;
      carState.set(numId, next);
    }
    for (const [sid, st] of Object.entries(kf.s || {})) {
      const base = slotState.get(sid) || { id: sid };
      slotState.set(sid, { ...base, state: st });
    }
    const cars = Array.from(carState.values()).map((c) => ({ ...c }));
    // ensure every roster car appears (scheduled etc.)
    for (const r of payload.roster || []) {
      if (!carState.has(r.id)) {
        cars.push({ ...r, state: "scheduled", x: 0, y: 0, heading: null, slot_id: null, exit_phase: null, queue_arrived: false });
      }
    }
    frames.push({
      time_minutes: kf.t,
      cars,
      slots: Array.from(slotState.values()),
      entry_gate_open: !!(kf.g && kf.g.e),
      exit_gate_open: !!(kf.g && kf.g.x),
      current_entry_queue: kf.q ? kf.q.e : 0,
      current_exit_queue: kf.q ? kf.q.x : 0,
      parked_count: kf.q ? kf.q.p : 0,
      available_slots: kf.q ? kf.q.a : 0,
      denied_count: kf.q ? kf.q.d : 0,
      completed_count: kf.q ? kf.q.c : 0,
    });
  }

  return {
    scenario: payload.scenario,
    defaults: payload.defaults,
    timeline: {
      snapshot_interval_minutes: payload.timeline.keyframe_max_gap_minutes || payload.timeline.snapshot_interval_minutes,
      end_minute: payload.timeline.end_minute,
    },
    slots: payload.slots,
    frames,
    metrics: payload.metrics,
  };
}

function rememberClientCache(key, value) {
  if (clientSimulationCache.has(key)) clientSimulationCache.delete(key);
  clientSimulationCache.set(key, value);
  while (clientSimulationCache.size > CLIENT_CACHE_MAX) {
    const oldest = clientSimulationCache.keys().next().value;
    clientSimulationCache.delete(oldest);
  }
}
```

**Important:** Keep expand logic consistent with Python `expand_simulation` field names (`s`/`x`/`y`/`h`/`p`/`sid`/`qa`). Prefer implementing expand only in JS for the UI path, and keep Python expand for tests — both must follow the same key map.

Update `loadSimulation`:

```javascript
async function loadSimulation() {
  const scenario = scenarioSelect.value || "baseline";
  const map = mapSelect.value || "one_entrance_one_exit";
  const customQuery = customParamQuery();
  const cacheKey = simulationCacheKey(map, scenario, customQuery);
  setLoadingState(true);
  setSimulationStatus(`Loading ${scenarioLabel(scenario)}...`, "loading");
  applyMap(map);
  try {
    let nextSimulationData;
    if (clientSimulationCache.has(cacheKey)) {
      nextSimulationData = clientSimulationCache.get(cacheKey);
    } else {
      const raw = await fetchJson(
        `/api/simulation?format=compact&map=${encodeURIComponent(map)}&scenario=${encodeURIComponent(scenario)}${customQuery}`
      );
      nextSimulationData = expandCompactSimulation(raw);
      rememberClientCache(cacheKey, nextSimulationData);
    }
    simulationData = nextSimulationData;
    // ... existing render/reset/status ...
  } catch (error) {
    // keep last valid run (existing)
  } finally {
    setLoadingState(false);
  }
}
```

**Debounce:** if scenario/map change handlers call `loadSimulation` directly, wrap custom param apply:

```javascript
let loadTimer = null;
function scheduleLoadSimulation() {
  clearTimeout(loadTimer);
  loadTimer = setTimeout(() => { loadSimulation(); }, 200);
}
```

Use `scheduleLoadSimulation` for slider/input changes; keep immediate `loadSimulation` for initial page load and explicit Apply button if that matches current UX (Apply can stay immediate).

- [ ] **Step 4: Playback interval**

With fewer frames, fixed `snapshot_interval_minutes` from original 0.05 would advance keyframes too slowly or too quickly. In the playback tick (where `baseIntervalMs` is derived), use the **delta between consecutive frame times**:

```javascript
const t0 = simulationData.frames[frameIndex].time_minutes;
const t1 = simulationData.frames[Math.min(frameIndex + 1, simulationData.frames.length - 1)].time_minutes;
const simDelta = Math.max(0.05, t1 - t0);
const baseIntervalMs = (simDelta / 0.05) * REFERENCE_MS; // keep REFERENCE_MS as today's base for 0.05 min
```

If current code uses a constant interval, adjust so wall-clock playback length stays roughly similar to before.

- [ ] **Step 5: Run static tests + full unittest**

```bash
python3 -m unittest -v
```

Expected: all pass (simulation tests still use full `to_dict()`).

- [ ] **Step 6: Commit**

```bash
git add app/static/app.js app/static/index.html tests/test_frontend_static.py
git commit -m "feat: expand compact timelines and client-cache sim loads"
```

---

### Task 5: Map preload + stable asset URLs

**Files:**
- Modify: `app/static/app.js` (`MAP_BACKGROUNDS`, `preloadMapBackgrounds`, boot path)
- Modify: `tests/test_frontend_static.py` if not fully covered in Task 4

- [ ] **Step 1: Implement preload**

```javascript
const DEFAULT_BACKGROUND = "/static/assets/generated/custom-parking-background.png";
const MAP_BACKGROUNDS = {
  two_entrance_two_exit: "/static/assets/generated/map-two-entrance-two-exit.png",
  two_entrance_one_exit: "/static/assets/generated/map-two-entrance-one-exit.png",
  one_entrance_two_exit: "/static/assets/generated/map-one-entrance-two-exit.png",
};

function preloadMapBackgrounds() {
  const urls = [DEFAULT_BACKGROUND, ...Object.values(MAP_BACKGROUNDS)];
  urls.forEach((url) => {
    const img = new Image();
    img.decoding = "async";
    img.src = url;
  });
}
```

Call `preloadMapBackgrounds()` during initial boot (same place as `loadScenarios` / DOMContentLoaded).

- [ ] **Step 2: Manual check**

```bash
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Open Network tab: first load fetches map PNGs; switching maps should show disk/memory cache hits (or at least no multi-second wait). Switching back to a prior scenario should be near-instant (client cache).

- [ ] **Step 3: Commit**

```bash
git add app/static/app.js tests/test_frontend_static.py
git commit -m "perf: preload map backgrounds with stable URLs"
```

---

### Task 6: Default warm + README + benchmarks

**Files:**
- Modify: `app/main.py` / `app/api.py` (`warm_defaults=True` for served app)
- Modify: `README.md`
- Optional: `tests/test_api.py` warm smoke (do not require full 20 sims in every test — only unit-test `_warm_defaults` fills one key if you inject a stub)

- [ ] **Step 1: Enable warm on real app**

```python
# app/main.py
from app.api import create_app
app = create_app(warm_defaults=True)
```

Ensure `_warm_defaults` uses the same clamp/normalize path as the endpoint and stores compact payloads.

- [ ] **Step 2: Benchmark script (run manually, paste numbers into commit message or README)**

```bash
python3 - <<'PY'
import json, time
from app.simulation import ParkingSimulationConfig, run_simulation
from app.timeline_compact import compact_simulation

full = run_simulation(ParkingSimulationConfig(scenario="baseline")).to_dict()
c = compact_simulation(full)
print("full_mb", len(json.dumps(full, separators=(',',':'))) / 1e6)
print("compact_mb", len(json.dumps(c, separators=(',',':'))) / 1e6)
print("full_frames", len(full["frames"]), "keyframes", len(c["keyframes"]))
t0 = time.perf_counter()
compact_simulation(full)
print("compact_ms", (time.perf_counter() - t0) * 1000)
PY
```

Confirm compact_mb &lt; 5 (hard requirement &lt; 10).

- [ ] **Step 3: README section**

Add under API or Performance:

```markdown
## Performance

- Dashboard requests `GET /api/simulation?format=compact` (default).
- Use `format=full` for the dense frame dump (debug/tests).
- Identical queries are cached in memory on the server; the browser also caches expanded results.
- Map backgrounds are preloaded and long-cached under `/static/assets/`.
```

- [ ] **Step 4: Full test suite**

```bash
python3 -m unittest -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add app/main.py app/api.py README.md
git commit -m "perf: warm default sim cache and document format=compact"
```

---

### Task 7: Playback polish (only if jank remains)

**Files:**
- Modify: `app/static/app.js` (`renderFrame` / tick)

**Do this task only if** after Tasks 1–6, manual playback still stutters.

- [ ] **Step 1:** Profile: ensure vehicle nodes are reused (`carNodes` Map already does this). Skip `createVehicleNode` when class unchanged; set `transform` only when position/angle changes.
- [ ] **Step 2:** Avoid `innerHTML` rebuilds on cars each frame (already structured with child spans — keep that).
- [ ] **Step 3:** Commit if changes made:

```bash
git commit -am "perf: reduce playback DOM thrash"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| Compact timeline wire format | Task 1 |
| Expand fidelity / metrics preserved | Task 1 |
| Payload ≪ 10MB / target &lt; 5MB | Task 1, 6 benchmark |
| Server LRU cache | Task 2, 3 |
| `format=compact` default + `full` | Task 3 |
| Cache hit skips re-sim | Task 3 |
| Static long-cache assets | Task 3 |
| Client expand + client cache | Task 4 |
| Debounce custom params | Task 4 |
| Playback works with fewer frames | Task 4 |
| Map preload + stable URLs | Task 5 |
| Warm 5×4 defaults | Task 6 |
| README | Task 6 |
| DOM thrash reduction if needed | Task 7 |
| Keep SimPy / visuals | All tasks (no art rewrite) |

## Self-review notes

- No TBD placeholders in tasks.
- Python `expand_simulation` and JS `expandCompactSimulation` must share the same short-key map (`s,x,y,h,p,sid,qa` / `g.e,g.x` / `q.*`).
- `tests/test_simulation.py` continues to use full `to_dict()` — do not change default `to_dict()` to compact.
- Cache key must use clamped values identical to the endpoint.
- `create_app(warm_defaults=False)` for tests so unittest stays fast.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-14-parking-sim-performance.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — execute tasks in this session with executing-plans and checkpoints  

Which approach?
