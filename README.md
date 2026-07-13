# Mall Parking Simulation

A local FastAPI + SimPy class project that models mall parking flow and visualizes it in a top-down browser dashboard. The MVP is meant for review/demo use: choose a scenario, watch vehicles enter, park, queue, leave, and compare the summary metrics.

## What This Demonstrates

- Discrete-event simulation for entry gates, search time, parking capacity, and exit flow.
- Separate car and motorcycle parking rules.
- Deterministic seeded scenarios so reviewers see repeatable results.
- A browser dashboard with live occupancy, queue pressure, vehicle states, and summary metrics.
- A small JSON API that can be inspected independently from the UI.

## Setup

```bash
python3 -m pip install -r requirements.txt
```

## Run Locally

```bash
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Open `http://127.0.0.1:8001/`.

## Run Tests

```bash
python3 -m unittest
```

The test suite covers the API contract, static frontend hooks, vehicle/slot rules, queue spacing, gate behavior, exit visibility, and deterministic scenario output.

## Project Structure

- `app/api.py`: FastAPI app, static file serving, and JSON endpoints.
- `app/simulation.py`: SimPy-backed parking model, vehicle paths, slot assignment, timeline frames, and metrics.
- `app/static/index.html`: Dashboard markup.
- `app/static/style.css`: Top-down lot and vehicle visuals.
- `app/static/app.js`: Scenario loading, playback, rendering, and UI resilience.
- `tests/`: API, simulation behavior, and static frontend tests.
- `scripts/generate_parking_background.py`: Utility script for generating the parking background asset.

## Scenarios

| Scenario | Purpose |
| --- | --- |
| `baseline` | Normal mall demand with balanced entry and exit flow. |
| `rush_hour` | Clustered arrival wave that makes entry pressure easier to see. |
| `limited_slots` | Reduced capacity, causing some vehicles to be denied. |
| `slow_entry` | Slower entrance gate service, producing a visible entry queue. |
| `exit_congestion` | Slower exit service, producing post-shopping exit congestion. |

Unknown scenario names fall back to `baseline`.

## Simulation Assumptions

- One simulated run is generated server-side and replayed in the browser.
- Scenario seeds make the output deterministic for review and testing.
- Vehicles follow fixed readable lanes instead of free-form driving physics.
- Cars use car slots; motorcycles use motorcycle slots.
- Vehicles can be denied when a compatible slot is unavailable.
- Queue spacing is modeled so vehicles do not stack visually on the same lane.

## Vehicle States

- `scheduled`: Vehicle has not appeared yet.
- `entry_queue`: Vehicle is waiting before the entrance gate.
- `approaching_gate`: Vehicle is moving toward the entrance stop line.
- `gate_wait`: Vehicle is paused at the entrance gate.
- `gate_crossing`: Vehicle is entering the lot.
- `searching`: Vehicle is following the search loop toward an assigned slot.
- `parked`: Vehicle is occupying a slot.
- `exit_queue`: Vehicle has finished parking, or was denied a slot, and is waiting in the shared exit lane.
- `exiting`: Vehicle is moving through the exit gate and outside road.
- `denied`: Vehicle could not park because no compatible slot was available.
- `done`: Vehicle has completed its path.

## Metrics Glossary

- `total_vehicle_count`: Total generated vehicles in the run.
- `total_cars` / `total_motorcycles`: Vehicle mix by type.
- `total_slots`: Usable parking capacity for the selected scenario.
- `visible_slot_count`: Total rendered parking spaces on the map, including unavailable spaces.
- `total_completed_vehicles`: Vehicles that successfully parked and completed the exit path.
- `denied_vehicle_count`: Vehicles denied due to capacity/type constraints.
- `average_search_time_minutes`: Average time from search start to parking start.
- `max_entry_queue_length`: Largest entrance queue observed.
- `max_exit_queue_length`: Largest exit queue observed.
- `peak_occupied_slots`: Highest number of occupied/targeted/exiting slots at one time.
- `occupancy_rate_percent`: Peak occupied slots divided by total slots.
- `car_slot_occupancy_percent`: Peak car-slot usage.
- `motorcycle_slot_occupancy_percent`: Peak motorcycle-slot usage.
- `exit_completion_time_minutes`: Last vehicle completion time.
- `average_entry_wait_minutes` / `average_exit_wait_minutes`: Average time a vehicle spends queued before the entry / exit gate begins serving it.
- `average_wait_minutes`: Average gate waiting time across both gates.
- `average_entry_service_minutes` / `average_exit_service_minutes`: Average processing (service) time at each gate.
- `average_time_in_system_minutes`: Average total time from arrival to departure (cycle time).
- `throughput_vehicles_per_hour`: Completed vehicles divided by the run length, in vehicles per hour.
- `entry_gate_utilization_percent` / `exit_gate_utilization_percent`: Busy server-time divided by available server-time at each gate (capacity-aware, so it stays 0–100% even with multiple gates).
- `entry_gate_count` / `exit_gate_count`: Number of parallel gates used for the run.
- `average_entry_queue_length` / `average_exit_queue_length`: Time-averaged queue length at each gate.

