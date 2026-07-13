from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.cache import LRUCache
from app.simulation import ParkingSimulationConfig, run_simulation
from app.timeline_compact import compact_simulation


STATIC_DIR = Path(__file__).resolve().parent / "static"
ASSETS_DIR = STATIC_DIR / "assets"
# Demand profiles — how busy the lot is and how fast gates serve.
SCENARIOS = {
    "baseline": "Normal mall parking demand with balanced entry and exit flow",
    "rush_hour": "Clustered arrival wave that creates entry queue pressure",
    "limited_slots": "Reduced parking capacity that forces some cars to be denied",
    "slow_entry": "Slower entrance gate processing creates a visible entry queue",
    "exit_congestion": "Slower exit throughput creates post-shopping congestion",
}
# Gate layouts — chosen independently of the scenario; sets the background + gates.
MAPS = {
    "one_entrance_one_exit": "One entry gate and one exit gate",
    "two_entrance_one_exit": "Two entry gates feed a single exit gate",
    "one_entrance_two_exit": "One entry gate, two exit gates clear the surge",
    "two_entrance_two_exit": "Two entry gates and two exit gates share the load",
}

_simulation_cache = LRUCache(maxsize=40)
_metrics_cache: dict[tuple[str, str], dict] = {}


def _clamp(value: float | int | None, lo: float | int, hi: float | int) -> float | int | None:
    return None if value is None else max(lo, min(hi, value))


def _normalize_format(format_name: str) -> str:
    if format_name not in ("compact", "full"):
        return "compact"
    return format_name


def _simulation_cache_key(
    map_name: str,
    scenario: str,
    total_cars: int | None,
    slot_count: int | None,
    entry_service: float | None,
    exit_service: float | None,
    base_search: float | None,
    seed: int | None,
    format_name: str,
) -> tuple:
    return (
        map_name,
        scenario,
        total_cars,
        slot_count,
        entry_service,
        exit_service,
        base_search,
        seed,
        format_name,
    )


def _build_payload(
    scenario: str,
    map_name: str,
    total_cars: int | None,
    slot_count: int | None,
    entry_service: float | None,
    exit_service: float | None,
    base_search: float | None,
    seed: int | None,
    format_name: str,
) -> dict[str, Any]:
    result = run_simulation(
        ParkingSimulationConfig(
            scenario=scenario,
            map=map_name,
            total_cars=total_cars,
            slot_count=slot_count,
            entry_service=entry_service,
            exit_service=exit_service,
            base_search=base_search,
            seed=seed,
        )
    )
    payload = result.to_dict()
    if format_name == "compact":
        return compact_simulation(payload)
    return payload


def _warm_defaults() -> None:
    """Fill compact responses for every default scenario × map combination."""
    for scenario in SCENARIOS:
        for map_name in MAPS:
            key = _simulation_cache_key(
                map_name,
                scenario,
                None,
                None,
                None,
                None,
                None,
                None,
                "compact",
            )
            if _simulation_cache.get(key) is not None:
                continue
            payload = _build_payload(
                scenario,
                map_name,
                None,
                None,
                None,
                None,
                None,
                None,
                "compact",
            )
            _simulation_cache.set(key, payload)


def create_app(*, warm_defaults: bool = False) -> FastAPI:
    app = FastAPI(title="Mall Parking Simulation")

    # Register before StaticFiles mount so long-cache headers apply to assets.
    @app.get("/static/assets/{asset_path:path}")
    def cached_asset(asset_path: str) -> FileResponse:
        path = ASSETS_DIR / asset_path
        try:
            resolved = path.resolve()
            assets_root = ASSETS_DIR.resolve()
        except OSError as exc:
            raise HTTPException(status_code=404) from exc
        if not resolved.is_file() or not str(resolved).startswith(str(assets_root)):
            raise HTTPException(status_code=404)
        return FileResponse(
            resolved,
            headers={"Cache-Control": "public, max-age=31536000, immutable"},
        )

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(
            STATIC_DIR / "index.html",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )

    @app.get("/api/scenarios")
    def scenario_list() -> dict:
        return {"scenarios": SCENARIOS, "maps": MAPS}

    @app.get("/api/simulation")
    def simulation(
        scenario: str = "baseline",
        map: str = "one_entrance_one_exit",
        total_cars: int | None = None,
        slot_count: int | None = None,
        entry_service: float | None = None,
        exit_service: float | None = None,
        base_search: float | None = None,
        seed: int | None = None,
        format: str = "compact",
    ) -> dict:
        if scenario not in SCENARIOS:
            scenario = "baseline"
        if map not in MAPS:
            map = "one_entrance_one_exit"

        format_name = _normalize_format(format)
        clamped_total_cars = _clamp(total_cars, 1, 200)
        clamped_slot_count = _clamp(slot_count, 1, 72)
        clamped_entry_service = _clamp(entry_service, 0.1, 15.0)
        clamped_exit_service = _clamp(exit_service, 0.1, 15.0)
        clamped_base_search = _clamp(base_search, 0.1, 15.0)

        key = _simulation_cache_key(
            map,
            scenario,
            clamped_total_cars,
            clamped_slot_count,
            clamped_entry_service,
            clamped_exit_service,
            clamped_base_search,
            seed,
            format_name,
        )
        cached = _simulation_cache.get(key)
        if cached is not None:
            return cached

        payload = _build_payload(
            scenario,
            map,
            clamped_total_cars,
            clamped_slot_count,
            clamped_entry_service,
            clamped_exit_service,
            clamped_base_search,
            seed,
            format_name,
        )
        _simulation_cache.set(key, payload)
        return payload

    @app.get("/api/compare")
    def compare(map: str = "one_entrance_one_exit") -> dict:
        """Metrics-only run of every scenario on the given map for side-by-side
        analysis. Output is deterministic, so results are cached per (map, scenario)."""
        if map not in MAPS:
            map = "one_entrance_one_exit"
        scenarios = {}
        for name in SCENARIOS:
            key = (map, name)
            if key not in _metrics_cache:
                _metrics_cache[key] = run_simulation(
                    ParkingSimulationConfig(scenario=name, map=map)
                ).metrics
            scenarios[name] = {
                "description": SCENARIOS[name],
                "metrics": _metrics_cache[key],
            }
        return {"scenarios": scenarios}

    if warm_defaults:
        threading.Thread(target=_warm_defaults, daemon=True).start()

    return app
