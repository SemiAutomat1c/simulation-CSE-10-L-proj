from __future__ import annotations

from dataclasses import dataclass
import random

import simpy


@dataclass(frozen=True)
class ParkingSimulationConfig:
    scenario: str = "baseline"
    snapshot_interval_minutes: float = 0.05
    # Optional live overrides (None = use the scenario profile's value).
    total_cars: int | None = None
    slot_count: int | None = None
    entry_service: float | None = None
    exit_service: float | None = None
    base_search: float | None = None
    seed: int | None = None
    entry_gates: int | None = None
    exit_gates: int | None = None


@dataclass(frozen=True)
class ParkingSlot:
    id: str
    row: int
    col: int
    x: float
    y: float
    slot_type: str
    angle: float = 0


@dataclass
class CarRecord:
    id: int
    vehicle_type: str
    arrival_time: float
    entry_queue_time: float | None = None
    approach_start: float | None = None
    gate_wait_start: float | None = None
    gate_cross_start: float | None = None
    search_start: float | None = None
    park_start: float | None = None
    exit_request: float | None = None
    slot_release_time: float | None = None
    exit_start: float | None = None
    exit_wait_start: float | None = None
    exit_merge_start: float | None = None
    exit_road_start: float | None = None
    done_time: float | None = None
    denied_time: float | None = None
    slot_id: str | None = None
    entrance: str = "south"  # "south" (default lane) or "north" (top lane, 2-entrance maps)
    two_entrance: bool = False  # True on 2-entrance maps; the "south" lane then uses the lower gate
    exit_lane: str = "single"  # "single" (default) or "top"/"bottom" (2-exit maps)


class ParkingSimulationResult:
    def __init__(
        self,
        scenario: str,
        slots: list[ParkingSlot],
        cars: list[CarRecord],
        frames: list[dict],
        metrics: dict,
        snapshot_interval_minutes: float,
    ) -> None:
        self.scenario = scenario
        self.slots = slots
        self.cars = cars
        self.frames = frames
        self.metrics = metrics
        self.snapshot_interval_minutes = snapshot_interval_minutes

    def to_dict(self) -> dict:
        return {
            "scenario": self.scenario,
            "timeline": {
                "snapshot_interval_minutes": self.snapshot_interval_minutes,
                "end_minute": self.frames[-1]["time_minutes"] if self.frames else 0,
            },
            "slots": [_slot_to_dict(slot) for slot in self.slots],
            "frames": self.frames,
            "metrics": self.metrics,
        }


SCENARIO_PROFILES = {
    "baseline": {
        "seed": 101,
        "total_cars": 44,
        "slot_count": 72,
        "arrival_mode": "spread",
        "entry_service": 0.7,
        "exit_service": 0.8,
        "base_search": 1.5,
    },
    "rush_hour": {
        "seed": 202,
        "total_cars": 60,
        "slot_count": 72,
        "arrival_mode": "clustered",
        "early_window": (0, 4),
        "cluster_window": (5, 18),
        "entry_service": 1.0,
        "exit_service": 0.95,
        "base_search": 1.9,
    },
    "limited_slots": {
        "seed": 303,
        "total_cars": 60,
        "slot_count": 16,
        "visible_slot_count": 72,
        "usable_slot_count": 16,
        "arrival_mode": "spread",
        "entry_service": 0.75,
        "exit_service": 0.85,
        "base_search": 1.9,
        "dwell_range": (46, 82),
    },
    "slow_entry": {
        "seed": 404,
        "total_cars": 50,
        "slot_count": 72,
        "arrival_mode": "spread",
        "arrival_start": 0,
        "arrival_end": 58,
        "entry_service": 3.2,
        "exit_service": 0.8,
        "base_search": 1.5,
    },
    "exit_congestion": {
        "seed": 505,
        "total_cars": 52,
        "slot_count": 72,
        "arrival_mode": "spread",
        "arrival_start": 0,
        "arrival_end": 62,
        "entry_service": 0.7,
        "exit_service": 4.0,
        "base_search": 1.6,
    },
    # Gate-layout configurations (rendered on dedicated maps). Gate counts are baked
    # into the profile so they affect the metrics; the animation keeps the shared lot.
    "two_entrance_two_exit": {
        "seed": 606,
        "total_cars": 56,
        "slot_count": 72,
        "arrival_mode": "spread",
        "arrival_start": 0,
        "arrival_end": 60,
        "entry_service": 1.0,
        "exit_service": 1.2,
        "base_search": 1.7,
        "entry_gates": 2,
        "exit_gates": 2,
    },
    "two_entrance_one_exit": {
        "seed": 707,
        "total_cars": 60,
        "slot_count": 72,
        "arrival_mode": "clustered",
        "early_window": (0, 4),
        "cluster_window": (5, 18),
        "entry_service": 1.0,
        "exit_service": 1.2,
        "base_search": 1.8,
        "entry_gates": 2,
        "exit_gates": 1,
    },
    "one_entrance_two_exit": {
        "seed": 808,
        "total_cars": 56,
        "slot_count": 72,
        "arrival_mode": "spread",
        "arrival_start": 0,
        "arrival_end": 60,
        "entry_service": 0.7,
        "exit_service": 2.6,
        "base_search": 1.6,
        "entry_gates": 1,
        "exit_gates": 2,
    },
}

ENTRY_LANE_X = 8.0
ENTRY_QUEUE_FRONT_Y = 88.0
ENTRY_QUEUE_SPACING = 4.8
ENTRY_PATH_BOTTOM_VISIBLE_Y = 88.0
ENTRY_MAIN_ENTRY_Y = 12.0
ENTRY_TURN_X = 25.0
ROW_A_DRIVE_Y = 35.0
ENTRY_GATE_Y = 29.5
ENTRY_STOP_LINE_Y = 36.0
ENTRY_GATE_QUEUE_FRONT_Y = ENTRY_STOP_LINE_Y + 6.0
MAIN_ROAD_Y = 55.7
# North (top) entrance, used only on two-entrance maps. Cars appear from the top
# edge, queue downward to the north gate, then merge into the upper drive lane.
NORTH_ENTRY_SPAWN_Y = -14.0
NORTH_ENTRY_STOP_LINE_Y = 18.0
NORTH_ENTRY_GATE_Y = 23.0
NORTH_ENTRY_HEAD_GAP = 4.0
# South (lower) entrance on two-entrance maps. Cars rise from the bottom edge,
# queue up to the lower gate (~64% down, aligned to the painted gate throat),
# stop, pass straight through, then turn right into the central search loop.
SOUTH_LOW_GATE_Y = 64.2
SOUTH_LOW_STOP_LINE_Y = 70.0
SOUTH_LOW_HEAD_GAP = 6.0
ENTRY_LANE_MIN_GAP = 6.4
DRIVING_LANE_MIN_GAP = 4.4
MOTORCYCLE_LANE_MIN_GAP = 2.6
ENTRY_QUEUE_FILL_MINUTES = 1.0
ENTRY_APPROACH_MINUTES = 0.5
ENTRY_GATE_PAUSE_MINUTES = 1.0
ENTRY_GATE_CROSS_MINUTES = 1.35
EXIT_APPROACH_MINUTES = 2.5
EXIT_QUEUE_APPROACH_MINUTES = 2.2
EXIT_GATE_PAUSE_MINUTES = 0.1
EXIT_MERGE_MINUTES = 1.5
EXIT_ROAD_DRIVE_MINUTES = 5.0
DENIED_EXIT_APPROACH_MINUTES = 2.5
EXIT_GATE_ROAD_Y = 48.5
# Single vertical exit queue, centered on the painted exit road (dashed line).
EXIT_QUEUE_LANE_X = 88.5
# Staging lane in the left half of the exit road: joining vehicles descend here
# and merge into the TAIL from the side, never driving through the cars in line.
EXIT_QUEUE_APPROACH_X = 85.5
# The column runs down the exit lane to the RIGHT of the hatched median island
# (which sits in the inside of the bend, ~x79-87/y72-85), then wraps left along
# the bottom road BELOW the median so no car ever sits on the median.
EXIT_QUEUE_COLUMN_BOTTOM_Y = 83.0
EXIT_QUEUE_WRAP_Y = 87.0
# Horizontal staging lane (above the wrap road) for joining the wrapped tail.
EXIT_QUEUE_APPROACH_Y = 85.0
# Descent lane for the horizontal approach, kept left of the median so
# approaching cars don't clip it or the cars on the bend.
EXIT_QUEUE_WRAP_APPROACH_X = 77.0
# A long wrap snakes into stacked rows instead of running into the entry queue:
# each row stops at LEFT_X (clear of the entry lane) and drops to the next row,
# alternating direction (boustrophedon).
EXIT_QUEUE_WRAP_LEFT_X = 15.0
EXIT_QUEUE_WRAP_RIGHT_X = 82.0
EXIT_QUEUE_WRAP_ROW_GAP = 5.0
EXIT_QUEUE_WRAP_ROWS = 3
EXIT_THROAT_POINT = (EXIT_QUEUE_LANE_X, EXIT_GATE_ROAD_Y)
EXIT_STOP_POINT = (EXIT_QUEUE_LANE_X, 41.0)
EXIT_GATE_BASE_POINT = (EXIT_STOP_POINT[0], EXIT_GATE_ROAD_Y)
EXIT_LEFT_TURN_POINT = (91.2, 45.6)
EXIT_RIGHT_TURN_POINT = (91.2, 58.9)
EXIT_ROAD_UP_X = 98.0
EXIT_ROAD_DOWN_X = 94.8
EXIT_ROAD_UP_ENTRY_Y = 48.0
EXIT_ROAD_DOWN_ENTRY_Y = 63.4
EXIT_ROAD_TOP_Y = -12.0
EXIT_ROAD_BOTTOM_Y = 112.0
EXIT_VERT_QUEUE_SPACING = 6.4
EXIT_HORIZ_QUEUE_SPACING = 6.4
# Two-exit maps: two parallel lanes either side of the road centre line, one
# climbing to the top exit and one dropping to the bottom exit, instead of the
# single middle column. The X offset keeps the columns from overlapping where
# they both reach toward the central lot.
EXIT_TOP_LANE_X = 86.8
EXIT_BOTTOM_LANE_X = 90.2
EXIT_TOP_STOP_Y = 28.0
EXIT_BOTTOM_STOP_Y = 72.0


