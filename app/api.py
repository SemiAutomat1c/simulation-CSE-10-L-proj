from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.simulation import ParkingSimulationConfig, run_simulation


STATIC_DIR = Path(__file__).resolve().parent / "static"
SCENARIOS = {
    "baseline": "Normal mall parking demand with balanced entry and exit flow",
    "rush_hour": "Clustered arrival wave that creates entry queue pressure",
    "limited_slots": "Reduced parking capacity that forces some cars to be denied",
    "slow_entry": "Slower entrance gate processing creates a visible entry queue",
    "exit_congestion": "Slower exit throughput creates post-shopping congestion",
    "two_entrance_two_exit": "Two entry gates and two exit gates share the load",
    "two_entrance_one_exit": "Two entry gates feed a single exit gate",
    "one_entrance_two_exit": "One entry gate, two exit gates clear the post-shopping surge",
}


def create_app() -> FastAPI:
    app = FastAPI(title="Mall Parking Simulation")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(
            STATIC_DIR / "index.html",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )

    @app.get("/api/scenarios")
    def scenario_list() -> dict:
        return {"scenarios": SCENARIOS}

    @app.get("/api/simulation")
    def simulation(
        scenario: str = "baseline",
        total_cars: int | None = None,
        slot_count: int | None = None,
        entry_service: float | None = None,
        exit_service: float | None = None,
        base_search: float | None = None,
        seed: int | None = None,
        entry_gates: int | None = None,
        exit_gates: int | None = None,
    ) -> dict:
        if scenario not in SCENARIOS:
            scenario = "baseline"

        def clamp(value, lo, hi):
            return None if value is None else max(lo, min(hi, value))

        result = run_simulation(
            ParkingSimulationConfig(
                scenario=scenario,
                total_cars=clamp(total_cars, 1, 200),
                slot_count=clamp(slot_count, 1, 72),
                entry_service=clamp(entry_service, 0.1, 15.0),
                exit_service=clamp(exit_service, 0.1, 15.0),
                base_search=clamp(base_search, 0.1, 15.0),
                seed=seed,
                entry_gates=clamp(entry_gates, 1, 4),
                exit_gates=clamp(exit_gates, 1, 4),
            )
        )
        return result.to_dict()

    @app.get("/api/compare")
    def compare() -> dict:
        """Metrics-only run of every scenario for side-by-side analysis.
        Output is deterministic, so results are cached after the first build."""
        scenarios = {}
        for name in SCENARIOS:
            if name not in _metrics_cache:
                _metrics_cache[name] = run_simulation(
                    ParkingSimulationConfig(scenario=name)
                ).metrics
            scenarios[name] = {
                "description": SCENARIOS[name],
                "metrics": _metrics_cache[name],
            }
        return {"scenarios": scenarios}

    return app


_metrics_cache: dict[str, dict] = {}
