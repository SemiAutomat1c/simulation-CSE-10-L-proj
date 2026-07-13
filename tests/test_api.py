import unittest

from fastapi.testclient import TestClient

from app.api import SCENARIOS, create_app


class ParkingApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_scenarios_endpoint_returns_expected_names(self) -> None:
        response = self.client.get("/api/scenarios")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()["scenarios"].keys()), set(SCENARIOS.keys()))

    def test_simulation_default_is_compact(self) -> None:
        response = self.client.get("/api/simulation?scenario=baseline")
        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload.get("format"), "compact")
        self.assertIn("keyframes", payload)
        self.assertIn("roster", payload)
        self.assertIn("metrics", payload)
        self.assertNotIn("frames", payload)

    def test_simulation_full_format_still_available(self) -> None:
        response = self.client.get("/api/simulation?scenario=baseline&format=full")
        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertIn("frames", payload)
        self.assertIn("cars", payload["frames"][0])
        self.assertIn("vehicle_type", payload["frames"][0]["cars"][0])

    def test_simulation_cache_hit_skips_second_run(self) -> None:
        from app import api as api_module

        api_module._simulation_cache.clear()
        # Patch run counter: wrap run_simulation
        calls = {"n": 0}
        original = api_module.run_simulation

        def counting(config):
            calls["n"] += 1
            return original(config)

        api_module.run_simulation = counting
        try:
            r1 = self.client.get("/api/simulation?scenario=baseline&map=one_entrance_one_exit")
            r2 = self.client.get("/api/simulation?scenario=baseline&map=one_entrance_one_exit")
            self.assertEqual(r1.status_code, 200)
            self.assertEqual(r2.status_code, 200)
            self.assertEqual(r1.json(), r2.json())
            self.assertEqual(calls["n"], 1)
        finally:
            api_module.run_simulation = original

    def test_static_assets_have_long_cache_headers(self) -> None:
        response = self.client.get("/static/assets/generated/custom-parking-background.png")
        self.assertEqual(response.status_code, 200)
        cache = response.headers.get("cache-control", "").lower()
        self.assertTrue("max-age" in cache or "public" in cache)

    def test_unknown_scenario_falls_back_to_baseline(self) -> None:
        response = self.client.get("/api/simulation?scenario=not-real")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["scenario"], "baseline")

    def test_compare_endpoint_returns_metrics_for_all_scenarios(self) -> None:
        response = self.client.get("/api/compare")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(payload["scenarios"].keys()), set(SCENARIOS.keys()))
        baseline = payload["scenarios"]["baseline"]["metrics"]
        for key in (
            "average_entry_wait_minutes",
            "average_exit_wait_minutes",
            "throughput_vehicles_per_hour",
            "entry_gate_utilization_percent",
        ):
            self.assertIn(key, baseline)
        # Metrics-only payload keeps the comparison response lightweight.
        self.assertNotIn("frames", payload["scenarios"]["baseline"])


if __name__ == "__main__":
    unittest.main()