def run_simulation(config: ParkingSimulationConfig) -> ParkingSimulationResult:
    scenario = config.scenario if config.scenario in SCENARIO_PROFILES else "baseline"
    base_profile = SCENARIO_PROFILES[scenario]
    profile = dict(base_profile)
    # Apply live overrides on top of the scenario profile.
    if config.total_cars is not None:
        profile["total_cars"] = config.total_cars
    if config.slot_count is not None:
        profile["slot_count"] = config.slot_count
        profile["visible_slot_count"] = config.slot_count
        profile["usable_slot_count"] = config.slot_count
    if config.entry_service is not None:
        profile["entry_service"] = config.entry_service
    if config.exit_service is not None:
        profile["exit_service"] = config.exit_service
    if config.base_search is not None:
        profile["base_search"] = config.base_search
    if config.seed is not None:
        profile["seed"] = config.seed
    entry_capacity = max(1, config.entry_gates or base_profile.get("entry_gates", 1))
    exit_capacity = max(1, config.exit_gates or base_profile.get("exit_gates", 1))
    rng = random.Random(profile["seed"])
    visible_slot_count = profile.get("visible_slot_count", profile["slot_count"])
    usable_slot_count = profile.get("usable_slot_count", profile["slot_count"])
    slots = _build_slots(visible_slot_count)
    usable_slot_ids = _usable_slot_ids(slots, usable_slot_count)
    free_car_slots = [slot_id for slot_id in _ordered_car_slot_ids(slots) if slot_id in usable_slot_ids]
    free_motorcycle_slots = [
        slot.id for slot in slots if slot.slot_type == "motorcycle_slot" and slot.id in usable_slot_ids
    ]
    cars = [
        CarRecord(
            id=index + 1,
            vehicle_type=_vehicle_type_for_index(index, rng),
            arrival_time=arrival,
        )
        for index, arrival in enumerate(_arrival_times(profile, rng))
    ]
    # On maps with two physical entrances, split arrivals between the top (north)
    # and the default (south) entry lanes so cars visibly appear at both.
    if base_profile.get("entry_gates", 1) >= 2:
        for index, car in enumerate(cars):
            car.entrance = "north" if index % 2 == 0 else "south"
            car.two_entrance = True
    # On maps with two exits, split departures between the top and bottom exit lanes.
    if base_profile.get("exit_gates", 1) >= 2:
        for index, car in enumerate(cars):
            car.exit_lane = "top" if index % 2 == 0 else "bottom"

    env = simpy.Environment()
    entry_gate = simpy.Resource(env, capacity=entry_capacity)
    exit_gate = simpy.Resource(env, capacity=exit_capacity)

    def car_process(car: CarRecord):
        yield env.timeout(car.arrival_time)
        car.entry_queue_time = env.now
        yield env.timeout(_approach_queue_time(rng))

        with entry_gate.request() as request:
            yield request
            car.approach_start = env.now
            yield env.timeout(ENTRY_APPROACH_MINUTES)
            car.gate_wait_start = env.now
            yield env.timeout(ENTRY_GATE_PAUSE_MINUTES + _service_time(profile["entry_service"], rng))

            slot_id = _reserve_slot(car.vehicle_type, free_car_slots, free_motorcycle_slots)
            if slot_id is not None:
                car.slot_id = slot_id
            car.gate_cross_start = env.now
            yield env.timeout(ENTRY_GATE_CROSS_MINUTES)

        if car.slot_id is None:
            car.denied_time = env.now
            yield env.timeout(DENIED_EXIT_APPROACH_MINUTES)

            car.exit_request = env.now
            yield env.timeout(EXIT_QUEUE_APPROACH_MINUTES)

            with exit_gate.request() as request:
                yield request
                car.exit_start = env.now
                yield env.timeout(EXIT_APPROACH_MINUTES)
                car.exit_wait_start = env.now
                yield env.timeout(EXIT_GATE_PAUSE_MINUTES + _service_time(profile["exit_service"], rng))
                car.exit_merge_start = env.now
                yield env.timeout(EXIT_MERGE_MINUTES)

            car.exit_road_start = env.now
            yield env.timeout(EXIT_ROAD_DRIVE_MINUTES)
            car.done_time = env.now
            return

        car.search_start = env.now
        free_slot_count = len(free_car_slots) + len(free_motorcycle_slots)
        occupancy_factor = 1 - (free_slot_count / max(len(slots), 1))
        search_time = profile["base_search"] + rng.uniform(0.4, 2.2) + occupancy_factor * 3.4
        yield env.timeout(search_time)

        car.park_start = env.now
        dwell_time = rng.uniform(*profile.get("dwell_range", (18, 44)))
        yield env.timeout(dwell_time)

        car.exit_request = env.now
        _release_slot(car, slots, free_car_slots, free_motorcycle_slots)
        yield env.timeout(EXIT_QUEUE_APPROACH_MINUTES)

        with exit_gate.request() as request:
            yield request
            car.exit_start = env.now
            yield env.timeout(EXIT_APPROACH_MINUTES)
            car.exit_wait_start = env.now
            yield env.timeout(EXIT_GATE_PAUSE_MINUTES + _service_time(profile["exit_service"], rng))
            car.exit_merge_start = env.now
            yield env.timeout(EXIT_MERGE_MINUTES)

        car.exit_road_start = env.now
        yield env.timeout(EXIT_ROAD_DRIVE_MINUTES)
        car.done_time = env.now

    for car in cars:
        env.process(car_process(car))

    env.run()
    frames = _build_frames(slots, cars, config.snapshot_interval_minutes, usable_slot_ids)
    metrics = _build_metrics(slots, cars, frames, usable_slot_ids, entry_capacity, exit_capacity)
    return ParkingSimulationResult(
        scenario=scenario,
        slots=slots,
        cars=cars,
        frames=frames,
        metrics=metrics,
        snapshot_interval_minutes=config.snapshot_interval_minutes,
    )


