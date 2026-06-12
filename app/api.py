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
    def simulation(scenario: str = "baseline") -> dict:
        if scenario not in SCENARIOS:
            scenario = "baseline"
        result = run_simulation(ParkingSimulationConfig(scenario=scenario))
        return result.to_dict()

    return app
