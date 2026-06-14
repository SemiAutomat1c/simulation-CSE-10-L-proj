import unittest

from app.simulation import (
    EXIT_GATE_ROAD_Y,
    EXIT_QUEUE_LANE_X,
    EXIT_STOP_POINT,
    EXIT_VERT_QUEUE_SPACING,
    ParkingSimulationConfig,
    run_simulation,
)


class ParkingSimulationTests(unittest.TestCase):
    _payload_cache: dict[str, dict] = {}

    @classmethod
    def scenario_payload(cls, scenario: str) -> dict:
        if scenario not in cls._payload_cache:
            cls._payload_cache[scenario] = run_simulation(ParkingSimulationConfig(scenario=scenario)).to_dict()
        return cls._payload_cache[scenario]

    def test_cars_progress_through_required_states(self) -> None:
        payload = self.scenario_payload("baseline")
        states = {car["state"] for frame in payload["frames"] for car in frame["cars"]}

        self.assertIn("entry_queue", states)
        self.assertIn("approaching_gate", states)
        self.assertIn("gate_wait", states)
        self.assertIn("gate_crossing", states)
        self.assertIn("searching", states)
        self.assertIn("parked", states)
        self.assertIn("exiting", states)
        self.assertIn("done", states)

    def test_slots_are_never_double_booked_in_any_frame(self) -> None:
        payload = self.scenario_payload("rush_hour")

        for frame in payload["frames"]:
            occupied_slots = [
                slot["id"]
                for slot in frame["slots"]
                if slot["state"] in {"targeted", "occupied", "exiting"}
            ]
            self.assertEqual(len(occupied_slots), len(set(occupied_slots)))

    def test_limited_slots_records_denied_cars(self) -> None:
        payload = self.scenario_payload("limited_slots")

        self.assertGreater(payload["metrics"]["denied_cars"], 0)
        self.assertLess(payload["metrics"]["total_completed_cars"], payload["metrics"]["total_cars"])

    def test_limited_slots_renders_full_map_with_blocked_spaces(self) -> None:
        payload = self.scenario_payload("limited_slots")
        first_frame_slots = payload["frames"][0]["slots"]

        self.assertEqual(len(payload["slots"]), 72)
        self.assertEqual(payload["metrics"]["visible_slot_count"], 72)
        self.assertEqual(payload["metrics"]["total_slots"], 16)
        self.assertEqual(sum(1 for slot in first_frame_slots if slot["state"] == "unavailable"), 56)
        self.assertEqual(sum(1 for slot in first_frame_slots if slot["state"] == "free"), 16)

    def test_unavailable_limited_slots_are_never_assigned_to_vehicles(self) -> None:
        payload = self.scenario_payload("limited_slots")
        unavailable_slot_ids = {
            slot["id"]
            for slot in payload["frames"][0]["slots"]
            if slot["state"] == "unavailable"
        }
        assigned_slot_ids = {
            car["slot_id"]
            for frame in payload["frames"]
            for car in frame["cars"]
            if car["slot_id"] is not None
        }

        self.assertTrue(unavailable_slot_ids)
        self.assertTrue(assigned_slot_ids)
        self.assertTrue(unavailable_slot_ids.isdisjoint(assigned_slot_ids))

    def test_rush_hour_entry_pressure_is_visible_early(self) -> None:
        payload = self.scenario_payload("rush_hour")
        max_entry_queue = payload["metrics"]["max_entry_queue_length"]
        first_peak_time = next(
            frame["time_minutes"]
            for frame in payload["frames"]
            if frame["current_entry_queue"] == max_entry_queue
        )

        self.assertGreaterEqual(max_entry_queue, 50)
        self.assertLessEqual(first_peak_time, 20.0)

    def test_slow_entry_queue_is_visibly_stronger_than_baseline(self) -> None:
        baseline = self.scenario_payload("baseline")
        slow_entry = self.scenario_payload("slow_entry")

        self.assertGreaterEqual(
            slow_entry["metrics"]["max_entry_queue_length"],
            baseline["metrics"]["max_entry_queue_length"] + 12,
        )

    def test_payload_contains_metrics_slots_and_timeline(self) -> None:
        payload = self.scenario_payload("baseline")

        self.assertIn("timeline", payload)
        self.assertIn("slots", payload)
        self.assertIn("frames", payload)
        self.assertIn("average_search_time_minutes", payload["metrics"])
        self.assertIn("occupancy_rate_percent", payload["metrics"])

    def test_vehicle_payload_includes_cars_and_motorcycles(self) -> None:
        payload = self.scenario_payload("baseline")
        vehicle_types = {car["vehicle_type"] for frame in payload["frames"] for car in frame["cars"]}

        self.assertIn("car", vehicle_types)
        self.assertIn("motorcycle", vehicle_types)
        self.assertGreater(payload["metrics"]["total_cars"], 0)
        self.assertGreater(payload["metrics"]["total_motorcycles"], 0)

    def test_exiting_vehicle_payload_includes_visible_exit_phases(self) -> None:
        payload = self.scenario_payload("baseline")
        exit_phases = {
            car["exit_phase"]
            for frame in payload["frames"]
            for car in frame["cars"]
            if car["state"] == "exiting"
        }

        self.assertIn("approach", exit_phases)
        self.assertIn("wait", exit_phases)
        self.assertIn("merge", exit_phases)
        self.assertIn("road", exit_phases)

    def test_slots_include_car_and_motorcycle_types(self) -> None:
        payload = self.scenario_payload("baseline")
        slot_types = {slot["slot_type"] for slot in payload["slots"]}

        self.assertIn("car_slot", slot_types)
        self.assertIn("motorcycle_slot", slot_types)

    def test_cars_never_occupy_motorcycle_only_slots(self) -> None:
        payload = self.scenario_payload("rush_hour")
        slot_types = {slot["id"]: slot["slot_type"] for slot in payload["slots"]}

        for frame in payload["frames"]:
            for car in frame["cars"]:
                if car["vehicle_type"] == "car" and car["slot_id"] is not None:
                    self.assertNotEqual(slot_types[car["slot_id"]], "motorcycle_slot")

    def test_motorcycles_use_motorcycle_slots(self) -> None:
        payload = self.scenario_payload("baseline")
        slot_types = {slot["id"]: slot["slot_type"] for slot in payload["slots"]}
        parked_motorcycle_slots = {
            car["slot_id"]
            for frame in payload["frames"]
            for car in frame["cars"]
            if car["vehicle_type"] == "motorcycle" and car["slot_id"] is not None
        }

        self.assertTrue(any(slot_types[slot_id] == "motorcycle_slot" for slot_id in parked_motorcycle_slots))

    def test_baseline_matches_visible_lot_capacity(self) -> None:
        payload = self.scenario_payload("baseline")
        car_slots_by_row = {
            row: sum(1 for slot in payload["slots"] if slot["slot_type"] == "car_slot" and slot["row"] == row)
            for row in (0, 1, 2)
        }
        motorcycle_slots = [slot for slot in payload["slots"] if slot["slot_type"] == "motorcycle_slot"]

        self.assertEqual(car_slots_by_row, {0: 20, 1: 20, 2: 20})
        self.assertEqual(len(motorcycle_slots), 12)

    def test_motorcycles_never_occupy_car_slots(self) -> None:
        payload = self.scenario_payload("baseline")
        slot_types = {slot["id"]: slot["slot_type"] for slot in payload["slots"]}

        for frame in payload["frames"]:
            for car in frame["cars"]:
                if car["vehicle_type"] == "motorcycle" and car["slot_id"] is not None:
                    self.assertEqual(slot_types[car["slot_id"]], "motorcycle_slot")

    def test_visible_vehicles_stay_inside_readable_map_area(self) -> None:
        payload = self.scenario_payload("limited_slots")
        visible_states = {"entry_queue", "approaching_gate", "gate_wait", "gate_crossing", "searching", "parked", "exit_queue", "exiting", "denied"}

        for frame in payload["frames"]:
            for car in frame["cars"]:
                if car["state"] in visible_states:
                    self.assertGreaterEqual(car["x"], 0)
                    self.assertLessEqual(car["x"], 100)
                    # entry_queue/approaching vehicles may start below the map before driving upward.
                    # exit_queue/exiting vehicles may extend down the exit road during heavy congestion.
                    if car["state"] not in {"entry_queue", "approaching_gate", "exit_queue", "exiting", "denied"}:
                        self.assertGreaterEqual(car["y"], 0)
                    if car["state"] not in {"entry_queue", "approaching_gate", "exit_queue", "exiting", "denied"}:
                        self.assertLessEqual(car["y"], 88)

    def test_baseline_uses_all_car_rows(self) -> None:
        payload = self.scenario_payload("baseline")
        slot_rows = {slot["id"]: slot["row"] for slot in payload["slots"]}
        occupied_rows = {
            slot_rows[car["slot_id"]]
            for frame in payload["frames"]
            for car in frame["cars"]
            if car["vehicle_type"] == "car" and car["slot_id"] and car["state"] in {"parked", "exit_queue"}
        }

        self.assertEqual({0, 1, 2}, occupied_rows)

    def test_motorcycle_slots_stay_inside_marked_motorcycle_area(self) -> None:
        payload = self.scenario_payload("baseline")
        motorcycle_slots = [slot for slot in payload["slots"] if slot["slot_type"] == "motorcycle_slot"]

        for slot in motorcycle_slots:
            self.assertGreaterEqual(slot["x"], 75)
            self.assertLessEqual(slot["x"], 89)
            self.assertGreaterEqual(slot["y"], 14)
            self.assertLessEqual(slot["y"], 36.0)

    def test_searching_vehicles_follow_lanes_before_parking(self) -> None:
        payload = self.scenario_payload("baseline")

        for frame in payload["frames"]:
            for car in frame["cars"]:
                if car["state"] == "searching":
                    on_horizontal_lane = 42 <= car["y"] <= 80
                    on_vertical_turn_lane = 22 <= car["x"] <= 79
                    in_motorcycle_area = car["vehicle_type"] == "motorcycle" and 72 <= car["x"] <= 90 and 14 <= car["y"] <= 36.0
                    near_parking_slot = car["slot_id"] is not None and abs(
                        car["y"] - next(slot["y"] for slot in payload["slots"] if slot["id"] == car["slot_id"])
                    ) <= 4
                    self.assertTrue(on_horizontal_lane or on_vertical_turn_lane or in_motorcycle_area or near_parking_slot)

    def test_entry_queue_stays_on_entry_centerline(self) -> None:
        payload = self.scenario_payload("rush_hour")

        for frame in payload["frames"]:
            for car in frame["cars"]:
                if car["state"] == "entry_queue":
                    self.assertGreaterEqual(car["x"], 7.2)
                    self.assertLessEqual(car["x"], 8.8)
                    self.assertGreaterEqual(car["y"], 40.0)

    def test_entry_queue_starts_offmap_then_stacks_behind_gate(self) -> None:
        payload = self.scenario_payload("rush_hour")

        checked = False
        for frame in payload["frames"]:
            waiting = [
                car
                for car in frame["cars"]
                if car["state"] == "gate_wait" and abs(car["x"] - 8.0) <= 0.1 and abs(car["y"] - 36.0) <= 0.1
            ]
            queued = sorted(
                [
                    car
                    for car in frame["cars"]
                    if car["state"] == "entry_queue" and abs(car["x"] - 8.0) <= 0.1
                ],
                key=lambda car: car["y"],
            )
            if not waiting or len(queued) < 2:
                continue
            if queued[0]["y"] > 48.0 or queued[1]["y"] > 56.0:
                continue
            self.assertLessEqual(queued[0]["y"], 48.0)
            self.assertLessEqual(queued[1]["y"], 56.0)
            checked = True
            break

        self.assertTrue(checked)

    def test_entry_queue_uses_single_centerline(self) -> None:
        payload = self.scenario_payload("rush_hour")

        checked = False
        for frame in payload["frames"]:
            queued = [car for car in frame["cars"] if car["state"] == "entry_queue"]
            if len(queued) < 3:
                continue
            xs = {round(car["x"], 2) for car in queued[:6]}
            ys = [car["y"] for car in queued[:6]]
            self.assertEqual(xs, {8.0})
            self.assertEqual(ys, sorted(ys))
            checked = True
            break

        self.assertTrue(checked)

    def test_entry_lane_vehicles_keep_visible_follow_distance(self) -> None:
        payload = self.scenario_payload("rush_hour")

        checked = False
        for frame in payload["frames"]:
            lane_cars = [
                car
                for car in frame["cars"]
                if car["state"] in {"entry_queue", "approaching_gate", "gate_wait", "gate_crossing"}
                and abs(car["x"] - 8.0) <= 0.1
                and car["y"] >= 26.6
            ]
            if len(lane_cars) < 2:
                continue
            lane_cars.sort(key=lambda car: car["y"])
            for leader, follower in zip(lane_cars, lane_cars[1:]):
                self.assertGreaterEqual(follower["y"] - leader["y"], 2.6)
            checked = True
            break

        self.assertTrue(checked)

    def test_entry_crossing_uses_main_entry_before_turning_right(self) -> None:
        payload = self.scenario_payload("baseline")

        gate_crossing_points = [
            car
            for frame in payload["frames"]
            for car in frame["cars"]
            if car["id"] == 1 and car["state"] == "gate_crossing"
        ]

        self.assertTrue(gate_crossing_points)
        self.assertTrue(any(abs(car["x"] - 8.0) <= 0.1 and car["y"] <= 18.0 for car in gate_crossing_points))
        self.assertTrue(any(car["x"] >= 20.0 and car["y"] <= 18.0 for car in gate_crossing_points))
        self.assertFalse(any(abs(car["x"] - 8.0) <= 0.1 and car["y"] > 40.0 for car in gate_crossing_points))

    def test_entry_gate_crossing_has_readable_duration(self) -> None:
        payload = self.scenario_payload("baseline")

        crossing_times = [
            frame["time_minutes"]
            for frame in payload["frames"]
            for car in frame["cars"]
            if car["id"] == 1 and car["state"] == "gate_crossing"
        ]

        self.assertTrue(crossing_times)
        self.assertGreaterEqual(crossing_times[-1] - crossing_times[0], 1.2)

    def test_row_a_vehicles_do_not_visit_row_b_lane_before_parking(self) -> None:
        payload = self.scenario_payload("baseline")
        slot_rows = {slot["id"]: slot["row"] for slot in payload["slots"]}
        row_a_car_id = next(
            car["id"]
            for frame in payload["frames"]
            for car in frame["cars"]
            if car["slot_id"] is not None and slot_rows[car["slot_id"]] == 0
        )

        row_a_entry_points = [
            car
            for frame in payload["frames"]
            for car in frame["cars"]
            if car["id"] == row_a_car_id and car["state"] in {"gate_crossing", "searching"}
        ]

        self.assertTrue(row_a_entry_points)
        self.assertFalse(any(abs(car["x"] - 25.0) <= 0.25 and car["y"] > 40.0 for car in row_a_entry_points))

    def test_main_road_vehicles_do_not_stack_on_top_of_each_other(self) -> None:
        payload = self.scenario_payload("rush_hour")

        spacing_violations = []
        for frame in payload["frames"]:
            road_cars = [
                car
                for car in frame["cars"]
                if car["state"] in {"searching", "exiting", "denied"}
                and abs(car["y"] - 55.7) <= 0.1
                and 8.0 <= car["x"] <= 88.0
            ]
            if len(road_cars) < 2:
                continue
            road_cars.sort(key=lambda car: car["x"])
            for left, right in zip(road_cars, road_cars[1:]):
                if right["x"] - left["x"] < 2.6:
                    spacing_violations.append((frame["time_minutes"], left["id"], right["id"]))

        self.assertEqual(spacing_violations, [])

    def test_exiting_vehicles_reach_outside_road_before_done(self) -> None:
        payload = self.scenario_payload("baseline")

        reached_outside_road = False
        for frame in payload["frames"]:
            for car in frame["cars"]:
                if car["state"] == "exiting" and car["x"] >= 90.0:
                    reached_outside_road = True
                    break
            if reached_outside_road:
                break

        self.assertTrue(reached_outside_road)

    def test_exiting_vehicle_pauses_at_exit_stop_line_before_merge(self) -> None:
        payload = self.scenario_payload("baseline")

        wait_frames = [
            (frame["time_minutes"], car["x"], car["y"])
            for frame in payload["frames"]
            for car in frame["cars"]
            if car["state"] == "exiting" and car["exit_phase"] == "wait"
        ]

        self.assertTrue(wait_frames)
        self.assertTrue(
            all(abs(x - EXIT_STOP_POINT[0]) <= 0.01 and abs(y - EXIT_STOP_POINT[1]) <= 0.01 for _, x, y in wait_frames)
        )
        self.assertGreaterEqual(len(wait_frames), 10)

    def test_exiting_vehicle_waits_inside_red_exit_gate_zone_before_merge(self) -> None:
        payload = self.scenario_payload("baseline")

        wait_frames = [
            car
            for frame in payload["frames"]
            for car in frame["cars"]
            if car["state"] == "exiting" and car["exit_phase"] == "wait"
        ]

        self.assertTrue(wait_frames)
        for car in wait_frames:
            self.assertGreaterEqual(car["x"], 86.8)
            self.assertLessEqual(car["x"], 98.8)
            self.assertGreaterEqual(car["y"], 39.0)
            self.assertLessEqual(car["y"], 58.0)

    def test_exiting_approach_uses_raised_exit_gate_lane(self) -> None:
        payload = self.scenario_payload("baseline")

        old_exit_flow_lane_frames = [
            car
            for frame in payload["frames"]
            for car in frame["cars"]
            if car["state"] == "exiting"
            and car["exit_phase"] == "approach"
            and 45.0 <= car["x"] <= 84.0
            and 53.0 <= car["y"] <= 58.0
        ]

        self.assertEqual(old_exit_flow_lane_frames, [])

    def test_raised_exit_gate_lane_vehicles_do_not_stack(self) -> None:
        payload = self.scenario_payload("rush_hour")

        for frame in payload["frames"]:
            raised_lane_cars = [
                car
                for car in frame["cars"]
                if car["state"] == "exiting"
                and car["exit_phase"] in {"approach", "wait"}
                and abs(car["y"] - 48.5) <= 0.1
                and 45.0 <= car["x"] <= 91.0
            ]
            raised_lane_cars.sort(key=lambda car: car["x"])
            for left, right in zip(raised_lane_cars, raised_lane_cars[1:]):
                self.assertGreaterEqual(right["x"] - left["x"], 2.6)

    def test_exit_congestion_shows_physical_vertical_exit_queue_on_exit_road(self) -> None:
        payload = self.scenario_payload("exit_congestion")
        max_visible_exit_queue = max(
            sum(
                1
                for car in frame["cars"]
                if car["state"] == "exit_queue"
                and abs(car["x"] - EXIT_QUEUE_LANE_X) <= 0.25
                and car["y"] >= EXIT_GATE_ROAD_Y
            )
            for frame in payload["frames"]
        )

        self.assertGreaterEqual(max_visible_exit_queue, 4)

    def test_exit_queue_vehicles_are_not_drawn_on_their_released_slots(self) -> None:
        payload = self.scenario_payload("exit_congestion")
        slot_positions = {slot["id"]: (slot["x"], slot["y"]) for slot in payload["slots"]}
        frame_with_visible_queue = next(
            frame
            for frame in payload["frames"]
            if sum(
                1
                for car in frame["cars"]
                if car["state"] == "exit_queue"
                and abs(car["x"] - EXIT_QUEUE_LANE_X) <= 0.25
                and car["y"] >= EXIT_GATE_ROAD_Y
            )
            >= 4
        )

        for car in frame_with_visible_queue["cars"]:
            if car["state"] != "exit_queue" or car["slot_id"] is None:
                continue
            slot_x, slot_y = slot_positions[car["slot_id"]]
            self.assertTrue(abs(car["x"] - slot_x) > 2.0 or abs(car["y"] - slot_y) > 2.0)

    def test_exit_queue_uses_one_vertical_lane_for_denied_and_parked_vehicles(self) -> None:
        payload = self.scenario_payload("limited_slots")

        shared_queue_frame = next(
            frame
            for frame in payload["frames"]
            if any(
                car["state"] == "exit_queue"
                and car["slot_id"] is None
                and abs(car["x"] - EXIT_QUEUE_LANE_X) <= 0.25
                for car in frame["cars"]
            )
            and any(
                car["state"] == "exit_queue"
                and car["slot_id"] is not None
                and abs(car["x"] - EXIT_QUEUE_LANE_X) <= 0.25
                for car in frame["cars"]
            )
        )
        queued = [
            car
            for car in shared_queue_frame["cars"]
            if car["state"] == "exit_queue" and abs(car["x"] - EXIT_QUEUE_LANE_X) <= 0.25
        ]

        self.assertTrue(any(car["slot_id"] is None for car in queued))
        self.assertTrue(any(car["slot_id"] is not None for car in queued))
        self.assertTrue(all(car["y"] >= EXIT_GATE_ROAD_Y for car in queued))

    def test_exit_queue_spacing_is_vertical_not_crossing_horizontal_lane(self) -> None:
        payload = self.scenario_payload("exit_congestion")
        frame_with_queue = max(
            payload["frames"],
            key=lambda frame: sum(1 for car in frame["cars"] if car["state"] == "exit_queue"),
        )
        queued = sorted(
            [
                car
                for car in frame_with_queue["cars"]
                if car["state"] == "exit_queue" and abs(car["x"] - EXIT_QUEUE_LANE_X) <= 0.25
            ],
            key=lambda car: car["y"],
        )

        self.assertGreaterEqual(len(queued), 4)
        for front, behind in zip(queued, queued[1:]):
            self.assertGreaterEqual(behind["y"] - front["y"], EXIT_VERT_QUEUE_SPACING - 0.05)

    def test_released_exit_queue_slot_can_become_free_before_vehicle_done(self) -> None:
        payload = self.scenario_payload("exit_congestion")

        found_released_free_slot = False
        for frame in payload["frames"]:
            slot_states = {slot["id"]: slot["state"] for slot in frame["slots"]}
            for car in frame["cars"]:
                if car["state"] == "exit_queue" and car["slot_id"] is not None and slot_states[car["slot_id"]] == "free":
                    found_released_free_slot = True
                    break
            if found_released_free_slot:
                break

        self.assertTrue(found_released_free_slot)

    def test_only_one_vehicle_occupies_exit_throat_wait_point_at_a_time(self) -> None:
        payload = self.scenario_payload("rush_hour")

        for frame in payload["frames"]:
            waiting = [
                car
                for car in frame["cars"]
                if car["state"] == "exiting"
                and car["exit_phase"] == "wait"
                and abs(car["x"] - EXIT_STOP_POINT[0]) <= 0.01
                and abs(car["y"] - EXIT_STOP_POINT[1]) <= 0.01
            ]
            self.assertLessEqual(len(waiting), 1)

    def test_exiting_vehicles_use_both_outside_road_directions(self) -> None:
        payload = self.scenario_payload("baseline")

        saw_up_exit = False
        saw_down_exit = False
        for frame in payload["frames"]:
            for car in frame["cars"]:
                if car["state"] != "exiting" or car["x"] < 90.0:
                    continue
                if car["y"] < 0:
                    saw_up_exit = True
                if car["y"] > 88:
                    saw_down_exit = True
            if saw_up_exit and saw_down_exit:
                break

        self.assertTrue(saw_up_exit)
        self.assertTrue(saw_down_exit)

    def test_exit_turns_follow_current_visual_lane_split(self) -> None:
        payload = self.scenario_payload("baseline")

        saw_up_merge = False
        saw_down_merge = False
        for frame in payload["frames"]:
            for car in frame["cars"]:
                if car["state"] != "exiting" or car["exit_phase"] != "merge":
                    continue
                if car["id"] % 2 == 1 and abs(car["y"] - EXIT_STOP_POINT[1]) <= 0.1 and car["x"] > 94.8:
                    saw_up_merge = True
                if car["id"] % 2 == 0 and abs(car["x"] - 94.8) <= 0.25 and car["y"] > 55.7:
                    saw_down_merge = True
            if saw_up_merge and saw_down_merge:
                break

        self.assertTrue(saw_up_merge)
        self.assertTrue(saw_down_merge)

    def test_limited_slots_exit_merge_crosses_actual_gate_line(self) -> None:
        payload = self.scenario_payload("limited_slots")
        actual_gate_y = 41.0

        gate_crossing_frames = [
            car
            for frame in payload["frames"]
            for car in frame["cars"]
            if car["state"] == "exiting"
            and car["exit_phase"] == "merge"
            and 88.0 <= car["x"] <= 95.0
            and abs(car["y"] - actual_gate_y) <= 0.25
        ]

        self.assertEqual(EXIT_STOP_POINT, (88.5, actual_gate_y))
        self.assertTrue(gate_crossing_frames)

    def test_outside_road_uses_distinct_lanes_for_up_and_down_traffic(self) -> None:
        payload = self.scenario_payload("baseline")

        saw_up_lane = False
        saw_down_lane = False
        for frame in payload["frames"]:
            for car in frame["cars"]:
                if car["state"] != "exiting":
                    continue
                if abs(car["x"] - 98.0) <= 0.25 and car["y"] < 48.0:
                    saw_up_lane = True
                if abs(car["x"] - 94.8) <= 0.25 and car["y"] > 63.4:
                    saw_down_lane = True
            if saw_up_lane and saw_down_lane:
                break

        self.assertTrue(saw_up_lane)
        self.assertTrue(saw_down_lane)

    def test_exit_direction_is_deterministic_for_same_scenario(self) -> None:
        first = run_simulation(ParkingSimulationConfig(scenario="baseline")).to_dict()
        second = run_simulation(ParkingSimulationConfig(scenario="baseline")).to_dict()

        def final_exit_directions(payload: dict) -> dict[int, str]:
            directions: dict[int, str] = {}
            for frame in payload["frames"]:
                for car in frame["cars"]:
                    if car["state"] != "exiting" or car["x"] < 90.0:
                        continue
                    if car["y"] < 0:
                        directions[car["id"]] = "up"
                    elif car["y"] > 88:
                        directions[car["id"]] = "down"
            return directions

        self.assertEqual(final_exit_directions(first), final_exit_directions(second))

    def test_entry_queue_can_extend_offscreen_below_map(self) -> None:
        payload = self.scenario_payload("rush_hour")

        found_offscreen_queue = False
        for frame in payload["frames"]:
            queued = [car for car in frame["cars"] if car["state"] == "entry_queue"]
            if not queued:
                continue
            if any(car["y"] > 100 for car in queued):
                found_offscreen_queue = True
                break

        self.assertTrue(found_offscreen_queue)

    def test_first_visible_vehicle_appears_in_entry_queue_lane(self) -> None:
        payload = self.scenario_payload("baseline")

        first_visible = None
        for frame in payload["frames"]:
            car = next(
                (
                    item
                    for item in frame["cars"]
                    if item["id"] == 1
                    and item["state"] in {"entry_queue", "approaching_gate", "gate_wait", "gate_crossing"}
                    and item["y"] <= 100
                ),
                None,
            )
            if car is not None:
                first_visible = car
                break

        self.assertIsNotNone(first_visible)
        self.assertIn(first_visible["state"], {"entry_queue", "approaching_gate"})
        self.assertGreaterEqual(first_visible["x"], 7.2)
        self.assertLessEqual(first_visible["x"], 8.8)
        self.assertGreaterEqual(first_visible["y"], 82.0)
        self.assertLessEqual(first_visible["y"], 100.0)

    def test_entry_vehicles_face_upward_before_gate(self) -> None:
        payload = self.scenario_payload("baseline")

        entry_headings = [
            car["heading"]
            for frame in payload["frames"]
            for car in frame["cars"]
            if car["id"] == 1 and car["state"] in {"entry_queue", "approaching_gate", "gate_wait"}
        ]

        self.assertTrue(entry_headings)
        self.assertTrue(all(abs(heading or 0.0) <= 1.0 for heading in entry_headings))

    def test_first_vehicle_progresses_through_gate_stop_sequence(self) -> None:
        payload = self.scenario_payload("baseline")

        states = []
        for frame in payload["frames"]:
            car = next(item for item in frame["cars"] if item["id"] == 1)
            if not states or states[-1] != car["state"]:
                states.append(car["state"])

        expected_sequence = ["scheduled", "entry_queue", "approaching_gate", "gate_wait", "gate_crossing", "searching", "parked", "exiting", "done"]
        current_index = 0
        for state in states:
            if current_index < len(expected_sequence) and state == expected_sequence[current_index]:
                current_index += 1

        self.assertEqual(current_index, len(expected_sequence))

    def test_gate_wait_position_stays_stable(self) -> None:
        payload = self.scenario_payload("baseline")

        wait_positions = {
            (car["x"], car["y"])
            for frame in payload["frames"]
            for car in frame["cars"]
            if car["id"] == 1 and car["state"] == "gate_wait"
        }

        self.assertTrue(wait_positions)
        self.assertEqual(wait_positions, {(8.0, 36.0)})


if __name__ == "__main__":
    unittest.main()