def _build_slots(slot_count: int) -> list[ParkingSlot]:
    slots: list[ParkingSlot] = []
    layout_points = _top_down_slot_layout()
    motorcycle_count = 12 if slot_count >= 72 else min(8, max(4, round(slot_count * 0.25)))
    car_points = [point for point in layout_points if point["slot_type"] == "car_slot"]
    motorcycle_points = [point for point in layout_points if point["slot_type"] == "motorcycle_slot"]
    car_count = slot_count - motorcycle_count
    selected_points = [
        {**car_points[index % len(car_points)], "slot_type": "car_slot"}
        for index in range(car_count)
    ] + [
        {**motorcycle_points[index % len(motorcycle_points)], "slot_type": "motorcycle_slot"}
        for index in range(motorcycle_count)
    ]
    for index, point in enumerate(selected_points):
        slots.append(
            ParkingSlot(
                id=f"P{index + 1:02d}",
                row=point["row"],
                col=point["col"],
                x=point["x"],
                y=point["y"],
                slot_type=point["slot_type"],
                angle=point["angle"],
            )
        )
    return slots


def _top_down_slot_layout() -> list[dict]:
    points: list[dict] = []

    def add_row(row: int, y: float, xs: list[float], angle: float, slot_type: str = "car_slot") -> None:
        for col, x in enumerate(xs):
            points.append({"row": row, "col": col, "x": x, "y": y, "angle": angle, "slot_type": slot_type})

    row_xs = [
        31.37, 33.56, 35.44, 37.32, 39.21, 41.09, 42.98, 44.83, 46.71, 48.60,
        50.45, 52.31, 54.16, 56.01, 57.87, 59.78, 61.70, 63.58, 65.49, 67.83
    ]
    add_row(0, 26.0, row_xs, 0)
    add_row(1, 43.8, row_xs, 0)
    add_row(2, 63.3, row_xs, 0)
    add_row(3, 14.4, [79.76, 81.46, 83.17, 84.87, 86.58, 88.31], 0, "motorcycle_slot")
    add_row(4, 24.5, [79.76, 81.46, 83.17, 84.87, 86.58, 88.31], 0, "motorcycle_slot")
    return points


def _ordered_car_slot_ids(slots: list[ParkingSlot]) -> list[str]:
    car_slots = [slot for slot in slots if slot.slot_type == "car_slot"]
    rows = sorted({slot.row for slot in car_slots})
    cols = sorted({slot.col for slot in car_slots})
    return [
        slot.id
        for col in cols
        for row in rows
        for slot in car_slots
        if slot.row == row and slot.col == col
    ]


def _usable_slot_ids(slots: list[ParkingSlot], usable_slot_count: int) -> set[str]:
    usable_count = min(max(usable_slot_count, 0), len(slots))
    if usable_count == 0:
        return set()

    motorcycle_count = 12 if usable_count >= 72 else min(8, max(4, round(usable_count * 0.25)))
    motorcycle_count = min(motorcycle_count, sum(1 for slot in slots if slot.slot_type == "motorcycle_slot"))
    car_count = min(usable_count - motorcycle_count, sum(1 for slot in slots if slot.slot_type == "car_slot"))

    usable_car_slots = _ordered_car_slot_ids(slots)[:car_count]
    usable_motorcycle_slots = [
        slot.id for slot in slots if slot.slot_type == "motorcycle_slot"
    ][:motorcycle_count]
    return set(usable_car_slots + usable_motorcycle_slots)


def _vehicle_type_for_index(index: int, rng: random.Random) -> str:
    if index % 7 == 3:
        return "motorcycle"
    return "motorcycle" if rng.random() < 0.08 else "car"


def _reserve_slot(
    vehicle_type: str,
    free_car_slots: list[str],
    free_motorcycle_slots: list[str],
) -> str | None:
    if vehicle_type == "motorcycle":
        if free_motorcycle_slots:
            return free_motorcycle_slots.pop(0)
        return None
    if free_car_slots:
        return free_car_slots.pop(0)
    return None


def _release_slot(
    car: CarRecord,
    slots: list[ParkingSlot],
    free_car_slots: list[str],
    free_motorcycle_slots: list[str],
) -> None:
    if car.slot_id is None or car.slot_release_time is not None:
        return

    car.slot_release_time = car.exit_request
    released_slot = next(slot for slot in slots if slot.id == car.slot_id)
    if released_slot.slot_type == "motorcycle_slot":
        free_motorcycle_slots.append(car.slot_id)
    else:
        free_car_slots.append(car.slot_id)


