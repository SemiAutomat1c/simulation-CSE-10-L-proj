"""Parity checks between Python expand and the JS expand key contract."""

from __future__ import annotations

import unittest
from pathlib import Path

from app.simulation import ParkingSimulationConfig, run_simulation
from app.timeline_compact import (
    _VEHICLE_DELTA_KEYS,
    compact_simulation,
    expand_simulation,
)


class ExpandParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.full = run_simulation(
            ParkingSimulationConfig(scenario="baseline", map="one_entrance_one_exit")
        ).to_dict()
        cls.compact = compact_simulation(cls.full)
        cls.static_js = (
            Path(__file__).resolve().parent.parent / "app" / "static" / "app.js"
        ).read_text()

    def test_js_expand_handles_all_python_vehicle_short_keys(self) -> None:
        """JS expandCompactSimulation must understand every Python delta short key."""
        start = self.static_js.find("function expandCompactSimulation")
        self.assertGreater(start, -1)
        # Function body until next top-level function
        end = self.static_js.find("\nfunction ", start + 1)
        body = self.static_js[start:end if end != -1 else start + 4000]
        for short, full in _VEHICLE_DELTA_KEYS:
            self.assertIn(
                f"delta.{short}",
                body,
                msg=f"JS expand missing short key {short!r} for field {full!r}",
            )

    def test_js_expand_handles_gate_and_queue_short_keys(self) -> None:
        start = self.static_js.find("function expandCompactSimulation")
        end = self.static_js.find("\nfunction ", start + 1)
        body = self.static_js[start:end if end != -1 else start + 4000]
        for token in ("kf.g", "kf.q", "kf.v", "kf.s", "kf.t"):
            self.assertIn(token, body)

    def test_python_expand_matches_full_positions_at_keyframes(self) -> None:
        expanded = expand_simulation(self.compact)
        full_by_t = {round(f["time_minutes"], 2): f for f in self.full["frames"]}
        self.assertGreater(len(expanded["frames"]), 10)
        for frame in expanded["frames"][:: max(1, len(expanded["frames"]) // 20)]:
            t = round(frame["time_minutes"], 2)
            truth = full_by_t[t]
            by_id = {c["id"]: c for c in truth["cars"]}
            for car in frame["cars"]:
                if car["id"] not in by_id:
                    continue
                tc = by_id[car["id"]]
                self.assertEqual(car["state"], tc["state"])
                self.assertAlmostEqual(car["x"], tc["x"], places=2)
                self.assertAlmostEqual(car["y"], tc["y"], places=2)


if __name__ == "__main__":
    unittest.main()