## Performance

- Dashboard requests `GET /api/simulation?format=compact` (default).
- Use `format=full` for the dense frame dump (debug/tests).
- Identical queries are cached in memory on the server; the browser also caches expanded results.
- Map backgrounds are preloaded and long-cached under `/static/assets/`.

## API Endpoints

```text
GET /api/scenarios
```

Returns the available scenario names and descriptions.

```text
GET /api/simulation?scenario=baseline
```

Returns the selected scenario, initial slots, generated timeline frames, and summary metrics. The JSON shape is intentionally stable for the frontend and tests.

Optional query parameters override the scenario's inputs live (each is clamped to a safe range):

| Parameter | Range | Effect |
| --- | --- | --- |
| `total_cars` | 1–200 | Number of vehicles generated |
| `slot_count` | 1–72 | Usable parking spaces |
| `entry_service` / `exit_service` | 0.1–15 | Gate service time (minutes) |
| `base_search` | 0.1–15 | Base slot-search time (minutes) |
| `entry_gates` / `exit_gates` | 1–4 | Number of parallel gates (resource capacity) |
| `seed` | any int | Random seed |

Example: `GET /api/simulation?scenario=rush_hour&entry_gates=2` models a second entry gate
("one cashier vs. two cashiers"). The dashboard's **Custom Inputs** panel sends these same
parameters so values can be typed and applied live during a demo. Note: gate counts above 1
change the metrics correctly, but the bundled single-gate map renders both served vehicles at
one gate position — a multi-gate background is needed to animate them in separate lanes.

```text
GET /api/compare
```

Returns metrics-only results for every scenario (no frames) for side-by-side comparison. Results are deterministic and cached after the first build. The dashboard's "Compare scenarios" button renders this as a table plus bar charts.

## Demo Walkthrough

1. Start the local server and open the dashboard.
2. Begin with `baseline` and point out the entry queue, gate animation, search loop, parking occupancy, and exit flow.
3. Switch to `rush_hour` and compare entry queue pressure.
4. Switch to `limited_slots` and show denied vehicles plus the denied counters.
5. Switch to `slow_entry` or `exit_congestion` to isolate one bottleneck at a time.
6. Use the speed slider and replay button to revisit interesting moments.
7. Use the **Custom Inputs** panel to change vehicles, slots, gate counts, or service times live, then **Apply & run** (great for "what if we add a second gate?" questions).
8. Run `python3 -m unittest` to show the behavior is covered by automated tests.

## Documentation (CSE 10/L deliverables)

- `docs/REPORT.md`: Final report draft covering requirement items 1–5, 7, 8 (add a front cover, then export to PDF).
- `docs/flowchart.md`: Vehicle-lifecycle process diagram (Mermaid).
- `docs/architecture.md`: Conceptual DES model and software architecture diagrams (Mermaid).
- `docs/SLIDES_OUTLINE.md`: Slide-by-slide outline mapped to the required presentation sections.

## Limitations

- This is a local MVP, not a deployed production app.
- One replication per scenario (deterministic seed); no confidence intervals.
- There is no in-UI scenario editor, CSV export, authentication, or database.
- The model prioritizes readable class-review behavior over real-world traffic physics.
- The frontend is a static dashboard backed by the local FastAPI API.