def _arrival_times(profile: dict, rng: random.Random) -> list[float]:
    total = profile["total_cars"]
    if profile["arrival_mode"] == "clustered":
        early_window = profile.get("early_window", (0, 16))
        cluster_window = profile.get("cluster_window", (18, 34))
        early = [rng.uniform(*early_window) for _ in range(total // 5)]
        cluster = [rng.uniform(*cluster_window) for _ in range(total - len(early))]
        return sorted(early + cluster)
    return sorted(rng.uniform(profile.get("arrival_start", 0), profile.get("arrival_end", 68)) for _ in range(total))


def _service_time(base: float, rng: random.Random) -> float:
    return max(0.2, base + rng.uniform(-0.18, 0.32))


def _approach_queue_time(rng: random.Random) -> float:
    return 1.0


def _build_frames(
    slots: list[ParkingSlot],
    cars: list[CarRecord],
    interval: float,
    usable_slot_ids: set[str],
) -> list[dict]:
    end_time = max(
        [car.done_time or car.denied_time or car.arrival_time for car in cars],
        default=0,
    ) + 4
    frame_count = int(end_time / interval) + 1
    frames = []
    for step in range(frame_count + 1):
        time_minutes = round(step * interval, 2)
        car_payload = [_car_to_frame(car, cars, slots, time_minutes) for car in cars]
        _apply_vehicle_spacing(car_payload)
        slot_payload = _slots_for_frame(slots, car_payload, usable_slot_ids)
        frames.append(
            {
                "time_minutes": time_minutes,
                "cars": car_payload,
                "slots": slot_payload,
                "entry_gate_open": any(_car_is_at_entry_gate(car) for car in car_payload),
                "exit_gate_open": any(_car_is_at_exit_gate(car, time_minutes) for car in cars),
                "current_entry_queue": sum(1 for car in car_payload if car["state"] == "entry_queue"),
                "current_exit_queue": sum(1 for car in car_payload if car["state"] == "exit_queue"),
                "parked_count": sum(1 for car in car_payload if car["state"] == "parked"),
                "available_slots": sum(1 for slot in slot_payload if slot["state"] == "free"),
                "denied_count": sum(1 for car in car_payload if car["state"] == "denied"),
                "completed_count": sum(1 for car in car_payload if car["state"] == "done"),
            }
        )
    return frames


def _apply_vehicle_spacing(car_payload: list[dict]) -> None:
    moving_states = {"entry_queue", "approaching_gate", "gate_wait", "gate_crossing", "searching", "exiting", "denied"}

    # Full entry lane (queue → approaching → gate_wait → gate_crossing): the car
    # closest to the gate (lowest y) is the leader. Followers are pushed further
    # from the gate (higher y). Covers the full vertical extent including the
    # off-screen queue below the map (no y-bound filter).
    _enforce_lane_spacing(
        car_payload,
        lambda car: car["state"] in {"entry_queue", "approaching_gate", "gate_wait", "gate_crossing"} and abs(car["x"] - ENTRY_LANE_X) <= 0.35,
        axis="y",
        direction=-1,
        minimum_gap=ENTRY_LANE_MIN_GAP,
    )
    _enforce_lane_spacing(
        car_payload,
        lambda car: car["state"] in moving_states and abs(car["y"] - MAIN_ROAD_Y) <= 0.25 and 8.0 <= car["x"] <= 88.0,
        axis="x",
        direction=1,
        minimum_gap=DRIVING_LANE_MIN_GAP,
    )
    _enforce_lane_spacing(
        car_payload,
        lambda car: car["state"] in moving_states and abs(car["y"] - 35.0) <= 0.25 and 24.0 <= car["x"] <= 86.0,
        axis="x",
        direction=1,
        minimum_gap=DRIVING_LANE_MIN_GAP,
    )
    _enforce_lane_spacing(
        car_payload,
        lambda car: car["state"] in moving_states and abs(car["y"] - 72.0) <= 0.25 and 31.0 <= car["x"] <= 78.0,
        axis="x",
        direction=-1,
        minimum_gap=DRIVING_LANE_MIN_GAP,
    )
    _enforce_lane_spacing(
        car_payload,
        lambda car: car["state"] in moving_states and abs(car["y"] - 78.5) <= 0.25 and 31.0 <= car["x"] <= 86.0,
        axis="x",
        direction=1,
        minimum_gap=DRIVING_LANE_MIN_GAP,
    )
    _enforce_lane_spacing(
        car_payload,
        lambda car: car["state"] in moving_states and abs(car["y"] - 20.0) <= 0.25 and 71.0 <= car["x"] <= 86.0,
        axis="x",
        direction=1,
        minimum_gap=MOTORCYCLE_LANE_MIN_GAP,
    )
    _enforce_lane_spacing(
        car_payload,
        lambda car: car["state"] in moving_states and abs(car["x"] - 72.0) <= 0.25 and 19.0 <= car["y"] <= MAIN_ROAD_Y,
        axis="y",
        direction=-1,
        minimum_gap=MOTORCYCLE_LANE_MIN_GAP,
    )
    _enforce_lane_spacing(
        car_payload,
        lambda car: car["state"] in moving_states and abs(car["x"] - 77.5) <= 0.25 and MAIN_ROAD_Y <= car["y"] <= 72.0,
        axis="y",
        direction=1,
        minimum_gap=DRIVING_LANE_MIN_GAP,
    )
    _enforce_lane_spacing(
        car_payload,
        lambda car: car["state"] in moving_states and abs(car["x"] - 85.0) <= 0.25 and 19.0 <= car["y"] <= MAIN_ROAD_Y,
        axis="y",
        direction=1,
        minimum_gap=DRIVING_LANE_MIN_GAP,
    )
    # Unified vertical exit queue on the exit road (above the wrap point).
    _enforce_lane_spacing(
        car_payload,
        lambda car: car["state"] == "exit_queue" and car.get("exit_lane", "single") == "single" and abs(car["x"] - EXIT_QUEUE_LANE_X) <= 1.0 and car["y"] >= EXIT_GATE_ROAD_Y,
        axis="y",
        direction=-1,
        minimum_gap=EXIT_VERT_QUEUE_SPACING,
    )
    # Two-exit maps: top column packs toward the top exit, bottom toward the bottom.
    _enforce_lane_spacing(
        car_payload,
        lambda car: car["state"] == "exit_queue" and car.get("exit_lane") == "top" and abs(car["x"] - EXIT_TOP_LANE_X) <= 1.5,
        axis="y",
        direction=-1,
        minimum_gap=EXIT_VERT_QUEUE_SPACING,
    )
    _enforce_lane_spacing(
        car_payload,
        lambda car: car["state"] == "exit_queue" and car.get("exit_lane") == "bottom" and abs(car["x"] - EXIT_BOTTOM_LANE_X) <= 1.5,
        axis="y",
        direction=1,
        minimum_gap=EXIT_VERT_QUEUE_SPACING,
    )
    # Wrapped exit queue running left along the bottom road (leader nearest corner).
    _enforce_lane_spacing(
        car_payload,
        lambda car: car["state"] == "exit_queue" and abs(car["y"] - EXIT_QUEUE_WRAP_Y) <= 1.0 and car["x"] <= EXIT_QUEUE_LANE_X - 3.0,
        axis="x",
        direction=1,
        minimum_gap=EXIT_HORIZ_QUEUE_SPACING,
    )
    # Approach descent lanes: when several cars request exit at once they stack
    # behind each other on the staging lane instead of overlapping.
    _enforce_lane_spacing(
        car_payload,
        lambda car: car["state"] == "exit_queue" and abs(car["x"] - EXIT_QUEUE_APPROACH_X) <= 0.75 and MAIN_ROAD_Y - 1.0 <= car["y"] <= EXIT_QUEUE_COLUMN_BOTTOM_Y + 1.0,
        axis="y",
        direction=1,
        minimum_gap=EXIT_VERT_QUEUE_SPACING,
    )
    _enforce_lane_spacing(
        car_payload,
        lambda car: car["state"] == "exit_queue" and abs(car["x"] - EXIT_QUEUE_WRAP_APPROACH_X) <= 0.75 and MAIN_ROAD_Y - 1.0 <= car["y"] <= EXIT_QUEUE_APPROACH_Y + 1.0,
        axis="y",
        direction=1,
        minimum_gap=EXIT_VERT_QUEUE_SPACING,
    )
    _enforce_lane_spacing(
        car_payload,
        lambda car: car["state"] == "exiting" and abs(car["x"] - EXIT_ROAD_UP_X) <= 0.35 and EXIT_ROAD_TOP_Y <= car["y"] <= EXIT_ROAD_UP_ENTRY_Y,
        axis="y",
        direction=-1,
        minimum_gap=DRIVING_LANE_MIN_GAP,
    )
    _enforce_lane_spacing(
        car_payload,
        lambda car: car["state"] == "exiting" and abs(car["x"] - EXIT_ROAD_DOWN_X) <= 0.35 and EXIT_ROAD_DOWN_ENTRY_Y <= car["y"] <= EXIT_ROAD_BOTTOM_Y,
        axis="y",
        direction=1,
        minimum_gap=DRIVING_LANE_MIN_GAP,
    )


def _enforce_lane_spacing(
    car_payload: list[dict],
    matcher,
    axis: str,
    direction: int,
    minimum_gap: float,
) -> None:
    lane_cars = [car for car in car_payload if matcher(car)]
    if len(lane_cars) < 2:
        return

    lane_cars.sort(key=lambda car: car[axis], reverse=direction > 0)
    leader = lane_cars[0]
    leader_gap = _vehicle_gap(leader)

    for follower in lane_cars[1:]:
        follower_gap = max(minimum_gap, _vehicle_gap(follower), leader_gap)
        if direction > 0:
            allowed = leader[axis] - follower_gap
            if follower[axis] > allowed:
                follower[axis] = allowed
        else:
            allowed = leader[axis] + follower_gap
            if follower[axis] < allowed:
                follower[axis] = allowed
        leader = follower
        leader_gap = _vehicle_gap(leader)


def _vehicle_gap(car_payload: dict) -> float:
    if car_payload["vehicle_type"] == "motorcycle":
        return MOTORCYCLE_LANE_MIN_GAP
    return DRIVING_LANE_MIN_GAP


def _car_to_frame(car: CarRecord, cars: list[CarRecord], slots: list[ParkingSlot], time_minutes: float) -> dict:
    state = _car_state(car, time_minutes)
    exit_phase = _exit_phase(car, time_minutes) if state == "exiting" else None
    x, y = _car_position(car, cars, slots, time_minutes, state)
    return {
        "id": car.id,
        "vehicle_type": car.vehicle_type,
        "state": state,
        "exit_phase": exit_phase,
        "slot_id": car.slot_id,
        "heading": _car_heading(car, cars, slots, state, time_minutes),
        "x": round(x, 2),
        "y": round(y, 2),
        "exit_lane": car.exit_lane,
    }


def _car_heading(car: CarRecord, cars: list[CarRecord], slots: list[ParkingSlot], state: str, time_minutes: float) -> float | None:
    slot = next((slot for slot in slots if slot.id == car.slot_id), None)
    if slot is not None and state == "parked":
        return slot.angle

    if state in {"entry_queue", "gate_wait"}:
        return 0.0

    if state not in {"approaching_gate", "gate_crossing", "searching", "exit_queue", "exiting", "denied"}:
        return None

    if state == "exiting" and _exit_phase(car, time_minutes) == "wait":
        return 90.0

    t_start = None
    t_end = None
    if state == "approaching_gate":
        t_start, t_end = car.approach_start, car.gate_wait_start
    elif state == "gate_crossing":
        t_start, t_end = car.gate_cross_start, car.search_start or car.denied_time
    elif state == "searching":
        t_start, t_end = car.search_start, car.park_start
    elif state == "exit_queue":
        t_start, t_end = car.exit_request, car.exit_start
    elif state == "exiting":
        t_start, t_end = car.exit_start, car.done_time
    elif state == "denied":
        t_start, t_end = car.denied_time, car.exit_request or car.done_time

    if t_start is None or t_end is None or t_end <= t_start:
        return None

    delta = 0.001
    if time_minutes + delta <= t_end:
        p1 = _car_position(car, cars, slots, time_minutes, state)
        p2 = _car_position(car, cars, slots, time_minutes + delta, state)
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
    elif time_minutes - delta >= t_start:
        p1 = _car_position(car, cars, slots, time_minutes - delta, state)
        p2 = _car_position(car, cars, slots, time_minutes, state)
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
    else:
        return None

    if abs(dx) + abs(dy) < 1e-5:
        if state == "exit_queue":
            # Vertical column faces the gate (up). Wrapped rows face the way they
            # advance, which alternates per snake row (right, then left, ...).
            pos = _car_position(car, cars, slots, time_minutes, state)
            if pos[1] > EXIT_QUEUE_COLUMN_BOTTOM_Y + 0.5:
                row = round((pos[1] - EXIT_QUEUE_WRAP_Y) / EXIT_QUEUE_WRAP_ROW_GAP)
                return 90.0 if row % 2 == 0 else 270.0
            return 0.0
        return slot.angle if slot is not None else 90.0

    # Snap to dominant axis for axis-aligned paths — prevents brief
    # diagonal headings when the delta straddles a corner waypoint.
    if abs(dx) > 0 and abs(dy) > 0:
        if abs(dx) >= abs(dy):
            dy = 0
        else:
            dx = 0

    import math
    angle = math.atan2(dy, dx) * (180.0 / math.pi) + 90.0
    return round(angle, 2)



def _car_state(car: CarRecord, time_minutes: float) -> str:
    if time_minutes < car.arrival_time:
        return "scheduled"
    if car.done_time is not None and time_minutes >= car.done_time:
        return "done"
    if car.exit_start is not None and time_minutes >= car.exit_start:
        return "exiting"
    if car.exit_request is not None and time_minutes >= car.exit_request:
        return "exit_queue"
    if car.denied_time is not None and time_minutes >= car.denied_time:
        return "denied"
    if car.park_start is not None and time_minutes >= car.park_start:
        return "parked"
    if car.search_start is not None and time_minutes >= car.search_start:
        return "searching"
    if car.gate_cross_start is not None and time_minutes >= car.gate_cross_start:
        return "gate_crossing"
    if car.gate_wait_start is not None and time_minutes >= car.gate_wait_start:
        return "gate_wait"
    if car.approach_start is not None and time_minutes >= car.approach_start:
        return "approaching_gate"
    return "entry_queue"


def _car_position(
    car: CarRecord,
    cars: list[CarRecord],
    slots: list[ParkingSlot],
    time_minutes: float,
    state: str,
) -> tuple[float, float]:
    slot = next((slot for slot in slots if slot.id == car.slot_id), None)
    slot_point = (slot.x, slot.y) if slot else (18, 82)
    search_start = _search_start_point(slot)
    offscreen = (106, 55.7)
    if state == "scheduled":
        return (ENTRY_LANE_X, NORTH_ENTRY_SPAWN_Y if car.entrance == "north" else 110)
    if state == "entry_queue":
        return _entry_queue_position(cars, car, time_minutes)
    if state == "approaching_gate":
        approach_start_point = _entry_queue_target_point(cars, car, car.approach_start or time_minutes)
        return _interpolate_path(_entry_approach_path(approach_start_point, car), car.approach_start, car.gate_wait_start, time_minutes)
    if state == "gate_wait":
        return _entry_stop_point(car)
    if state == "gate_crossing":
        return _interpolate_path(
            _gate_crossing_path(slot, car),
            car.gate_cross_start,
            car.search_start or car.denied_time,
            time_minutes,
        )
    if state == "searching":
        return _interpolate_path(_parking_path(slot, search_start, slot_point), car.search_start, car.park_start, time_minutes)
    if state == "parked":
        return slot_point
    if state == "exit_queue":
        return _exit_queue_position(car, cars, slot, slot_point, time_minutes)
    if state == "exiting":
        return _exit_position(car, cars, time_minutes)
    if state == "denied":
        denied_approach = [(25.0, MAIN_ROAD_Y), (EXIT_QUEUE_APPROACH_X, MAIN_ROAD_Y)]
        return _interpolate_path(denied_approach, car.denied_time, car.exit_request, time_minutes)
    return offscreen


def _entry_queue_position(cars: list[CarRecord], current_car: CarRecord, reference_time: float) -> tuple[float, float]:
    target = _entry_queue_target_point(cars, current_car, reference_time)
    spawn_y = NORTH_ENTRY_SPAWN_Y if current_car.entrance == "north" else 110
    if current_car.entry_queue_time is None:
        return (ENTRY_LANE_X, spawn_y)

    path = [(ENTRY_LANE_X, spawn_y)]
    if current_car.entrance != "north" and target[1] <= ENTRY_PATH_BOTTOM_VISIBLE_Y:
        path.append((ENTRY_LANE_X, ENTRY_PATH_BOTTOM_VISIBLE_Y))
    path.append(target)
    return _interpolate_path(
        path,
        current_car.entry_queue_time,
        current_car.entry_queue_time + ENTRY_QUEUE_FILL_MINUTES,
        reference_time,
    )


def _entry_queue_target_point(cars: list[CarRecord], current_car: CarRecord, reference_time: float) -> tuple[float, float]:
    queue_cars = [
        car
        for car in cars
        if car.arrival_time <= reference_time
        and car.entrance == current_car.entrance
        and (car.approach_start is None or car.approach_start > reference_time)
        and (car.denied_time is None or car.denied_time > reference_time)
        and (car.done_time is None or car.done_time > reference_time)
    ]
    queue_cars.sort(key=lambda car: (car.arrival_time, car.id))
    try:
        queue_idx = queue_cars.index(current_car)
    except ValueError:
        queue_idx = 0

    # Anchor right behind the stop line.  When the front car leaves the queue
    # (enters approaching_gate), every remaining car's queue_idx drops by 1 and
    # they advance forward naturally.  The spacing enforcer prevents overlaps.
    if current_car.entrance == "north":
        # North queue stacks upward toward the top spawn edge.
        lead_queue_y = NORTH_ENTRY_STOP_LINE_Y - NORTH_ENTRY_HEAD_GAP
        return (ENTRY_LANE_X, lead_queue_y - queue_idx * ENTRY_QUEUE_SPACING)
    if _is_lower_entrance(current_car):
        # Lower (south) gate: queue stacks downward toward the bottom spawn edge.
        lead_queue_y = SOUTH_LOW_STOP_LINE_Y + SOUTH_LOW_HEAD_GAP
        return (ENTRY_LANE_X, lead_queue_y + queue_idx * ENTRY_QUEUE_SPACING)
    head_gap = 6.0
    lead_queue_y = ENTRY_STOP_LINE_Y + head_gap
    return (ENTRY_LANE_X, lead_queue_y + queue_idx * ENTRY_QUEUE_SPACING)


def _entry_approach_path(queue_start: tuple[float, float], car: CarRecord) -> list[tuple[float, float]]:
    if car.entrance == "north":
        return [queue_start, _entry_stop_point(car)]
    if queue_start[1] <= ENTRY_PATH_BOTTOM_VISIBLE_Y:
        return [
            queue_start,
            _entry_stop_point(car),
        ]
    return [
        queue_start,
        (queue_start[0], ENTRY_PATH_BOTTOM_VISIBLE_Y),
        _entry_stop_point(car),
    ]


def _search_start_point(slot: ParkingSlot | None) -> tuple[float, float]:
    if slot is not None and slot.row == 0:
        return (ENTRY_TURN_X, ROW_A_DRIVE_Y)
    return (ENTRY_TURN_X, MAIN_ROAD_Y)


def _gate_crossing_path(slot: ParkingSlot | None = None, car: CarRecord | None = None) -> list[tuple[float, float]]:
    if car is not None and car.entrance == "north":
        # Cross the north gate, drop to the upper drive lane, then turn right into
        # the central search loop (no diagonal short-cut across the lot).
        return [
            _entry_stop_point(car),
            (ENTRY_LANE_X, NORTH_ENTRY_GATE_Y),
            (ENTRY_LANE_X, ROW_A_DRIVE_Y),
            (ENTRY_TURN_X, ROW_A_DRIVE_Y),
            _search_start_point(slot),
        ]
    if car is not None and _is_lower_entrance(car):
        # Cross the lower gate, rise to the main drive lane, then turn right into
        # the central search loop.
        return [
            _entry_stop_point(car),
            (ENTRY_LANE_X, SOUTH_LOW_GATE_Y),
            (ENTRY_LANE_X, MAIN_ROAD_Y),
            (ENTRY_TURN_X, MAIN_ROAD_Y),
            _search_start_point(slot),
        ]
    return [
        _entry_stop_point(car),
        (ENTRY_LANE_X, ENTRY_GATE_Y),
        (ENTRY_LANE_X, ENTRY_MAIN_ENTRY_Y),
        (ENTRY_TURN_X, ENTRY_MAIN_ENTRY_Y),
        _search_start_point(slot),
    ]


def _is_lower_entrance(car: CarRecord | None) -> bool:
    return car is not None and car.two_entrance and car.entrance == "south"


def _entry_stop_point(car: CarRecord | None = None) -> tuple[float, float]:
    if car is not None and car.entrance == "north":
        return (ENTRY_LANE_X, NORTH_ENTRY_STOP_LINE_Y)
    if _is_lower_entrance(car):
        return (ENTRY_LANE_X, SOUTH_LOW_STOP_LINE_Y)
    return (ENTRY_LANE_X, ENTRY_STOP_LINE_Y)


def _entry_active_position(car: CarRecord, cars: list[CarRecord], reference_time: float) -> tuple[float, float]:
    state = _car_state(car, reference_time)
    queue_start = _entry_queue_target_point(cars, car, car.approach_start or reference_time)
    if state == "approaching_gate":
        return _interpolate_path(_entry_approach_path(queue_start, car), car.approach_start, car.gate_wait_start, reference_time)
    if state == "gate_wait":
        return _entry_stop_point(car)
    if state == "gate_crossing":
        return _interpolate_path(_gate_crossing_path(None, car), car.gate_cross_start, car.search_start or car.denied_time, reference_time)
    return queue_start


def _car_is_at_entry_gate(car_payload: dict) -> bool:
    return car_payload["state"] == "gate_crossing"


def _car_is_at_exit_gate(car: CarRecord, reference_time: float) -> bool:
    return _exit_phase(car, reference_time) == "merge"


def _interpolate(
    start: tuple[float, float],
    end: tuple[float, float],
    start_time: float | None,
    end_time: float | None,
    now: float,
) -> tuple[float, float]:
    if start_time is None or end_time is None or end_time <= start_time:
        return end
    progress = min(1, max(0, (now - start_time) / (end_time - start_time)))
    return (
        start[0] + (end[0] - start[0]) * progress,
        start[1] + (end[1] - start[1]) * progress,
    )


def _parking_path(
    slot: ParkingSlot | None,
    search_start: tuple[float, float],
    slot_point: tuple[float, float],
) -> list[tuple[float, float]]:
    if slot is None:
        return [search_start, slot_point]
    if slot.slot_type == "motorcycle_slot":
        return [search_start, (72, 55.7), (72, 20), (slot.x, 20), slot_point]
    if slot.row == 0:
        return [search_start, (25, 35), (slot.x, 35), slot_point]
    if slot.row == 1:
        return [search_start, (slot.x, 55.7), slot_point]
    if slot.row == 2:
        return [search_start, (77.5, 55.7), (77.5, 72.0), (slot.x, 72.0), slot_point]
    return [search_start, (slot.x, 55.7), slot_point]


def _exit_queue_position(
    car: CarRecord,
    cars: list[CarRecord],
    slot: ParkingSlot | None,
    slot_point: tuple[float, float],
    time_minutes: float,
) -> tuple[float, float]:
    queue_target = _exit_queue_target_point(cars, car, time_minutes)
    queue_arrival = min(
        car.exit_start or car.done_time or time_minutes,
        (car.exit_request or time_minutes) + EXIT_QUEUE_APPROACH_MINUTES,
    )
    if time_minutes >= queue_arrival:
        return queue_target
    # Denied and parked vehicles share one approach: a single collector along the
    # main road that merges into the exit column at one join point (no crossing).
    is_denied = car.denied_time is not None and car.slot_id is None
    path = _slot_to_exit_queue_path(None if is_denied else slot, slot_point, queue_target, car)
    return _interpolate_path(
        path,
        car.exit_request,
        queue_arrival,
        time_minutes,
    )


def _exit_queue_path_points() -> list[tuple[float, float]]:
    """The polyline the exit queue follows: down the exit lane, around the corner,
    then snaking left/right along stacked bottom rows.  Each row stops at LEFT_X so
    it never runs into the entry queue, then drops to the next row below."""
    points = [
        (EXIT_QUEUE_LANE_X, EXIT_GATE_ROAD_Y),
        (EXIT_QUEUE_LANE_X, EXIT_QUEUE_COLUMN_BOTTOM_Y),
        (EXIT_QUEUE_LANE_X - EXIT_HORIZ_QUEUE_SPACING, EXIT_QUEUE_WRAP_Y),
    ]
    y = EXIT_QUEUE_WRAP_Y
    going_left = True
    for _ in range(EXIT_QUEUE_WRAP_ROWS):
        end_x = EXIT_QUEUE_WRAP_LEFT_X if going_left else EXIT_QUEUE_WRAP_RIGHT_X
        points.append((end_x, y))            # run to the end of this row
        y += EXIT_QUEUE_WRAP_ROW_GAP
        points.append((end_x, y))            # drop to the next row
        going_left = not going_left
    return points


def _point_along_polyline(points: list[tuple[float, float]], distance: float) -> tuple[float, float]:
    """Point at the given arc-length distance along a polyline.  Past the end it
    keeps going in the last segment's direction (rare extreme overflow)."""
    if distance <= 0:
        return points[0]
    for start, end in zip(points, points[1:]):
        seg = _distance(start, end)
        if seg <= 0:
            continue
        if distance <= seg:
            t = distance / seg
            return (start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t)
        distance -= seg
    start, end = points[-2], points[-1]
    seg = _distance(start, end) or 1.0
    ux, uy = (end[0] - start[0]) / seg, (end[1] - start[1]) / seg
    return (end[0] + ux * distance, end[1] + uy * distance)


def _exit_stop_point(car: CarRecord | None = None) -> tuple[float, float]:
    if car is not None and car.exit_lane == "top":
        return (EXIT_TOP_LANE_X, EXIT_TOP_STOP_Y)
    if car is not None and car.exit_lane == "bottom":
        return (EXIT_BOTTOM_LANE_X, EXIT_BOTTOM_STOP_Y)
    return EXIT_STOP_POINT


def _exit_queue_slot_point(index: int, car: CarRecord | None = None) -> tuple[float, float]:
    """Position of the Nth car in the exit queue, by arc length along the queue
    polyline.  Arc-length placement keeps consecutive slots one spacing apart even
    around the bend and snake turns, so advancing cars hug the path."""
    if car is not None and car.exit_lane == "top":
        # Lane left of centre, climbing to the top exit; cars stack downward.
        return (EXIT_TOP_LANE_X, EXIT_TOP_STOP_Y + index * EXIT_VERT_QUEUE_SPACING)
    if car is not None and car.exit_lane == "bottom":
        # Lane right of centre, dropping to the bottom exit; cars stack upward.
        return (EXIT_BOTTOM_LANE_X, EXIT_BOTTOM_STOP_Y - index * EXIT_VERT_QUEUE_SPACING)
    return _point_along_polyline(_exit_queue_path_points(), index * EXIT_VERT_QUEUE_SPACING)


def _exit_queue_target_point(cars: list[CarRecord], current_car: CarRecord, reference_time: float) -> tuple[float, float]:
    """Unified exit queue: a vertical column on the exit road that wraps left
    along the bottom road when it would otherwise run off the map."""
    queue_cars = [
        car
        for car in cars
        if car.exit_request is not None
        and car.exit_request <= reference_time
        and car.exit_lane == current_car.exit_lane
        and (car.exit_start is None or car.exit_start > reference_time)
        and (car.done_time is None or car.done_time > reference_time)
    ]
    queue_cars.sort(key=lambda car: (car.exit_request or 0, car.id))
    try:
        queue_idx = queue_cars.index(current_car)
    except ValueError:
        queue_idx = 0

    # While the front car is still pulling out of the head slot toward the gate
    # (its "approach" phase), hold the rest of the queue back by one slot so the
    # next car doesn't advance into space the exiting car hasn't vacated yet.
    # The car doing the exiting must not count itself, or it would start its
    # approach one slot too far back.
    throat_busy = any(
        car.id != current_car.id
        and car.exit_lane == current_car.exit_lane
        and car.exit_start is not None
        and car.exit_start <= reference_time
        and (car.exit_wait_start is None or car.exit_wait_start > reference_time)
        for car in cars
    )
    offset = 1 if throat_busy else 0
    return _exit_queue_slot_point(queue_idx + offset, current_car)


def _exit_queue_merge_path(queue_target: tuple[float, float]) -> list[tuple[float, float]]:
    """Final approach from the main-road collector into the tail of the queue,
    merging from the side so the joining car never drives through the line.

    Vertical tail: descend the staging lane (left of the column), step right in.
    Wrapped tail: descend the staging lane to the horizontal staging lane (above
    the bottom road), run left to the tail column, then drop into the slot.
    """
    tx, ty = queue_target
    if ty <= EXIT_QUEUE_COLUMN_BOTTOM_Y + 0.01:
        return [
            (EXIT_QUEUE_APPROACH_X, MAIN_ROAD_Y),
            (EXIT_QUEUE_APPROACH_X, ty),
            queue_target,
        ]
    return [
        (EXIT_QUEUE_WRAP_APPROACH_X, MAIN_ROAD_Y),
        (EXIT_QUEUE_WRAP_APPROACH_X, EXIT_QUEUE_APPROACH_Y),
        (tx, EXIT_QUEUE_APPROACH_Y),
        queue_target,
    ]


def _slot_to_exit_queue_path(
    slot: ParkingSlot | None,
    slot_point: tuple[float, float],
    queue_target: tuple[float, float],
    car: CarRecord | None = None,
) -> list[tuple[float, float]]:
    """Funnel every vehicle onto the main-road collector, then down a staging
    lane into the TAIL of the exit column.  All exiting vehicles share this single
    stream so denied and parked cars form one line without crossing, and a joining
    vehicle merges into the back from the side instead of driving through the line.

    Right-edge connector lanes (x=85 from the top rows, x=77.5 from the bottom
    row) are reused to reach the main road; see _apply_vehicle_spacing.
    """
    # Two-exit maps: reach the exit lane on the main road, then go straight to the
    # tail of the top/bottom column (no shared staging lane).
    if car is not None and car.exit_lane in ("top", "bottom"):
        lane_x = EXIT_TOP_LANE_X if car.exit_lane == "top" else EXIT_BOTTOM_LANE_X
        merge = [(lane_x, MAIN_ROAD_Y), queue_target]
    else:
        merge = _exit_queue_merge_path(queue_target)
    # Denied vehicles are already coasting along the main road toward the column.
    if slot is None:
        return merge
    if slot.slot_type == "motorcycle_slot":
        return [slot_point, (slot.x, 20), (85.0, 20), (85.0, MAIN_ROAD_Y), *merge]
    if slot.row == 0:
        return [slot_point, (slot.x, 35), (85.0, 35), (85.0, MAIN_ROAD_Y), *merge]
    if slot.row == 1:
        return [slot_point, (slot.x, MAIN_ROAD_Y), *merge]
    if slot.row == 2:
        return [slot_point, (slot.x, 72.0), (77.5, 72.0), (77.5, MAIN_ROAD_Y), *merge]
    return [slot_point, (slot.x, MAIN_ROAD_Y), *merge]


def _exit_approach_path(car: CarRecord, cars: list[CarRecord]) -> list[tuple[float, float]]:
    queue_start = _exit_queue_target_point(cars, car, car.exit_start or 0)
    if car.exit_lane in ("top", "bottom"):
        return [queue_start, _exit_stop_point(car)]
    return [queue_start, EXIT_GATE_BASE_POINT, EXIT_STOP_POINT]


def _exit_merge_path(car: CarRecord) -> list[tuple[float, float]]:
    if car.exit_lane in ("top", "bottom"):
        stop = _exit_stop_point(car)
        road_x = EXIT_ROAD_UP_X if car.exit_lane == "top" else EXIT_ROAD_DOWN_X
        return [stop, (road_x, stop[1])]
    direction = _exit_direction(car)
    if direction == "up":
        return [
            EXIT_STOP_POINT,
            (EXIT_ROAD_UP_X, EXIT_STOP_POINT[1]),
        ]
    return [
        EXIT_STOP_POINT,
        (EXIT_ROAD_DOWN_X, EXIT_STOP_POINT[1]),
        (EXIT_ROAD_DOWN_X, EXIT_ROAD_DOWN_ENTRY_Y),
    ]


def _outside_road_path(car: CarRecord) -> list[tuple[float, float]]:
    if car.exit_lane == "top":
        sy = _exit_stop_point(car)[1]
        return [(EXIT_ROAD_UP_X, sy), (EXIT_ROAD_UP_X, 14.0), (EXIT_ROAD_UP_X, EXIT_ROAD_TOP_Y)]
    if car.exit_lane == "bottom":
        sy = _exit_stop_point(car)[1]
        return [(EXIT_ROAD_DOWN_X, sy), (EXIT_ROAD_DOWN_X, 90.0), (EXIT_ROAD_DOWN_X, EXIT_ROAD_BOTTOM_Y)]
    direction = _exit_direction(car)
    if direction == "up":
        return [
            (EXIT_ROAD_UP_X, EXIT_STOP_POINT[1]),
            (EXIT_ROAD_UP_X, 24.0),
            (EXIT_ROAD_UP_X, EXIT_ROAD_TOP_Y),
        ]
    return [
        (EXIT_ROAD_DOWN_X, EXIT_ROAD_DOWN_ENTRY_Y),
        (EXIT_ROAD_DOWN_X, 86.0),
        (EXIT_ROAD_DOWN_X, EXIT_ROAD_BOTTOM_Y),
    ]


def _exit_direction(car: CarRecord) -> str:
    if car.exit_lane == "top":
        return "up"
    if car.exit_lane == "bottom":
        return "down"
    return "up" if car.id % 2 else "down"


def _exit_phase(car: CarRecord, reference_time: float) -> str | None:
    if car.exit_start is None or reference_time < car.exit_start:
        return None
    if car.done_time is not None and reference_time >= car.done_time:
        return None
    if car.exit_wait_start is None or reference_time < car.exit_wait_start:
        return "approach"
    if car.exit_merge_start is None or reference_time < car.exit_merge_start:
        return "wait"
    if car.exit_road_start is None or reference_time < car.exit_road_start:
        return "merge"
    return "road"


def _exit_position(
    car: CarRecord,
    cars: list[CarRecord],
    time_minutes: float,
) -> tuple[float, float]:
    phase = _exit_phase(car, time_minutes)
    if phase == "approach":
        return _interpolate_path(
            _exit_approach_path(car, cars),
            car.exit_start,
            car.exit_wait_start,
            time_minutes,
        )
    if phase == "wait":
        return _exit_stop_point(car)
    if phase == "merge":
        return _interpolate_path(
            _exit_merge_path(car),
            car.exit_merge_start,
            car.exit_road_start,
            time_minutes,
        )
    return _interpolate_path(
        _outside_road_path(car),
        car.exit_road_start,
        car.done_time,
        time_minutes,
    )


def _interpolate_path(
    points: list[tuple[float, float]],
    start_time: float | None,
    end_time: float | None,
    now: float,
) -> tuple[float, float]:
    if start_time is None or end_time is None or end_time <= start_time or len(points) < 2:
        return points[-1]

    total_distance = sum(_distance(start, end) for start, end in zip(points, points[1:]))
    if total_distance <= 0:
        return points[-1]

    progress = min(1, max(0, (now - start_time) / (end_time - start_time)))
    target_distance = total_distance * progress
    covered = 0.0
    for start, end in zip(points, points[1:]):
        segment_distance = _distance(start, end)
        if covered + segment_distance >= target_distance:
            segment_progress = (target_distance - covered) / max(segment_distance, 0.001)
            return _point_between(start, end, segment_progress)
        covered += segment_distance
    return points[-1]


def _distance(start: tuple[float, float], end: tuple[float, float]) -> float:
    return ((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5


def _point_between(
    start: tuple[float, float],
    end: tuple[float, float],
    progress: float,
) -> tuple[float, float]:
    return (
        start[0] + (end[0] - start[0]) * progress,
        start[1] + (end[1] - start[1]) * progress,
    )


def _slots_for_frame(slots: list[ParkingSlot], car_payload: list[dict], usable_slot_ids: set[str]) -> list[dict]:
    slot_states = {slot.id: "free" if slot.id in usable_slot_ids else "unavailable" for slot in slots}
    for car in car_payload:
        slot_id = car["slot_id"]
        if slot_id is None:
            continue
        if slot_id not in usable_slot_ids:
            continue
        if car["state"] == "searching":
            slot_states[slot_id] = "targeted"
        elif car["state"] == "parked":
            slot_states[slot_id] = "occupied"
    return [
        {
            **_slot_to_dict(slot),
            "state": slot_states[slot.id],
        }
        for slot in slots
    ]


def _slot_to_dict(slot: ParkingSlot) -> dict:
    return {
        "id": slot.id,
        "row": slot.row,
        "col": slot.col,
        "slot_type": slot.slot_type,
        "angle": slot.angle,
        "x": slot.x,
        "y": slot.y,
    }


def _build_metrics(
    slots: list[ParkingSlot],
    cars: list[CarRecord],
    frames: list[dict],
    usable_slot_ids: set[str],
    entry_capacity: int = 1,
    exit_capacity: int = 1,
) -> dict:
    search_times = [
        car.park_start - car.search_start
        for car in cars
        if car.park_start is not None and car.search_start is not None
    ]
    max_occupied = max(
        (
            sum(1 for slot in frame["slots"] if slot["state"] in {"targeted", "occupied", "exiting"})
            for frame in frames
        ),
        default=0,
    )
    peak_car_slots = max(
        (
            sum(
                1
                for slot in frame["slots"]
                if slot["slot_type"] == "car_slot" and slot["state"] in {"targeted", "occupied", "exiting"}
            )
            for frame in frames
        ),
        default=0,
    )
    peak_motorcycle_slots = max(
        (
            sum(
                1
                for slot in frame["slots"]
                if slot["slot_type"] == "motorcycle_slot"
                and slot["state"] in {"targeted", "occupied", "exiting"}
            )
            for frame in frames
        ),
        default=0,
    )
    car_slot_count = sum(1 for slot in slots if slot.slot_type == "car_slot" and slot.id in usable_slot_ids)
    motorcycle_slot_count = sum(
        1 for slot in slots if slot.slot_type == "motorcycle_slot" and slot.id in usable_slot_ids
    )
    total_cars = sum(1 for car in cars if car.vehicle_type == "car")
    total_motorcycles = sum(1 for car in cars if car.vehicle_type == "motorcycle")

    # --- Discrete-event performance metrics (derived from per-vehicle timestamps) ---
    def _avg(values: list[float]) -> float:
        return round(sum(values) / len(values), 2) if values else 0.0

    # Waiting time = time spent in a queue before the gate begins serving the vehicle.
    entry_waits = [
        car.approach_start - car.entry_queue_time
        for car in cars
        if car.approach_start is not None and car.entry_queue_time is not None
    ]
    exit_waits = [
        car.exit_start - car.exit_request
        for car in cars
        if car.exit_start is not None and car.exit_request is not None
    ]
    # Processing (service) time = time the gate actively serves the vehicle.
    entry_services = [
        car.gate_cross_start - car.gate_wait_start
        for car in cars
        if car.gate_cross_start is not None and car.gate_wait_start is not None
    ]
    exit_services = [
        car.exit_merge_start - car.exit_wait_start
        for car in cars
        if car.exit_merge_start is not None and car.exit_wait_start is not None
    ]
    # Cycle time = total time in the system, arrival to departure.
    time_in_system = [
        car.done_time - car.arrival_time
        for car in cars
        if car.done_time is not None
    ]

    completed_vehicles = sum(1 for car in cars if car.done_time is not None and car.slot_id is not None)
    end_minute = max((frame["time_minutes"] for frame in frames), default=0.0) or 0.0
    throughput_per_hour = round(completed_vehicles / (end_minute / 60.0), 2) if end_minute > 0 else 0.0

    # Resource utilisation = busy server-time / available server-time (capacity-aware).
    entry_busy = sum(
        (car.search_start if car.search_start is not None else car.denied_time) - car.approach_start
        for car in cars
        if car.approach_start is not None
        and (car.search_start is not None or car.denied_time is not None)
    )
    exit_busy = sum(
        car.exit_road_start - car.exit_start
        for car in cars
        if car.exit_road_start is not None and car.exit_start is not None
    )
    entry_gate_util = round(min(entry_busy / (end_minute * entry_capacity), 1.0) * 100, 1) if end_minute > 0 else 0.0
    exit_gate_util = round(min(exit_busy / (end_minute * exit_capacity), 1.0) * 100, 1) if end_minute > 0 else 0.0

    avg_entry_queue = round(sum(f["current_entry_queue"] for f in frames) / len(frames), 2) if frames else 0.0
    avg_exit_queue = round(sum(f["current_exit_queue"] for f in frames) / len(frames), 2) if frames else 0.0

    return {
        "total_vehicle_count": len(cars),
        "total_cars": total_cars,
        "total_motorcycles": total_motorcycles,
        "total_slots": len(usable_slot_ids),
        "visible_slot_count": len(slots),
        "total_car_slots": car_slot_count,
        "total_motorcycle_slots": motorcycle_slot_count,
        "total_completed_cars": sum(
            1 for car in cars if car.vehicle_type == "car" and car.done_time is not None and car.slot_id is not None
        ),
        "total_completed_vehicles": sum(1 for car in cars if car.done_time is not None and car.slot_id is not None),
        "denied_cars": sum(1 for car in cars if car.vehicle_type == "car" and car.denied_time is not None),
        "denied_motorcycles": sum(
            1 for car in cars if car.vehicle_type == "motorcycle" and car.denied_time is not None
        ),
        "denied_vehicle_count": sum(1 for car in cars if car.denied_time is not None),
        "average_search_time_minutes": round(sum(search_times) / len(search_times), 2) if search_times else 0,
        "max_entry_queue_length": max((frame["current_entry_queue"] for frame in frames), default=0),
        "max_exit_queue_length": max((frame["current_exit_queue"] for frame in frames), default=0),
        "peak_occupied_slots": max_occupied,
        "occupancy_rate_percent": round((max_occupied / max(len(usable_slot_ids), 1)) * 100, 1),
        "car_slot_occupancy_percent": round((peak_car_slots / max(car_slot_count, 1)) * 100, 1),
        "motorcycle_slot_occupancy_percent": round(
            (peak_motorcycle_slots / max(motorcycle_slot_count, 1)) * 100,
            1,
        ),
        "exit_completion_time_minutes": round(max((car.done_time or 0 for car in cars), default=0), 1),
        # Discrete-event performance metrics (rubric item 7).
        "average_entry_wait_minutes": _avg(entry_waits),
        "average_exit_wait_minutes": _avg(exit_waits),
        "average_wait_minutes": _avg(entry_waits + exit_waits),
        "average_entry_service_minutes": _avg(entry_services),
        "average_exit_service_minutes": _avg(exit_services),
        "average_time_in_system_minutes": _avg(time_in_system),
        "throughput_vehicles_per_hour": throughput_per_hour,
        "entry_gate_utilization_percent": entry_gate_util,
        "exit_gate_utilization_percent": exit_gate_util,
        "entry_gate_count": entry_capacity,
        "exit_gate_count": exit_capacity,
        "average_entry_queue_length": avg_entry_queue,
        "average_exit_queue_length": avg_exit_queue,
    }
