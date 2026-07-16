"""Deterministic model and reasoning routing for Hermes ACP sessions.

The router performs no network or model call. It intentionally prefers a
higher-capability route when a prompt is ambiguous: latency optimization is
limited to short, clearly read-only work.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class RouteDecision:
    route_id: str
    model: str
    effort: str
    reason: str


ROUTE_PROFILES = {
    "low": RouteDecision(
        route_id="spark-low",
        model="gpt-5.3-codex-spark",
        effort="low",
        reason="manual low-latency override",
    ),
    "medium": RouteDecision(
        route_id="terra-medium",
        model="gpt-5.6-terra",
        effort="medium",
        reason="manual routine-work override",
    ),
    "high": RouteDecision(
        route_id="sol-high",
        model="gpt-5.6-sol",
        effort="high",
        reason="manual production-work override",
    ),
    "xhigh": RouteDecision(
        route_id="sol-xhigh",
        model="gpt-5.6-sol",
        effort="xhigh",
        reason="manual difficult-work override",
    ),
    "max": RouteDecision(
        route_id="sol-max",
        model="gpt-5.6-sol",
        effort="max",
        reason="manual maximum-reasoning override",
    ),
}

_ALLOWED_OVERRIDES = ("auto", *ROUTE_PROFILES.keys())

_READ_ONLY_PATTERNS = (
    r"\b(show|list|find|locate|read|explain|summari[sz]e|format)\b",
    r"\b(check|git)\s+(the\s+)?status\b",
    r"^(what|where|when|who|which|how many)\b",
    r"^(hi|hello|thanks|thank you)\b",
)
_MUTATION_PATTERNS = (
    r"\b(add|apply|build|change|configure|create|delete|deploy|edit|fix|implement|install|migrate|modify|patch|publish|remove|rename|rotate|run|update|upgrade|write)\b",
)
_ROUTINE_PATTERNS = (
    r"\b(regression test|unit test|documentation|docs|parser|typo|formatting|refactor|test coverage)\b",
)
_HIGH_COMPLEXITY_PATTERNS = (
    r"\b(across|architecture|chief review|complex|independent(ly)?|integration|multi[- ]file|multiple systems|root cause|server and tests|verify)\b",
)
_RISK_PATTERNS = (
    r"\b(authentication|authorization|credential|data[- ]loss|database|deployment|incident|migration|production|rollback|secret|security)\b",
)
_EXPLICIT_MAX_PATTERNS = (
    r"\b(maximum reasoning|use max|route max|hardest possible)\b",
)


def _matches(text: str, patterns: tuple[str, ...]) -> list[str]:
    return [pattern for pattern in patterns if re.search(pattern, text, re.IGNORECASE)]


def _match_count(text: str, patterns: tuple[str, ...]) -> int:
    return sum(len(re.findall(pattern, text, re.IGNORECASE)) for pattern in patterns)


def _with_reason(profile: str, reason: str) -> RouteDecision:
    base = ROUTE_PROFILES[profile]
    return RouteDecision(base.route_id, base.model, base.effort, reason)


def route_for_override(value: str) -> RouteDecision:
    """Resolve a manual effort override to its approved model profile."""

    normalized = str(value or "").strip().lower()
    if normalized == "auto":
        raise ValueError("auto requires a prompt to classify")
    try:
        return ROUTE_PROFILES[normalized]
    except KeyError as exc:
        allowed = ", ".join(_ALLOWED_OVERRIDES)
        raise ValueError(f"route must be one of: {allowed}") from exc


def choose_route(prompt: str) -> RouteDecision:
    """Choose an approved route without invoking an additional model.

    Spark is selected only for short, clearly read-only prompts. Ambiguous,
    mutating, or risky prompts stay on Terra or Sol. Max requires either an
    explicit request or several independent risk and complexity signals.
    """

    text = " ".join(str(prompt or "").split())
    if not text:
        return _with_reason("high", "empty or non-text prompt; conservative default")

    explicit_max = _matches(text, _EXPLICIT_MAX_PATTERNS)
    risks = _matches(text, _RISK_PATTERNS)
    complexity = _matches(text, _HIGH_COMPLEXITY_PATTERNS)
    mutations = _matches(text, _MUTATION_PATTERNS)
    read_only = _matches(text, _READ_ONLY_PATTERNS)
    routine = _matches(text, _ROUTINE_PATTERNS)
    risk_count = _match_count(text, _RISK_PATTERNS)
    complexity_count = _match_count(text, _HIGH_COMPLEXITY_PATTERNS)

    if explicit_max or (risk_count >= 4 and complexity_count >= 2):
        return _with_reason("max", "multiple irreversible risk and complexity signals")

    if risk_count >= 2 or (risks and complexity):
        return _with_reason("xhigh", "security, production, or data-integrity risk")

    if complexity or len(text) > 500:
        return _with_reason("high", "cross-cutting or complex implementation")

    if len(text) <= 240 and read_only and not mutations and not risks:
        return _with_reason("low", "short read-only latency-sensitive task")

    if routine or mutations or len(text) <= 400:
        return _with_reason("medium", "routine bounded work")

    return _with_reason("high", "conservative default for ambiguous work")
