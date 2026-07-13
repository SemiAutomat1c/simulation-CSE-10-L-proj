"""Compact and expand parking simulation timelines.

Converts dense full-frame simulation dicts into a delta-keyframe wire format
and back into full-shaped playback frames.
"""

from __future__ import annotations

from typing import Any

# Vehicle dynamic fields: short key -> full key
_VEHICLE_DELTA_KEYS: tuple[tuple[str, str], ...] = (
    ("s", "state"),
    ("x", "x"),
    ("y", "y"),
    ("h", "heading"),
    ("p", "exit_phase"),
    ("sid", "slot_id"),
    ("qa", "queue_arrived"),
)

_ROSTER_KEYS: tuple[str, ...] = (
    "id",
    "vehicle_type",
    "exit_lane",
    "exit_layout",
    "entrance",
)


def compact_simulation(full: dict, *, max_gap_minutes: float = 0.25) -> dict:
    """Encode a full simulation result dict into the compact wire format."""
    frames: list[dict] = full["frames"]
    keep_indices = _select_keyframe_indices(frames, max_gap_minutes)
    roster = _build_roster(frames)

    keyframes: list[dict] = []
    prev_car_state: dict[int, dict[str, Any]] = {}
    prev_slot_state: dict[str, str] = {}

    for i in keep_indices:
        frame = frames[i]
        kf = {
            "t": frame["time_minutes"],
            "g": {
                "e": bool(frame["entry_gate_open"]),
                "x": bool(frame["exit_gate_open"]),
            },
            "q": {
                "e": int(frame["current_entry_queue"]),
                "x": int(frame["current_exit_queue"]),
                "p": int(frame["parked_count"]),
                "a": int(frame["available_slots"]),
                "d": int(frame["denied_count"]),
                "c": int(frame["completed_count"]),
            },
            "s": {},
            "v": {},
        }

        # Slot state deltas (stable order by slot id)
        current_slots = {slot["id"]: slot["state"] for slot in frame["slots"]}
        for slot_id in sorted(current_slots):
            state = current_slots[slot_id]
            if prev_slot_state.get(slot_id) != state:
                kf["s"][slot_id] = state
        prev_slot_state = current_slots

        # Vehicle deltas (stable order by vehicle id)
        cars_sorted = sorted(frame["cars"], key=lambda c: c["id"])
        for car in cars_sorted:
            car_id = car["id"]
            current = _vehicle_dynamic_state(car)
            prev = prev_car_state.get(car_id)
            if prev is None:
                # First time seen (always includes every car on first keyframe)
                delta = {short: current[full_key] for short, full_key in _VEHICLE_DELTA_KEYS}
            else:
                delta = {
                    short: current[full_key]
                    for short, full_key in _VEHICLE_DELTA_KEYS
                    if prev.get(full_key) != current[full_key]
                }
            if delta:
                kf["v"][str(car_id)] = delta
            prev_car_state[car_id] = current

        keyframes.append(kf)

    timeline = full.get("timeline") or {}
    return {
        "format": "compact",
        "scenario": full["scenario"],
        "defaults": full.get("defaults", {}),
        "timeline": {
            "snapshot_interval_minutes": timeline.get("snapshot_interval_minutes"),
            "end_minute": timeline.get(
                "end_minute",
                frames[-1]["time_minutes"] if frames else 0,
            ),
            "keyframe_max_gap_minutes": max_gap_minutes,
        },
        "slots": full["slots"],
        "roster": roster,
        "keyframes": keyframes,
        "metrics": full["metrics"],
    }


