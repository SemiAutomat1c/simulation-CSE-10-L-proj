import unittest
from pathlib import Path


class FrontendStaticTests(unittest.TestCase):
    def setUp(self) -> None:
        self.static_dir = Path(__file__).resolve().parent.parent / "app" / "static"

    def test_dashboard_contains_required_controls_and_layers(self) -> None:
        html = (self.static_dir / "index.html").read_text()

        self.assertIn("scenarioSelect", html)
        self.assertIn("mapSelect", html)
        self.assertIn("playPauseButton", html)
        self.assertIn("replayButton", html)
        self.assertIn("parkingStage", html)
        self.assertIn("slotLayer", html)
        self.assertIn("carLayer", html)
        self.assertIn('/static/style.css?v=25', html)
        self.assertIn('/static/app.js?v=28', html)
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
        self.assertIn("inputSlots", html)
        # Gate counts come from the map now, not from custom inputs.
        self.assertNotIn("inputEntryGates", html)
        self.assertNotIn("inputExitGates", html)
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
        self.assertIn("format=compact", js)
        self.assertIn("expandCompactSimulation", js)
        self.assertIn("clientSimulationCache", js)
        self.assertIn("preloadMapBackgrounds", js)
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
        # Playback uses fixed frame cadence (original 40ms at 1x), not sim-delta stretch.
        self.assertIn("FRAME_INTERVAL_MS", js)
        self.assertIn("syncTransitionDuration", js)
        self.assertIn("--transition-duration", js)
        self.assertNotIn("baseIntervalMsAt", js)
        self.assertIn("wheels-moving", js)
        self.assertIn("topdown-vehicle", js)
        self.assertIn('slot.state === "unavailable"', js)
        # Compact fetch must not bust cache with Date.now(); client cache keys instead.
        self.assertNotIn("/api/simulation?map=", js)  # legacy full fetch shape without format=
        sim_fetch_region = js[js.find("/api/simulation") : js.find("/api/simulation") + 220]
        self.assertIn("format=compact", sim_fetch_region)
        self.assertNotIn("Date.now()", sim_fetch_region)

    def test_map_backgrounds_use_stable_urls_without_query_bust(self) -> None:
        js = (self.static_dir / "app.js").read_text()

        self.assertIn("MAP_BACKGROUNDS", js)
        # Stable asset URLs (no ?v= cache busters on map PNGs).
        self.assertIn(
            'two_entrance_two_exit: "/static/assets/generated/map-two-entrance-two-exit.png"',
            js,
        )
        self.assertIn(
            'two_entrance_one_exit: "/static/assets/generated/map-two-entrance-one-exit.png"',
            js,
        )
        self.assertIn(
            'one_entrance_two_exit: "/static/assets/generated/map-one-entrance-two-exit.png"',
            js,
        )
        self.assertNotIn("map-two-entrance-two-exit.png?v=", js)
        self.assertNotIn("map-two-entrance-one-exit.png?v=", js)
        self.assertNotIn("map-one-entrance-two-exit.png?v=", js)

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
        self.assertIn("total_cars", js)
        # Gates are set by the map; the gate overrides are no longer sent.
        self.assertNotIn("entry_gates", js)
        self.assertNotIn("exit_gates", js)
        self.assertIn("applyParamsButton", js)

    def test_frontend_switches_background_per_gate_layout(self) -> None:
        js = (self.static_dir / "app.js").read_text()

        self.assertIn("MAP_BACKGROUNDS", js)
        self.assertIn("applyMap", js)
        self.assertIn("two_entrance_two_exit", js)
        self.assertIn("custom-map", js)

    def test_frontend_builds_animated_gates_per_map(self) -> None:
        js = (self.static_dir / "app.js").read_text()
        css = (self.static_dir / "style.css").read_text()

        self.assertIn("MAP_GATES", js)
        self.assertIn("buildCustomGates", js)
        self.assertIn("map-gate", js)
        self.assertIn(".map-gate", css)
        self.assertIn(".map-gate-exit.open", css)

    def test_frontend_skips_corner_cutting_interpolation_for_gate_exit_turns(self) -> None:
        js = (self.static_dir / "app.js").read_text()

        self.assertIn("function shouldInterpolatePosition", js)
        self.assertIn('car.state !== "exiting"', js)
        self.assertIn('"merge"', js)
        self.assertIn('"road"', js)

    def test_frontend_skips_two_exit_queue_corner_interpolation(self) -> None:
        js = (self.static_dir / "app.js").read_text()

        self.assertIn('car.state === "exit_queue"', js)
        self.assertIn('car.exit_layout === "horizontal_split"', js)
        self.assertIn("Math.abs(nextCar.x - car.x) > 0.01", js)
        self.assertIn("Math.abs(nextCar.y - car.y) > 0.01", js)

    def test_entry_gate_opens_away_from_entry_queue(self) -> None:
        css = (self.static_dir / "style.css").read_text()

        self.assertIn("transform-origin: 100% 50%", css)
        self.assertIn(".entry-gate-arm.open {\n  transform: rotate(90deg);\n}", css)


if __name__ == "__main__":
    unittest.main()
