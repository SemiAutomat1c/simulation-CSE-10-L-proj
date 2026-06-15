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

    def test_simulation_endpoint_returns_payload_shape(self) -> None:
        response = self.client.get("/api/simulation?scenario=baseline")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("frames", payload)
        self.assertIn("slots", payload)
        self.assertIn("metrics", payload)
        self.assertIn("current_entry_queue", payload["frames"][0])
        self.assertIn("cars", payload["frames"][0])
        self.assertIn("vehicle_type", payload["frames"][0]["cars"][0])
        self.assertIn("slot_type", payload["slots"][0])
        self.assertIn("total_motorcycles", payload["metrics"])

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
