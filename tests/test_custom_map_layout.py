import re
import unittest
from pathlib import Path

from app.simulation import _top_down_slot_layout


class CustomMapLayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.static_dir = Path(__file__).resolve().parent.parent / "app" / "static"

    def test_custom_gate_arms_align_to_painted_gate_throats(self) -> None:
        js = (self.static_dir / "app.js").read_text()

        expected = {
            "two_entrance_two_exit": [
                ("entry", 29.0, 6.6, 7.6),
                ("entry", 72.0, 6.6, 7.6),
                ("exit", 34.2, 92.2, 8.8),
                ("exit", 69.3, 92.2, 8.8),
            ],
            "two_entrance_one_exit": [
                ("entry", 29.0, 6.6, 7.6),
                ("entry", 72.0, 6.6, 7.6),
                ("exit", 38.8, 92.2, 8.8),
            ],
            "one_entrance_two_exit": [
                ("entry", 32.0, 4.8, 7.4),
                ("exit", 34.2, 92.2, 8.8),
                ("exit", 69.3, 92.2, 8.8),
            ],
        }

        for scenario, gates in expected.items():
            with self.subTest(scenario=scenario):
                self.assertEqual(self._scenario_gates(js, scenario), gates)

        self.assertIn("arm.style.width = `${g.width || 6}%`;", js)

    def test_custom_gate_css_keeps_entry_left_and_exit_vertical(self) -> None:
        css = (self.static_dir / "style.css").read_text()

        # Entry arm lifts open (rotates 90deg) like the baseline map's gate.
        self.assertIn(".map-gate-entry.open {\n  transform: rotate(90deg);\n}", css)
        self.assertIn(".map-gate-exit {", css)
        self.assertIn("transform-origin: 0% 50%;", css)
        self.assertIn("transform: rotate(90deg);", css)
        self.assertIn(".map-gate-exit.open {\n  transform: rotate(90deg);\n}", css)
        # Exit booth stays vertical; its striped barrier swings up when open.
        self.assertIn(".map-gate-exit.open::after {\n  transform: translateY(-50%) rotate(-78deg);\n}", css)
        self.assertIn(".map-gate-exit::before", css)
        self.assertIn(".map-gate-exit::after", css)
        self.assertIn('background: url("/static/assets/generated/sliced/gate-exit-red.png")', css)
        self.assertIn("border-radius: 999px", css)

    def test_parking_slot_centers_keep_baseline_map_reference(self) -> None:
        layout = _top_down_slot_layout()
        car_rows = {
            row: [
                (round(point["x"], 2), round(point["y"], 2))
                for point in layout
                if point["row"] == row and point["slot_type"] == "car_slot"
            ]
            for row in (0, 1, 2)
        }
        expected_car_xs = [
            31.37, 33.56, 35.44, 37.32, 39.21, 41.09, 42.98, 44.83, 46.71, 48.60,
            50.45, 52.31, 54.16, 56.01, 57.87, 59.78, 61.70, 63.58, 65.49, 67.83,
        ]

        self.assertEqual(car_rows[0], [(x, 26.0) for x in expected_car_xs])
        self.assertEqual(car_rows[1], [(x, 43.8) for x in expected_car_xs])
        self.assertEqual(car_rows[2], [(x, 63.3) for x in expected_car_xs])

        motorcycle_rows = {
            row: [
                (round(point["x"], 2), round(point["y"], 2))
                for point in layout
                if point["row"] == row and point["slot_type"] == "motorcycle_slot"
            ]
            for row in (3, 4)
        }
        expected_motorcycle_xs = [79.76, 81.46, 83.17, 84.87, 86.58, 88.31]

        self.assertEqual(motorcycle_rows[3], [(x, 14.4) for x in expected_motorcycle_xs])
        self.assertEqual(motorcycle_rows[4], [(x, 24.5) for x in expected_motorcycle_xs])

    def test_custom_maps_remap_vehicle_coordinates_to_painted_grid(self) -> None:
        js = (self.static_dir / "app.js").read_text()

        self.assertIn("const CUSTOM_MAP_COORDINATE_TRANSFORM = {", js)
        self.assertIn("xScale: 0.95815", js)
        self.assertIn("xOffset: 1.94316", js)
        self.assertIn("yScale: 1.03202", js)
        self.assertIn("yOffset: 2.42282", js)
        self.assertIn("function mapScenePoint(x, y, options = {}) {", js)
        self.assertIn("return { x: transformedX, y: transformedY };", js)
        self.assertIn("const slotPoint = mapScenePoint(slot.x, slot.y, { row: slot.row });", js)
        self.assertIn("const point = mapScenePoint(interpX, interpY, { row: sceneMappingRow(car) });", js)

    def test_two_entrance_one_exit_uses_its_own_vehicle_grid_transform(self) -> None:
        js = (self.static_dir / "app.js").read_text()

        self.assertIn("let activeScenario = \"baseline\";", js)
        self.assertIn("const CUSTOM_MAP_SCENARIO_TRANSFORMS = {", js)
        self.assertIn("two_entrance_one_exit: {", js)
        self.assertIn("xScale: 0.99270", js)
        self.assertIn("xOffset: 0.27096", js)
        self.assertIn("rowYOffsets: { 1: 2.6, 2: 2.6 },", js)
        self.assertIn("function rowFromSlotId(slotId) {", js)
        self.assertIn("const rowOffset = transform.rowYOffsets?.[row] || 0;", js)
        self.assertIn("activeScenario = scenario;", js)
        self.assertIn("CUSTOM_MAP_SCENARIO_TRANSFORMS[activeScenario] || CUSTOM_MAP_COORDINATE_TRANSFORM", js)

    def test_parking_row_offset_does_not_shift_exit_queues(self) -> None:
        js = (self.static_dir / "app.js").read_text()

        self.assertIn("function sceneMappingRow(car) {", js)
        self.assertIn("if (car.state !== \"parked\" && car.state !== \"searching\") return null;", js)
        self.assertIn("function parkingRowOffsetApplies(y, row) {", js)
        self.assertIn("if (!parkingRowOffsetApplies(y, row)) return 0;", js)

    def test_one_entrance_two_exit_uses_painted_vehicle_grid_transform(self) -> None:
        js = (self.static_dir / "app.js").read_text()

        self.assertIn("one_entrance_two_exit: {", js)
        self.assertIn("xScale: 0.98514", js)
        self.assertIn("xOffset: 0.52786", js)
        self.assertIn("rowYOffsets: { 1: 2.6, 2: 2.6 },", js)

    def _scenario_gates(self, js: str, scenario: str) -> list[tuple[str, float, float, float]]:
        match = re.search(rf"{scenario}:\s*\[(.*?)\n  \],", js, re.S)
        self.assertIsNotNone(match, scenario)
        body = match.group(1)
        gates = []
        for gate in re.finditer(
            r'\{ type: "([^"]+)", top: ([\d.]+), left: ([\d.]+)(?:, width: ([\d.]+))? \}',
            body,
        ):
            gate_type, top, left, width = gate.groups()
            gates.append((gate_type, float(top), float(left), float(width or 6.0)))
        return gates


if __name__ == "__main__":
    unittest.main()
