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
