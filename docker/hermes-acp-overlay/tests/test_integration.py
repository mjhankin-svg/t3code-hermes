import json
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


SITE_ROOT = Path(__file__).resolve().parents[1]
if str(SITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SITE_ROOT))

from acp_adapter.routing import route_for_override


class _FakeDB:
    def __init__(self, row=None, history=None):
        self.row = row
        self.history = history or []
        self.created = None
        self.updated = None

    def get_session(self, _session_id):
        return self.row

    def create_session(self, **kwargs):
        self.created = kwargs
        self.row = {
            "id": kwargs["session_id"],
            "source": kwargs["source"],
            "model": kwargs["model"],
            "model_config": json.dumps(kwargs["model_config"]),
        }

    def update_session_meta(self, session_id, model_config, model):
        self.updated = (session_id, model_config, model)

    def has_archived_messages(self, _session_id):
        return False

    def replace_messages(self, _session_id, _history, active_only=False):
        self.history = list(_history)

    def get_messages_as_conversation(self, _session_id):
        return list(self.history)


class RoutingIntegrationTests(unittest.TestCase):
    def _server(self, manager):
        from acp_adapter.server import HermesACPAgent

        return HermesACPAgent(session_manager=manager)

    def test_route_command_switches_model_and_reasoning_without_fast_tier(self) -> None:
        from acp_adapter.session import SessionManager, SessionState

        manager = SessionManager(agent_factory=lambda: SimpleNamespace(model="initial"), db=False)
        manager.save_session = lambda _session_id: None
        history = [{"role": "user", "content": "keep this"}]
        state = SessionState(
            session_id="test-session",
            agent=SimpleNamespace(model="gpt-5.6-sol", provider="openai-codex"),
            model="gpt-5.6-sol",
            history=history,
        )
        server = self._server(manager)

        response = server._cmd_route("low", state)

        self.assertEqual(state.route_mode, "low")
        self.assertEqual(state.route_id, "spark-low")
        self.assertEqual(state.model, "gpt-5.3-codex-spark")
        self.assertEqual(state.reasoning_effort, "low")
        self.assertIs(state.history, history)
        self.assertIn("Fast service tier: disabled", response)

    def test_route_auto_is_session_scoped_and_defers_classification(self) -> None:
        from acp_adapter.session import SessionManager, SessionState

        manager = SessionManager(agent_factory=lambda: SimpleNamespace(model="initial"), db=False)
        manager.save_session = lambda _session_id: None
        state = SessionState(
            session_id="test-session",
            agent=SimpleNamespace(model="gpt-5.6-sol", provider="openai-codex"),
            route_mode="max",
        )
        server = self._server(manager)

        response = server._cmd_route("auto", state)

        self.assertEqual(state.route_mode, "auto")
        self.assertIn("next prompt", response)

    def test_invalid_route_is_returned_as_chat_error(self) -> None:
        from acp_adapter.session import SessionManager, SessionState

        manager = SessionManager(agent_factory=lambda: SimpleNamespace(model="initial"), db=False)
        state = SessionState(session_id="test-session", agent=SimpleNamespace())
        response = self._server(manager)._handle_slash_command("/route impossible", state)
        self.assertIn("route must be one of", response)

    def test_route_metadata_is_persisted_and_restored(self) -> None:
        from acp_adapter.session import SessionManager, SessionState

        db = _FakeDB()
        manager = SessionManager(db=db)
        state = SessionState(
            session_id="test-session",
            agent=SimpleNamespace(provider="openai-codex"),
            model="gpt-5.6-sol",
            route_mode="xhigh",
            route_id="sol-xhigh",
            reasoning_effort="xhigh",
            history=[{"role": "user", "content": "persist me"}],
        )
        manager._persist(state)

        self.assertEqual(db.created["model_config"]["route_mode"], "xhigh")
        self.assertEqual(db.created["model_config"]["route_id"], "sol-xhigh")
        self.assertEqual(db.created["model_config"]["reasoning_effort"], "xhigh")

        manager = SessionManager(db=db)
        manager._make_agent = lambda **kwargs: SimpleNamespace(
            model=kwargs["model"], provider="openai-codex"
        )
        restored = manager._restore("test-session")

        self.assertEqual(restored.route_mode, "xhigh")
        self.assertEqual(restored.route_id, "sol-xhigh")
        self.assertEqual(restored.reasoning_effort, "xhigh")
        self.assertEqual(restored.history[0]["content"], "persist me")

    def test_make_agent_passes_explicit_reasoning_config(self) -> None:
        from acp_adapter.session import SessionManager

        captured = {}

        class FakeAgent:
            def __init__(self, **kwargs):
                captured.update(kwargs)
                self.model = kwargs["model"]

        run_agent = ModuleType("run_agent")
        run_agent.AIAgent = FakeAgent

        manager = SessionManager(db=False)
        manager._get_db = lambda: None
        config = {
            "model": {"default": "gpt-5.6-sol", "provider": "openai-codex"},
            "agent": {"reasoning_effort": "high"},
        }
        runtime = {
            "provider": "openai-codex",
            "api_mode": "codex",
            "base_url": None,
            "api_key": None,
            "command": None,
            "args": [],
        }

        with (
            patch.dict(sys.modules, {"run_agent": run_agent}),
            patch("hermes_cli.config.load_config", return_value=config),
            patch("hermes_cli.runtime_provider.resolve_runtime_provider", return_value=runtime),
        ):
            agent = manager._make_agent(
                session_id="test-session",
                cwd="/tmp",
                reasoning_effort="xhigh",
            )

        self.assertEqual(captured["reasoning_config"], {"enabled": True, "effort": "xhigh"})
        self.assertNotIn("service_tier", captured)
        self.assertEqual(agent.routing_reasoning_effort, "xhigh")

    def test_every_manual_override_uses_openai_codex_profile(self) -> None:
        for override in ("low", "medium", "high", "xhigh", "max"):
            with self.subTest(override=override):
                decision = route_for_override(override)
                self.assertTrue(decision.model.startswith("gpt-"))


if __name__ == "__main__":
    unittest.main()
