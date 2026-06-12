import unittest

from app.simulation import EXIT_STOP_POINT, ParkingSimulationConfig, run_simulation


class ParkingSimulationTests(unittest.TestCase):
    def test_cars_progress_through_required_states(self) -> None:
        result = run_simulation(ParkingSimulationConfig(scenario="baseline"))
        payload = result.to_dict()
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
        result = run_simulation(ParkingSimulationConfig(scenario="rush_hour"))
        payload = result.to_dict()

        for frame in payload["frames"]:
            occupied_slots = [
                slot["id"]
                for slot in frame["slots"]
                if slot["state"] in {"targeted", "occupied", "exiting"}
            ]
            self.assertEqual(len(occupied_slots), len(set(occupied_slots)))

    def test_limited_slots_records_denied_cars(self) -> None:
        result = run_simulation(ParkingSimulationConfig(scenario="limited_slots"))
        payload = result.to_dict()

        self.assertGreater(payload["metrics"]["denied_cars"], 0)
        self.assertLess(payload["metrics"]["total_completed_cars"], payload["metrics"]["total_cars"])

    def test_payload_contains_metrics_slots_and_timeline(self) -> None:
        result = run_simulation(ParkingSimulationConfig(scenario="baseline"))
        payload = result.to_dict()

        self.assertIn("timeline", payload)
        self.assertIn("slots", payload)
        self.assertIn("frames", payload)
        self.assertIn("average_search_time_minutes", payload["metrics"])
        self.assertIn("occupancy_rate_percent", payload["metrics"])

    def test_vehicle_payload_includes_cars_and_motorcycles(self) -> None:
        result = run_simulation(ParkingSimulationConfig(scenario="baseline"))
        payload = result.to_dict()
        vehicle_types = {car["vehicle_type"] for frame in payload["frames"] for car in frame["cars"]}

        self.assertIn("car", vehicle_types)
        self.assertIn("motorcycle", vehicle_types)
        self.assertGreater(payload["metrics"]["total_cars"], 0)
        self.assertGreater(payload["metrics"]["total_motorcycles"], 0)

    def test_exiting_vehicle_payload_includes_visible_exit_phases(self) -> None:
        result = run_simulation(ParkingSimulationConfig(scenario="baseline"))
        payload = result.to_dict()
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
        result = run_simulation(ParkingSimulationConfig(scenario="baseline"))
        payload = result.to_dict()
        slot_types = {slot["slot_type"] for slot in payload["slots"]}

        self.assertIn("car_slot", slot_types)
        self.assertIn("motorcycle_slot", slot_types)

    def test_cars_never_occupy_motorcycle_only_slots(self) -> None:
        result = run_simulation(ParkingSimulationConfig(scenario="rush_hour"))
        payload = result.to_dict()
        slot_types = {slot["id"]: slot["slot_type"] for slot in payload["slots"]}

        for frame in payload["frames"]:
            for car in frame["cars"]:
                if car["vehicle_type"] == "car" and car["slot_id"] is not None:
                    self.assertNotEqual(slot_types[car["slot_id"]], "motorcycle_slot")

    def test_motorcycles_use_motorcycle_slots(self) -> None:
        result = run_simulation(ParkingSimulationConfig(scenario="baseline"))
        payload = result.to_dict()
        slot_types = {slot["id"]: slot["slot_type"] for slot in payload["slots"]}
        parked_motorcycle_slots = {
            car["slot_id"]
            for frame in payload["frames"]
            for car in frame["cars"]
            if car["vehicle_type"] == "motorcycle" and car["slot_id"] is not None
        }

        self.assertTrue(any(slot_types[slot_id] == "motorcycle_slot" for slot_id in parked_motorcycle_slots))

    def test_baseline_matches_visible_lot_capacity(self) -> None:
        result = run_simulation(ParkingSimulationConfig(scenario="baseline"))
        payload = result.to_dict()
        car_slots_by_row = {
            row: sum(1 for slot in payload["slots"] if slot["slot_type"] == "car_slot" and slot["row"] == row)
            for row in (0, 1, 2)
        }
        motorcycle_slots = [slot for slot in payload["slots"] if slot["slot_type"] == "motorcycle_slot"]

        self.assertEqual(car_slots_by_row, {0: 20, 1: 20, 2: 20})
        self.assertEqual(len(motorcycle_slots), 12)

    def test_motorcycles_never_occupy_car_slots(self) -> None:
        result = run_simulation(ParkingSimulationConfig(scenario="baseline"))
        payload = result.to_dict()
        slot_types = {slot["id"]: slot["slot_type"] for slot in payload["slots"]}

        for frame in payload["frames"]:
            for car in frame["cars"]:
                if car["vehicle_type"] == "motorcycle" and car["slot_id"] is not None:
                    self.assertEqual(slot_types[car["slot_id"]], "motorcycle_slot")

    def test_visible_vehicles_stay_inside_readable_map_area(self) -> None:
        result = run_simulation(ParkingSimulationConfig(scenario="limited_slots"))
        payload = result.to_dict()
        visible_states = {"entry_queue", "approaching_gate", "gate_wait", "gate_crossing", "searching", "parked", "exit_queue", "exiting", "denied"}

        for frame in payload["frames"]:
            for car in frame["cars"]:
                if car["state"] in visible_states:
                    self.assertGreaterEqual(car["x"], 0)
                    self.assertLessEqual(car["x"], 100)
                    # entry_queue and approaching vehicles may start above the map (negative y)
                    # exiting vehicles may leave the map vertically before becoming done
                    if car["state"] not in {"entry_queue", "approaching_gate", "exiting"}:
                        self.assertGreaterEqual(car["y"], 0)
                    if car["state"] != "exiting":
                        self.assertLessEqual(car["y"], 88)

    def test_baseline_uses_all_car_rows(self) -> None:
        result = run_simulation(ParkingSimulationConfig(scenario="baseline"))
        payload = result.to_dict()
        slot_rows = {slot["id"]: slot["row"] for slot in payload["slots"]}
        occupied_rows = {
            slot_rows[car["slot_id"]]
            for frame in payload["frames"]
            for car in frame["cars"]
            if car["vehicle_type"] == "car" and car["slot_id"] and car["state"] in {"parked", "exit_queue"}
        }

        self.assertEqual({0, 1, 2}, occupied_rows)

    def test_motorcycle_slots_stay_inside_marked_motorcycle_area(self) -> None:
        result = run_simulation(ParkingSimulationConfig(scenario="baseline"))
        payload = result.to_dict()
        motorcycle_slots = [slot for slot in payload["slots"] if slot["slot_type"] == "motorcycle_slot"]

        for slot in motorcycle_slots:
            self.assertGreaterEqual(slot["x"], 75)
            self.assertLessEqual(slot["x"], 89)
            self.assertGreaterEqual(slot["y"], 14)
            self.assertLessEqual(slot["y"], 36.0)

    def test_searching_vehicles_follow_lanes_before_parking(self) -> None:
        result = run_simulation(ParkingSimulationConfig(scenario="baseline"))
        payload = result.to_dict()

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
        result = run_simulation(ParkingSimulationConfig(scenario="rush_hour"))
        payload = result.to_dict()

        for frame in payload["frames"]:
            for car in frame["cars"]:
                if car["state"] == "entry_queue":
                    self.assertGreaterEqual(car["x"], 7.2)
                    self.assertLessEqual(car["x"], 8.8)
                    self.assertLessEqual(car["y"], 10.5)

    def test_entry_queue_uses_single_centerline(self) -> None:
        result = run_simulation(ParkingSimulationConfig(scenario="rush_hour"))
        payload = result.to_dict()

        checked = False
        for frame in payload["frames"]:
            queued = [car for car in frame["cars"] if car["state"] == "entry_queue"]
            if len(queued) < 3:
                continue
            xs = {round(car["x"], 2) for car in queued[:6]}
            ys = [car["y"] for car in queued[:6]]
            self.assertEqual(xs, {8.0})
            self.assertEqual(ys, sorted(ys, reverse=True))
            checked = True
            break

        self.assertTrue(checked)

    def test_entry_lane_vehicles_keep_visible_follow_distance(self) -> None:
        result = run_simulation(ParkingSimulationConfig(scenario="rush_hour"))
        payload = result.to_dict()

        checked = False
        for frame in payload["frames"]:
            lane_cars = [
                car
                for car in frame["cars"]
                if car["state"] in {"entry_queue", "approaching_gate", "gate_wait", "gate_crossing"}
                and abs(car["x"] - 8.0) <= 0.1
                and car["y"] <= 55.7
            ]
            if len(lane_cars) < 2:
                continue
            lane_cars.sort(key=lambda car: car["y"], reverse=True)
            for leader, follower in zip(lane_cars, lane_cars[1:]):
                self.assertGreaterEqual(leader["y"] - follower["y"], 2.6)
            checked = True
            break

        self.assertTrue(checked)

    def test_main_road_vehicles_do_not_stack_on_top_of_each_other(self) -> None:
        result = run_simulation(ParkingSimulationConfig(scenario="rush_hour"))
        payload = result.to_dict()

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
        result = run_simulation(ParkingSimulationConfig(scenario="baseline"))
        payload = result.to_dict()

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
        result = run_simulation(ParkingSimulationConfig(scenario="baseline"))
        payload = result.to_dict()

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
        result = run_simulation(ParkingSimulationConfig(scenario="baseline"))
        payload = result.to_dict()

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
        result = run_simulation(ParkingSimulationConfig(scenario="baseline"))
        payload = result.to_dict()

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
        result = run_simulation(ParkingSimulationConfig(scenario="rush_hour"))
        payload = result.to_dict()

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

    def test_only_one_vehicle_occupies_exit_throat_wait_point_at_a_time(self) -> None:
        result = run_simulation(ParkingSimulationConfig(scenario="rush_hour"))
        payload = result.to_dict()

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
        result = run_simulation(ParkingSimulationConfig(scenario="baseline"))
        payload = result.to_dict()

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

    def test_exit_turns_split_from_throat_in_correct_direction(self) -> None:
        result = run_simulation(ParkingSimulationConfig(scenario="baseline"))
        payload = result.to_dict()

        saw_left_turn_up = False
        saw_right_turn_down = False
        for frame in payload["frames"]:
            for car in frame["cars"]:
                if car["state"] != "exiting" or car["x"] < 88.0 or car["x"] > 91.5:
                    continue
                if car["id"] % 2 == 1 and car["y"] < 55.7:
                    saw_left_turn_up = True
                if car["id"] % 2 == 0 and car["y"] > 55.7:
                    saw_right_turn_down = True
            if saw_left_turn_up and saw_right_turn_down:
                break

        self.assertTrue(saw_left_turn_up)
        self.assertTrue(saw_right_turn_down)

    def test_outside_road_uses_distinct_lanes_for_up_and_down_traffic(self) -> None:
        result = run_simulation(ParkingSimulationConfig(scenario="baseline"))
        payload = result.to_dict()

        saw_up_lane = False
        saw_down_lane = False
        for frame in payload["frames"]:
            for car in frame["cars"]:
                if car["state"] != "exiting":
                    continue
                if abs(car["x"] - 94.8) <= 0.25 and car["y"] < 48.0:
                    saw_up_lane = True
                if abs(car["x"] - 98.0) <= 0.25 and car["y"] > 63.4:
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

    def test_entry_queue_can_extend_offscreen_above_map(self) -> None:
        result = run_simulation(ParkingSimulationConfig(scenario="rush_hour"))
        payload = result.to_dict()

        found_offscreen_queue = False
        for frame in payload["frames"]:
            queued = [car for car in frame["cars"] if car["state"] == "entry_queue"]
            if not queued:
                continue
            if any(car["y"] < 0 for car in queued):
                found_offscreen_queue = True
                break

        self.assertTrue(found_offscreen_queue)

    def test_first_visible_vehicle_enters_from_top_edge(self) -> None:
        result = run_simulation(ParkingSimulationConfig(scenario="baseline"))
        payload = result.to_dict()

        first_visible = None
        for frame in payload["frames"]:
            car = next(
                (
                    item
                    for item in frame["cars"]
                    if item["id"] == 1 and item["state"] in {"entry_queue", "approaching_gate", "gate_wait", "gate_crossing"} and item["y"] >= 0
                ),
                None,
            )
            if car is not None:
                first_visible = car
                break

        self.assertIsNotNone(first_visible)
        self.assertEqual(first_visible["state"], "approaching_gate")
        self.assertGreaterEqual(first_visible["x"], 7.2)
        self.assertLessEqual(first_visible["x"], 8.8)
        self.assertLessEqual(first_visible["y"], 5.0)

    def test_first_vehicle_progresses_through_gate_stop_sequence(self) -> None:
        result = run_simulation(ParkingSimulationConfig(scenario="baseline"))
        payload = result.to_dict()

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
        result = run_simulation(ParkingSimulationConfig(scenario="baseline"))
        payload = result.to_dict()

        wait_positions = {
            (car["x"], car["y"])
            for frame in payload["frames"]
            for car in frame["cars"]
            if car["id"] == 1 and car["state"] == "gate_wait"
        }

        self.assertTrue(wait_positions)
        self.assertEqual(wait_positions, {(8.0, 26.6)})


if __name__ == "__main__":
    unittest.main()
