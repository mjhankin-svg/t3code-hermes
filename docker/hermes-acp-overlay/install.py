#!/usr/bin/env python3
"""Install the T3 automatic-routing overlay into a pinned Hermes ACP wheel."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import py_compile
import shutil
import site


EXPECTED_HASHES = {
    "acp_adapter/server.py": "f53d20853688ef41dea41d24722bec0ca41dc2f35a7fbbfd6a8b64ff90e3ff07",
    "acp_adapter/session.py": "3f3b55d929282802c007142c10b27fc9b8e9373f303cdd4b61d45e530183f737",
}

SESSION_REPLACEMENTS = (
    (
        '    cwd: str = "."\n    model: str = ""\n    history: List[Dict[str, Any]] = field(default_factory=list)\n',
        '    cwd: str = "."\n    model: str = ""\n'
        '    route_mode: str = "auto"\n    route_id: str = "sol-high"\n'
        '    reasoning_effort: str = "high"\n'
        '    history: List[Dict[str, Any]] = field(default_factory=list)\n',
    ),
    (
        '            model=getattr(agent, "model", "") or "",\n'
        '            cancel_event=threading.Event(),\n',
        '            model=getattr(agent, "model", "") or "",\n'
        '            reasoning_effort=getattr(agent, "routing_reasoning_effort", "high"),\n'
        '            cancel_event=threading.Event(),\n',
    ),
    (
        '            model=original.model or None,\n        )\n        state = SessionState(\n',
        '            model=original.model or None,\n'
        '            reasoning_effort=original.reasoning_effort,\n'
        '        )\n        state = SessionState(\n',
    ),
    (
        '            model=getattr(agent, "model", original.model) or original.model,\n'
        '            history=copy.deepcopy(original.history),\n',
        '            model=getattr(agent, "model", original.model) or original.model,\n'
        '            route_mode=original.route_mode,\n'
        '            route_id=original.route_id,\n'
        '            reasoning_effort=original.reasoning_effort,\n'
        '            history=copy.deepcopy(original.history),\n',
    ),
    (
        '        session_meta = {"cwd": state.cwd}\n',
        '        session_meta = {\n'
        '            "cwd": state.cwd,\n'
        '            "route_mode": state.route_mode,\n'
        '            "route_id": state.route_id,\n'
        '            "reasoning_effort": state.reasoning_effort,\n'
        '        }\n',
    ),
    (
        '                    model_config={"cwd": state.cwd},\n',
        '                    model_config=session_meta,\n',
    ),
    (
        '        cwd = "."\n        requested_provider = row.get("billing_provider")\n',
        '        cwd = "."\n'
        '        route_mode = "auto"\n'
        '        route_id = "sol-high"\n'
        '        reasoning_effort = "high"\n'
        '        requested_provider = row.get("billing_provider")\n',
    ),
    (
        '                    cwd = meta.get("cwd", ".")\n'
        '                    requested_provider = meta.get("provider") or requested_provider\n',
        '                    cwd = meta.get("cwd", ".")\n'
        '                    route_mode = str(meta.get("route_mode") or route_mode)\n'
        '                    route_id = str(meta.get("route_id") or route_id)\n'
        '                    reasoning_effort = str(\n'
        '                        meta.get("reasoning_effort") or reasoning_effort\n'
        '                    )\n'
        '                    requested_provider = meta.get("provider") or requested_provider\n',
    ),
    (
        '                base_url=restored_base_url,\n'
        '                api_mode=restored_api_mode,\n'
        '            )\n',
        '                base_url=restored_base_url,\n'
        '                api_mode=restored_api_mode,\n'
        '                reasoning_effort=reasoning_effort,\n'
        '            )\n',
    ),
    (
        '            model=model or getattr(agent, "model", "") or "",\n'
        '            history=history,\n',
        '            model=model or getattr(agent, "model", "") or "",\n'
        '            route_mode=route_mode,\n'
        '            route_id=route_id,\n'
        '            reasoning_effort=reasoning_effort,\n'
        '            history=history,\n',
    ),
    (
        '        base_url: str | None = None,\n'
        '        api_mode: str | None = None,\n'
        '    ):\n',
        '        base_url: str | None = None,\n'
        '        api_mode: str | None = None,\n'
        '        reasoning_effort: str | None = None,\n'
        '    ):\n',
    ),
    (
        '        elif isinstance(model_cfg, str) and model_cfg.strip():\n'
        '            default_model = model_cfg.strip()\n\n'
        '        configured_mcp_servers = [\n',
        '        elif isinstance(model_cfg, str) and model_cfg.strip():\n'
        '            default_model = model_cfg.strip()\n\n'
        '        agent_cfg = config.get("agent")\n'
        '        configured_effort = "medium"\n'
        '        if isinstance(agent_cfg, dict):\n'
        '            configured_effort = str(\n'
        '                agent_cfg.get("reasoning_effort") or configured_effort\n'
        '            ).strip().lower()\n'
        '        effective_effort = str(reasoning_effort or configured_effort).strip().lower()\n'
        '        if effective_effort not in {"low", "medium", "high", "xhigh", "max"}:\n'
        '            effective_effort = "high"\n\n'
        '        configured_mcp_servers = [\n',
    ),
    (
        '            "session_db": self._get_db(),\n'
        '            "model": model or default_model,\n'
        '        }\n',
        '            "session_db": self._get_db(),\n'
        '            "model": model or default_model,\n'
        '            "reasoning_config": {"enabled": True, "effort": effective_effort},\n'
        '        }\n',
    ),
    (
        '        agent.session_cwd = cwd\n'
        '        # ACP stdio transport requires stdout to remain protocol-only JSON-RPC.\n',
        '        agent.session_cwd = cwd\n'
        '        agent.routing_reasoning_effort = effective_effort\n'
        '        # ACP stdio transport requires stdout to remain protocol-only JSON-RPC.\n',
    ),
)

SERVER_REPLACEMENTS = (
    (
        'from acp_adapter.permissions import make_approval_callback\n'
        'from acp_adapter.provenance import session_provenance_meta\n',
        'from acp_adapter.permissions import make_approval_callback\n'
        'from acp_adapter.provenance import session_provenance_meta\n'
        'from acp_adapter.routing import RouteDecision, choose_route, route_for_override\n',
    ),
    (
        '        "model": "Show or change current model",\n'
        '        "tools": "List available tools",\n',
        '        "model": "Show or change current model",\n'
        '        "route": "Show or override automatic model/reasoning routing",\n'
        '        "tools": "List available tools",\n',
    ),
    (
        '        {\n'
        '            "name": "tools",\n'
        '            "description": "List available tools with descriptions",\n'
        '        },\n',
        '        {\n'
        '            "name": "route",\n'
        '            "description": "Show routing or set auto/low/medium/high/xhigh/max",\n'
        '            "input_hint": "auto, low, medium, high, xhigh, or max",\n'
        '        },\n'
        '        {\n'
        '            "name": "tools",\n'
        '            "description": "List available tools with descriptions",\n'
        '        },\n',
    ),
    (
        '            "model": self._cmd_model,\n'
        '            "tools": self._cmd_tools,\n',
        '            "model": self._cmd_model,\n'
        '            "route": self._cmd_route,\n'
        '            "tools": self._cmd_tools,\n',
    ),
    (
        '        logger.info("Prompt on session %s: %s", session_id, user_text[:100])\n\n'
        '        conn = self._conn\n',
        '        if getattr(state, "route_mode", "auto") == "auto":\n'
        '            try:\n'
        '                self._apply_route(state, choose_route(user_text))\n'
        '            except Exception:\n'
        '                logger.exception("Automatic routing failed for session %s", session_id)\n\n'
        '        logger.info(\n'
        '            "Prompt on session %s via %s (%s/%s): %s",\n'
        '            session_id,\n'
        '            getattr(state, "route_id", "unknown"),\n'
        '            state.model,\n'
        '            getattr(state, "reasoning_effort", "unknown"),\n'
        '            user_text[:100],\n'
        '        )\n\n'
        '        conn = self._conn\n',
    ),
    (
        '    def _cmd_model(self, args: str, state: SessionState) -> str:\n',
        '    def _apply_route(self, state: SessionState, decision: RouteDecision) -> None:\n'
        '        current_model = state.model or getattr(state.agent, "model", "")\n'
        '        current_effort = getattr(state, "reasoning_effort", "")\n'
        '        if current_model == decision.model and current_effort == decision.effort:\n'
        '            state.route_id = decision.route_id\n'
        '            return\n\n'
        '        state.agent = self.session_manager._make_agent(\n'
        '            session_id=state.session_id,\n'
        '            cwd=state.cwd,\n'
        '            model=decision.model,\n'
        '            requested_provider="openai-codex",\n'
        '            reasoning_effort=decision.effort,\n'
        '        )\n'
        '        state.model = decision.model\n'
        '        state.route_id = decision.route_id\n'
        '        state.reasoning_effort = decision.effort\n'
        '        self.session_manager.save_session(state.session_id)\n'
        '        logger.info(\n'
        '            "Session %s routed to %s (%s/%s): %s",\n'
        '            state.session_id,\n'
        '            decision.route_id,\n'
        '            decision.model,\n'
        '            decision.effort,\n'
        '            decision.reason,\n'
        '        )\n\n'
        '    def _cmd_route(self, args: str, state: SessionState) -> str:\n'
        '        normalized = str(args or "").strip().lower()\n'
        '        if not normalized:\n'
        '            mode = getattr(state, "route_mode", "auto")\n'
        '            route_id = getattr(state, "route_id", "sol-high")\n'
        '            effort = getattr(state, "reasoning_effort", "high")\n'
        '            return (\n'
        '                f"Routing mode: {mode}\\nRoute: {route_id}\\n"\n'
        '                f"Model: {state.model}\\nReasoning effort: {effort}\\n"\n'
        '                "Fast service tier: disabled"\n'
        '            )\n\n'
        '        if normalized == "auto":\n'
        '            state.route_mode = "auto"\n'
        '            self.session_manager.save_session(state.session_id)\n'
        '            return "Automatic routing enabled. The next prompt will be classified."\n\n'
        '        decision = route_for_override(normalized)\n'
        '        state.route_mode = normalized\n'
        '        self._apply_route(state, decision)\n'
        '        return (\n'
        '            f"Routing override: {normalized}\\nModel: {decision.model}\\n"\n'
        '            f"Reasoning effort: {decision.effort}\\nFast service tier: disabled"\n'
        '        )\n\n'
        '    def _cmd_model(self, args: str, state: SessionState) -> str:\n',
    ),
    (
        '        state.model = new_model\n'
        '        state.agent = self.session_manager._make_agent(\n',
        '        state.model = new_model\n'
        '        state.route_mode = "manual-model"\n'
        '        state.route_id = "manual-model"\n'
        '        state.agent = self.session_manager._make_agent(\n',
    ),
    (
        '            requested_provider=target_provider,\n'
        '        )\n'
        '        self.session_manager.save_session(state.session_id)\n',
        '            requested_provider=target_provider,\n'
        '            reasoning_effort=getattr(state, "reasoning_effort", "high"),\n'
        '        )\n'
        '        self.session_manager.save_session(state.session_id)\n',
    ),
    (
        '            state.model = resolved_model\n'
        '            provider_changed = bool(current_provider and requested_provider != current_provider)\n',
        '            state.model = resolved_model\n'
        '            state.route_mode = "manual-model"\n'
        '            state.route_id = "manual-model"\n'
        '            provider_changed = bool(current_provider and requested_provider != current_provider)\n',
    ),
    (
        '                base_url=current_base_url,\n'
        '                api_mode=current_api_mode,\n'
        '            )\n',
        '                base_url=current_base_url,\n'
        '                api_mode=current_api_mode,\n'
        '                reasoning_effort=getattr(state, "reasoning_effort", "high"),\n'
        '            )\n',
    ),
)


def _replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one patch anchor, found {count}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def install(site_packages: Path) -> None:
    site_packages = Path(site_packages).resolve()
    for relative, expected in EXPECTED_HASHES.items():
        path = site_packages / relative
        actual = sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"{relative}: expected sha256 {expected}, got {actual}")

    session_path = site_packages / "acp_adapter/session.py"
    server_path = site_packages / "acp_adapter/server.py"
    for old, new in SESSION_REPLACEMENTS:
        _replace_once(session_path, old, new)
    for old, new in SERVER_REPLACEMENTS:
        _replace_once(server_path, old, new)

    source_router = Path(__file__).parent / "acp_adapter/routing.py"
    target_router = site_packages / "acp_adapter/routing.py"
    shutil.copyfile(source_router, target_router)

    for path in (session_path, server_path, target_router):
        py_compile.compile(str(path), doraise=True)


if __name__ == "__main__":
    install(Path(site.getsitepackages()[0]))
