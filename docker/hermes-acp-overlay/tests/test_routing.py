import unittest

from acp_adapter.routing import ROUTE_PROFILES, choose_route, route_for_override


class AutomaticRoutingTests(unittest.TestCase):
    def test_short_read_only_status_uses_spark_low(self) -> None:
        decision = choose_route("Show the current git status.")

        self.assertEqual(decision.route_id, "spark-low")
        self.assertEqual(decision.model, "gpt-5.3-codex-spark")
        self.assertEqual(decision.effort, "low")

    def test_routine_implementation_uses_terra_medium(self) -> None:
        decision = choose_route("Add a regression test for the existing parser bug.")

        self.assertEqual(decision.route_id, "terra-medium")
        self.assertEqual(decision.model, "gpt-5.6-terra")
        self.assertEqual(decision.effort, "medium")

    def test_production_implementation_uses_sol_high(self) -> None:
        decision = choose_route(
            "Implement the approved routing feature across the server and tests, then verify it."
        )

        self.assertEqual(decision.route_id, "sol-high")
        self.assertEqual(decision.model, "gpt-5.6-sol")
        self.assertEqual(decision.effort, "high")

    def test_security_architecture_escalates_to_xhigh(self) -> None:
        decision = choose_route(
            "Design the authentication architecture and review it for credential exposure."
        )

        self.assertEqual(decision.route_id, "sol-xhigh")
        self.assertEqual(decision.effort, "xhigh")

    def test_multiple_irreversible_risks_escalate_to_max(self) -> None:
        decision = choose_route(
            "Plan and independently review a production database migration with rollback, "
            "data-loss prevention, credential rotation, and security architecture changes."
        )

        self.assertEqual(decision.route_id, "sol-max")
        self.assertEqual(decision.effort, "max")

    def test_mutating_prompt_never_uses_spark(self) -> None:
        decision = choose_route("Delete the obsolete deployment configuration.")

        self.assertNotEqual(decision.model, "gpt-5.3-codex-spark")

    def test_manual_override_maps_effort_to_approved_model(self) -> None:
        expected = {
            "low": ("gpt-5.3-codex-spark", "low"),
            "medium": ("gpt-5.6-terra", "medium"),
            "high": ("gpt-5.6-sol", "high"),
            "xhigh": ("gpt-5.6-sol", "xhigh"),
            "max": ("gpt-5.6-sol", "max"),
        }

        for override, route in expected.items():
            with self.subTest(override=override):
                decision = route_for_override(override)
                self.assertEqual((decision.model, decision.effort), route)

    def test_fast_service_tier_is_not_part_of_any_profile(self) -> None:
        for profile in ROUTE_PROFILES.values():
            self.assertNotIn("fast", profile.route_id)
            self.assertNotIn("fast", profile.model)
            self.assertFalse(hasattr(profile, "service_tier"))

    def test_invalid_override_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "auto, low, medium, high, xhigh, max"):
            route_for_override("ultra")


if __name__ == "__main__":
    unittest.main()
