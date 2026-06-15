import unittest
from pathlib import Path


class FrontendStaticTests(unittest.TestCase):
    def setUp(self) -> None:
        self.static_dir = Path(__file__).resolve().parent.parent / "app" / "static"

    def test_dashboard_contains_required_controls_and_layers(self) -> None:
        html = (self.static_dir / "index.html").read_text()

        self.assertIn("scenarioSelect", html)
        self.assertIn("playPauseButton", html)
        self.assertIn("replayButton", html)
        self.assertIn("parkingStage", html)
        self.assertIn("slotLayer", html)
        self.assertIn("carLayer", html)
        self.assertIn('/static/style.css?v=23', html)
        self.assertIn('/static/app.js?v=19', html)
        self.assertIn("metricMotorcycles", html)
        self.assertIn("Vehicle Mix", html)
        self.assertIn("simulationStatus", html)
        self.assertIn("parkingMap", html)
        self.assertIn("MAIN ENTRY", html)
        self.assertIn("ONE-WAY SEARCH LOOP", html)
        self.assertIn("EXIT TO ROAD", html)
        # Performance metrics panel + scenario comparison feature.
        self.assertIn("Performance", html)
        self.assertIn("metricEntryWait", html)
        self.assertIn("metricThroughput", html)
        self.assertIn("metricEntryUtil", html)
        self.assertIn("compareButton", html)
        self.assertIn("comparePanel", html)
        self.assertIn("Scenario Comparison", html)
        # Live custom-input controls.
        self.assertIn("Custom Inputs", html)
        self.assertIn("inputCars", html)
        self.assertIn("inputEntryGates", html)
        self.assertIn("inputExitGates", html)
        self.assertIn("applyParamsButton", html)
        self.assertIn("resetParamsButton", html)

    def test_css_contains_top_down_lot_visual_hooks(self) -> None:
        css = (self.static_dir / "style.css").read_text()

        self.assertIn(".parking-stage", css)
        self.assertIn(".topdown-slot", css)
        self.assertIn(".topdown-slot.unavailable", css)
        self.assertIn(".topdown-slot.slot-motorcycle.unavailable", css)
        self.assertIn("0 0 0 2px rgba(255, 245, 180, 0.95)", css)
        self.assertIn(".exit-gate-arm {\n  position: absolute;\n  left: 88%;\n  top: 38%;", css)
        self.assertIn(".topdown-vehicle", css)
        self.assertIn(".entry-gate", css)
        self.assertIn(".exit-gate", css)
        self.assertIn("parking-topdown-sprites-v1-transparent.png", css)
        self.assertIn("custom-parking-background.png", css)
        self.assertIn("sliced/car-red.png", css)
        self.assertIn("sliced/motorcycle-red.png", css)
        self.assertIn(".parking-map", css)
        self.assertIn(".route-arrow", css)
        self.assertIn(".entry-zone", css)
        self.assertIn(".exit-zone", css)
        self.assertIn(".vehicle-motorcycle", css)
        self.assertIn(".vehicle-suv", css)
        self.assertIn(".vehicle-van", css)
        self.assertIn(".vehicle-wheel", css)
        self.assertIn("@keyframes wheel-spin", css)
        self.assertIn(".vehicle-headlight", css)
        self.assertIn(".vehicle-brake-light", css)
        self.assertIn(".map-surface", css)
        self.assertIn(".simulation-status", css)
        self.assertIn(".control-rail.is-loading", css)
        self.assertIn("overflow: hidden", css)
        self.assertIn("grid-template-columns: clamp(360px, 29vw, 430px) minmax(0, 1fr)", css)

    def test_frontend_fetches_simulation_and_scenarios(self) -> None:
        js = (self.static_dir / "app.js").read_text()

        self.assertIn("/api/scenarios", js)
        self.assertIn("/api/simulation", js)
        self.assertIn("renderFrame", js)
        self.assertIn("requestAnimationFrame", js)
        self.assertIn("vehicle_type", js)
        self.assertIn("vehicleVisualClass", js)
        self.assertIn("createVehicleNode", js)
        self.assertIn("movementAngle", js)
        self.assertIn("setSimulationStatus", js)
        self.assertIn("setLoadingState", js)
        self.assertIn("response.ok", js)
        self.assertIn("catch (error)", js)
        self.assertIn("scenarioSelect.disabled", js)
        self.assertIn("speedSlider.disabled", js)
        self.assertIn("wheels-moving", js)
        self.assertIn("topdown-vehicle", js)
        self.assertIn('slot.state === "unavailable"', js)

    def test_frontend_has_scenario_comparison_logic(self) -> None:
        js = (self.static_dir / "app.js").read_text()

        self.assertIn("/api/compare", js)
        self.assertIn("renderCompare", js)
        self.assertIn("compare-table", js)
        self.assertIn("bar-fill", js)
        self.assertIn("average_entry_wait_minutes", js)
        self.assertIn("throughput_vehicles_per_hour", js)

    def test_frontend_sends_custom_parameters(self) -> None:
        js = (self.static_dir / "app.js").read_text()

        self.assertIn("customParamQuery", js)
        self.assertIn("entry_gates", js)
        self.assertIn("total_cars", js)
        self.assertIn("applyParamsButton", js)

    def test_frontend_switches_background_per_gate_layout(self) -> None:
        js = (self.static_dir / "app.js").read_text()

        self.assertIn("SCENARIO_BACKGROUNDS", js)
        self.assertIn("applyScenarioBackground", js)
        self.assertIn("two_entrance_two_exit", js)
        self.assertIn("custom-map", js)

    def test_frontend_skips_corner_cutting_interpolation_for_gate_exit_turns(self) -> None:
        js = (self.static_dir / "app.js").read_text()

        self.assertIn("function shouldInterpolatePosition", js)
        self.assertIn('car.state !== "exiting"', js)
        self.assertIn('"merge"', js)
        self.assertIn('"road"', js)

    def test_entry_gate_opens_away_from_entry_queue(self) -> None:
        css = (self.static_dir / "style.css").read_text()

        self.assertIn("transform-origin: 100% 50%", css)
        self.assertIn(".entry-gate-arm.open {\n  transform: rotate(90deg);\n}", css)


if __name__ == "__main__":
    unittest.main()
