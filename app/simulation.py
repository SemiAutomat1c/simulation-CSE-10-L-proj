from __future__ import annotations

from dataclasses import dataclass
import random

import simpy


@dataclass(frozen=True)
class ParkingSimulationConfig:
    scenario: str = "baseline"
    snapshot_interval_minutes: float = 0.05


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
    exit_start: float | None = None
    exit_wait_start: float | None = None
    exit_merge_start: float | None = None
    exit_road_start: float | None = None
    done_time: float | None = None
    denied_time: float | None = None
    slot_id: str | None = None


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
        "total_cars": 56,
        "slot_count": 72,
        "arrival_mode": "clustered",
        "entry_service": 0.8,
        "exit_service": 0.85,
        "base_search": 1.8,
    },
    "limited_slots": {
        "seed": 303,
        "total_cars": 48,
        "slot_count": 16,
        "arrival_mode": "spread",
        "entry_service": 0.75,
        "exit_service": 0.85,
        "base_search": 1.9,
    },
    "slow_entry": {
        "seed": 404,
        "total_cars": 44,
        "slot_count": 72,
        "arrival_mode": "spread",
        "entry_service": 1.8,
        "exit_service": 0.8,
        "base_search": 1.5,
    },
    "exit_congestion": {
        "seed": 505,
        "total_cars": 46,
        "slot_count": 72,
        "arrival_mode": "spread",
        "entry_service": 0.7,
        "exit_service": 2.4,
        "base_search": 1.6,
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
ENTRY_LANE_MIN_GAP = 6.4
DRIVING_LANE_MIN_GAP = 4.4
MOTORCYCLE_LANE_MIN_GAP = 2.6
ENTRY_QUEUE_FILL_MINUTES = 1.0
ENTRY_APPROACH_MINUTES = 0.5
ENTRY_GATE_PAUSE_MINUTES = 1.0
ENTRY_GATE_CROSS_MINUTES = 1.35
EXIT_APPROACH_MINUTES = 2.5
EXIT_GATE_PAUSE_MINUTES = 0.1
EXIT_MERGE_MINUTES = 1.5
EXIT_ROAD_DRIVE_MINUTES = 5.0
EXIT_GATE_ROAD_Y = 48.5
EXIT_THROAT_POINT = (85.0, EXIT_GATE_ROAD_Y)
EXIT_STOP_POINT = (89.0, 41.0)
EXIT_GATE_BASE_POINT = (EXIT_STOP_POINT[0], EXIT_GATE_ROAD_Y)
EXIT_LEFT_TURN_POINT = (91.2, 45.6)
EXIT_RIGHT_TURN_POINT = (91.2, 58.9)
EXIT_ROAD_UP_X = 98.0
EXIT_ROAD_DOWN_X = 94.8
EXIT_ROAD_UP_ENTRY_Y = 48.0
EXIT_ROAD_DOWN_ENTRY_Y = 63.4
EXIT_ROAD_TOP_Y = -12.0
EXIT_ROAD_BOTTOM_Y = 112.0


def run_simulation(config: ParkingSimulationConfig) -> ParkingSimulationResult:
    scenario = config.scenario if config.scenario in SCENARIO_PROFILES else "baseline"
    profile = SCENARIO_PROFILES[scenario]
    rng = random.Random(profile["seed"])
    slots = _build_slots(profile["slot_count"])
    free_car_slots = _ordered_car_slot_ids(slots)
    free_motorcycle_slots = [slot.id for slot in slots if slot.slot_type == "motorcycle_slot"]
    cars = [
        CarRecord(
            id=index + 1,
            vehicle_type=_vehicle_type_for_index(index, rng),
            arrival_time=arrival,
        )
        for index, arrival in enumerate(_arrival_times(profile, rng))
    ]

    env = simpy.Environment()
    entry_gate = simpy.Resource(env, capacity=1)
    exit_gate = simpy.Resource(env, capacity=1)

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
            yield env.timeout(4.0)
            car.done_time = env.now
            return

        car.search_start = env.now
        free_slot_count = len(free_car_slots) + len(free_motorcycle_slots)
        occupancy_factor = 1 - (free_slot_count / max(len(slots), 1))
        search_time = profile["base_search"] + rng.uniform(0.4, 2.2) + occupancy_factor * 3.4
        yield env.timeout(search_time)

        car.park_start = env.now
        dwell_time = rng.uniform(18, 44)
        yield env.timeout(dwell_time)

        car.exit_request = env.now
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
        if car.slot_id is not None:
            released_slot = next(slot for slot in slots if slot.id == car.slot_id)
            if released_slot.slot_type == "motorcycle_slot":
                free_motorcycle_slots.append(car.slot_id)
            else:
                free_car_slots.append(car.slot_id)

    for car in cars:
        env.process(car_process(car))

    env.run()
    frames = _build_frames(slots, cars, config.snapshot_interval_minutes)
    metrics = _build_metrics(slots, cars, frames)
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


def _arrival_times(profile: dict, rng: random.Random) -> list[float]:
    total = profile["total_cars"]
    if profile["arrival_mode"] == "clustered":
        early = [rng.uniform(0, 16) for _ in range(total // 4)]
        cluster = [rng.uniform(18, 34) for _ in range(total - len(early))]
        return sorted(early + cluster)
    return sorted(rng.uniform(0, 68) for _ in range(total))


def _service_time(base: float, rng: random.Random) -> float:
    return max(0.2, base + rng.uniform(-0.18, 0.32))


def _approach_queue_time(rng: random.Random) -> float:
    return 1.0


def _build_frames(slots: list[ParkingSlot], cars: list[CarRecord], interval: float) -> list[dict]:
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
        slot_payload = _slots_for_frame(slots, car_payload)
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
    }


def _car_heading(car: CarRecord, cars: list[CarRecord], slots: list[ParkingSlot], state: str, time_minutes: float) -> float | None:
    slot = next((slot for slot in slots if slot.id == car.slot_id), None)
    if slot is not None and state in {"parked", "exit_queue"}:
        return slot.angle

    if state in {"entry_queue", "gate_wait"}:
        return 0.0

    if state not in {"approaching_gate", "gate_crossing", "searching", "exiting", "denied"}:
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
    elif state == "exiting":
        t_start, t_end = car.exit_start, car.done_time
    elif state == "denied":
        t_start, t_end = car.denied_time, car.done_time

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
    if car.denied_time is not None and time_minutes >= car.denied_time:
        return "denied"
    if car.exit_start is not None and time_minutes >= car.exit_start:
        return "exiting"
    if car.exit_request is not None and time_minutes >= car.exit_request:
        return "exit_queue"
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
        return (ENTRY_LANE_X, 110)
    if state == "entry_queue":
        return _entry_queue_position(cars, car, time_minutes)
    if state == "approaching_gate":
        approach_start_point = _entry_queue_target_point(cars, car, car.approach_start or time_minutes)
        return _interpolate_path(_entry_approach_path(approach_start_point), car.approach_start, car.gate_wait_start, time_minutes)
    if state == "gate_wait":
        return _entry_stop_point()
    if state == "gate_crossing":
        return _interpolate_path(
            _gate_crossing_path(slot),
            car.gate_cross_start,
            car.search_start or car.denied_time,
            time_minutes,
        )
    if state == "searching":
        return _interpolate_path(_parking_path(slot, search_start, slot_point), car.search_start, car.park_start, time_minutes)
    if state in {"parked", "exit_queue"}:
        return slot_point
    if state == "exiting":
        return _exit_position(car, slot, slot_point, time_minutes)
    if state == "denied":
        denied_path = [(25.0, 55.7), (88.0, 55.7), (100.0, 55.7)]
        return _interpolate_path(denied_path, car.denied_time, car.done_time, time_minutes)
    return offscreen


def _entry_queue_position(cars: list[CarRecord], current_car: CarRecord, reference_time: float) -> tuple[float, float]:
    target = _entry_queue_target_point(cars, current_car, reference_time)
    if current_car.entry_queue_time is None:
        return (ENTRY_LANE_X, 110)

    path = [(ENTRY_LANE_X, 110)]
    if target[1] <= ENTRY_PATH_BOTTOM_VISIBLE_Y:
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
    head_gap = 6.0
    lead_queue_y = ENTRY_STOP_LINE_Y + head_gap
    return (ENTRY_LANE_X, lead_queue_y + queue_idx * ENTRY_QUEUE_SPACING)


def _entry_approach_path(queue_start: tuple[float, float]) -> list[tuple[float, float]]:
    if queue_start[1] <= ENTRY_PATH_BOTTOM_VISIBLE_Y:
        return [
            queue_start,
            _entry_stop_point(),
        ]
    return [
        queue_start,
        (queue_start[0], ENTRY_PATH_BOTTOM_VISIBLE_Y),
        _entry_stop_point(),
    ]


def _search_start_point(slot: ParkingSlot | None) -> tuple[float, float]:
    if slot is not None and slot.row == 0:
        return (ENTRY_TURN_X, ROW_A_DRIVE_Y)
    return (ENTRY_TURN_X, MAIN_ROAD_Y)


def _gate_crossing_path(slot: ParkingSlot | None = None) -> list[tuple[float, float]]:
    return [
        _entry_stop_point(),
        (ENTRY_LANE_X, ENTRY_GATE_Y),
        (ENTRY_LANE_X, ENTRY_MAIN_ENTRY_Y),
        (ENTRY_TURN_X, ENTRY_MAIN_ENTRY_Y),
        _search_start_point(slot),
    ]


def _entry_stop_point() -> tuple[float, float]:
    return (ENTRY_LANE_X, ENTRY_STOP_LINE_Y)


def _entry_active_position(car: CarRecord, cars: list[CarRecord], reference_time: float) -> tuple[float, float]:
    state = _car_state(car, reference_time)
    queue_start = _entry_queue_target_point(cars, car, car.approach_start or reference_time)
    if state == "approaching_gate":
        return _interpolate_path(_entry_approach_path(queue_start), car.approach_start, car.gate_wait_start, reference_time)
    if state == "gate_wait":
        return _entry_stop_point()
    if state == "gate_crossing":
        return _interpolate_path(_gate_crossing_path(), car.gate_cross_start, car.search_start or car.denied_time, reference_time)
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


def _exit_approach_path(
    car: CarRecord,
    slot: ParkingSlot | None,
    slot_point: tuple[float, float],
) -> list[tuple[float, float]]:
    lot_exit_path: list[tuple[float, float]]
    if slot is None:
        lot_exit_path = [slot_point, EXIT_THROAT_POINT, EXIT_GATE_BASE_POINT, EXIT_STOP_POINT]
    elif slot.slot_type == "motorcycle_slot":
        lot_exit_path = [slot_point, (slot.x, 20), (85.0, 20), EXIT_THROAT_POINT, EXIT_GATE_BASE_POINT, EXIT_STOP_POINT]
    elif slot.row == 0:
        lot_exit_path = [slot_point, (slot.x, 35), (85.0, 35), EXIT_THROAT_POINT, EXIT_GATE_BASE_POINT, EXIT_STOP_POINT]
    elif slot.row == 1:
        lot_exit_path = [slot_point, (slot.x, EXIT_GATE_ROAD_Y), EXIT_THROAT_POINT, EXIT_GATE_BASE_POINT, EXIT_STOP_POINT]
    elif slot.row == 2:
        lot_exit_path = [slot_point, (slot.x, 78.5), (85.0, 78.5), EXIT_THROAT_POINT, EXIT_GATE_BASE_POINT, EXIT_STOP_POINT]
    else:
        lot_exit_path = [slot_point, (slot.x, EXIT_GATE_ROAD_Y), EXIT_THROAT_POINT, EXIT_GATE_BASE_POINT, EXIT_STOP_POINT]

    return lot_exit_path


def _exit_merge_path(car: CarRecord) -> list[tuple[float, float]]:
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
    slot: ParkingSlot | None,
    slot_point: tuple[float, float],
    time_minutes: float,
) -> tuple[float, float]:
    phase = _exit_phase(car, time_minutes)
    if phase == "approach":
        return _interpolate_path(
            _exit_approach_path(car, slot, slot_point),
            car.exit_start,
            car.exit_wait_start,
            time_minutes,
        )
    if phase == "wait":
        return EXIT_STOP_POINT
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


def _slots_for_frame(slots: list[ParkingSlot], car_payload: list[dict]) -> list[dict]:
    slot_states = {slot.id: "free" for slot in slots}
    for car in car_payload:
        slot_id = car["slot_id"]
        if slot_id is None:
            continue
        if car["state"] == "searching":
            slot_states[slot_id] = "targeted"
        elif car["state"] in {"parked", "exit_queue"}:
            slot_states[slot_id] = "occupied"
        elif car["state"] == "exiting":
            slot_states[slot_id] = "exiting"
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


def _build_metrics(slots: list[ParkingSlot], cars: list[CarRecord], frames: list[dict]) -> dict:
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
    car_slot_count = sum(1 for slot in slots if slot.slot_type == "car_slot")
    motorcycle_slot_count = sum(1 for slot in slots if slot.slot_type == "motorcycle_slot")
    total_cars = sum(1 for car in cars if car.vehicle_type == "car")
    total_motorcycles = sum(1 for car in cars if car.vehicle_type == "motorcycle")
    return {
        "total_vehicle_count": len(cars),
        "total_cars": total_cars,
        "total_motorcycles": total_motorcycles,
        "total_slots": len(slots),
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
        "occupancy_rate_percent": round((max_occupied / max(len(slots), 1)) * 100, 1),
        "car_slot_occupancy_percent": round((peak_car_slots / max(car_slot_count, 1)) * 100, 1),
        "motorcycle_slot_occupancy_percent": round(
            (peak_motorcycle_slots / max(motorcycle_slot_count, 1)) * 100,
            1,
        ),
        "exit_completion_time_minutes": round(max((car.done_time or 0 for car in cars), default=0), 1),
    }