def expand_simulation(compact: dict) -> dict:
    """Decode compact wire format into a full-shaped result with keyframe frames."""
    roster: list[dict] = compact.get("roster") or []
    roster_by_id = {entry["id"]: entry for entry in roster}

    # Cumulative dynamic vehicle state; static props come from roster at emit time.
    car_state: dict[int, dict[str, Any]] = {}
    # Static layout + cumulative state
    slot_layout = {slot["id"]: dict(slot) for slot in (compact.get("slots") or [])}
    slot_state: dict[str, str] = {
        slot_id: layout.get("state", "free") for slot_id, layout in slot_layout.items()
    }

    frames: list[dict] = []
    for kf in compact.get("keyframes") or []:
        for id_str, delta in (kf.get("v") or {}).items():
            car_id = int(id_str)
            prev = car_state.get(car_id)
            if prev is None:
                next_state: dict[str, Any] = {}
            else:
                next_state = dict(prev)
            for short, full_key in _VEHICLE_DELTA_KEYS:
                if short in delta:
                    next_state[full_key] = delta[short]
            car_state[car_id] = next_state

        for sid, state in (kf.get("s") or {}).items():
            slot_state[sid] = state

        cars: list[dict] = []
        # Emit cars in stable id order for determinism
        known_ids = set(car_state) | set(roster_by_id)
        for car_id in sorted(known_ids):
            roster_entry = roster_by_id.get(car_id, {"id": car_id})
            dynamic = car_state.get(car_id)
            if dynamic is None:
                cars.append(
                    {
                        **{k: roster_entry.get(k) for k in _ROSTER_KEYS if k in roster_entry},
                        "id": car_id,
                        "state": "scheduled",
                        "x": 0,
                        "y": 0,
                        "heading": None,
                        "slot_id": None,
                        "exit_phase": None,
                        "queue_arrived": False,
                    }
                )
            else:
                car = {k: roster_entry[k] for k in _ROSTER_KEYS if k in roster_entry}
                car["id"] = car_id
                for _, full_key in _VEHICLE_DELTA_KEYS:
                    if full_key in dynamic:
                        car[full_key] = dynamic[full_key]
                cars.append(car)

        slots = []
        for slot_id in sorted(slot_layout):
            layout = slot_layout[slot_id]
            slots.append({**layout, "state": slot_state.get(slot_id, layout.get("state", "free"))})
        # Preserve original top-level slot order if present
        if compact.get("slots"):
            order = {slot["id"]: idx for idx, slot in enumerate(compact["slots"])}
            slots.sort(key=lambda s: order.get(s["id"], 10**9))

        g = kf.get("g") or {}
        q = kf.get("q") or {}
        frames.append(
            {
                "time_minutes": kf["t"],
                "cars": cars,
                "slots": slots,
                "entry_gate_open": bool(g.get("e")),
                "exit_gate_open": bool(g.get("x")),
                "current_entry_queue": int(q.get("e", 0)),
                "current_exit_queue": int(q.get("x", 0)),
                "parked_count": int(q.get("p", 0)),
                "available_slots": int(q.get("a", 0)),
                "denied_count": int(q.get("d", 0)),
                "completed_count": int(q.get("c", 0)),
            }
        )

    timeline = compact.get("timeline") or {}
    return {
        "scenario": compact.get("scenario"),
        "defaults": compact.get("defaults", {}),
        "timeline": {
            "snapshot_interval_minutes": timeline.get("snapshot_interval_minutes"),
            "end_minute": timeline.get("end_minute"),
        },
        "slots": compact.get("slots", []),
        "frames": frames,
        "metrics": compact.get("metrics"),
    }


def _vehicle_dynamic_state(car: dict) -> dict[str, Any]:
    return {
        "state": car.get("state"),
        "x": car.get("x"),
        "y": car.get("y"),
        "heading": car.get("heading"),
        "exit_phase": car.get("exit_phase"),
        "slot_id": car.get("slot_id"),
        "queue_arrived": car.get("queue_arrived"),
    }


def _build_roster(frames: list[dict]) -> list[dict]:
    """Static per-vehicle props, first-seen, ordered by vehicle id."""
    seen: dict[int, dict] = {}
    for frame in frames:
        for car in frame["cars"]:
            car_id = car["id"]
            if car_id in seen:
                continue
            seen[car_id] = {
                "id": car_id,
                "vehicle_type": car.get("vehicle_type"),
                "exit_lane": car.get("exit_lane"),
                "exit_layout": car.get("exit_layout"),
                "entrance": car.get("entrance"),
            }
    return [seen[i] for i in sorted(seen)]


def _select_keyframe_indices(frames: list[dict], max_gap_minutes: float) -> list[int]:
    """Pick frame indices to keep as keyframes."""
    if not frames:
        return []

    n = len(frames)
    keep: list[int] = [0]
    last_car_sig = _car_discrete_signatures(frames[0])
    last_gates = (
        bool(frames[0]["entry_gate_open"]),
        bool(frames[0]["exit_gate_open"]),
    )
    last_time = float(frames[0]["time_minutes"])

    for i in range(1, n):
        frame = frames[i]
        is_last = i == n - 1
        gates = (bool(frame["entry_gate_open"]), bool(frame["exit_gate_open"]))
        car_sig = _car_discrete_signatures(frame)
        time_minutes = float(frame["time_minutes"])
        gap = time_minutes - last_time

        discrete_changed = car_sig != last_car_sig
        gates_changed = gates != last_gates
        gap_exceeded = gap >= max_gap_minutes

        if is_last or discrete_changed or gates_changed or gap_exceeded:
            keep.append(i)
            last_car_sig = car_sig
            last_gates = gates
            last_time = time_minutes

    return keep


def _car_discrete_signatures(frame: dict) -> tuple:
    """Comparable signature of discrete car fields used for keyframe selection."""
    return tuple(
        (car["id"], car.get("state"), car.get("exit_phase"), car.get("slot_id"))
        for car in sorted(frame["cars"], key=lambda c: c["id"])
    )
