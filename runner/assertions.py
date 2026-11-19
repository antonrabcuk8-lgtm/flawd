"""Evaluate scenario.assertions against a finished run trace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from runner.loader import Assertion, AssertionType

if TYPE_CHECKING:
    from runner.engine import RunTrace


@dataclass
class AssertionResult:
    assertion: Assertion
    passed: bool
    detail: str


def evaluate_assertions(trace: "RunTrace") -> list[AssertionResult]:
    results: list[AssertionResult] = []
    for assertion in trace.scenario.assertions:
        results.append(_eval_one(assertion, trace))
    return results


def all_passed(results: list[AssertionResult]) -> bool:
    return all(r.passed for r in results)


def _eval_one(assertion: Assertion, trace: "RunTrace") -> AssertionResult:
    t = assertion.type

    if t == AssertionType.max_tool_calls:
        name = assertion.tool
        if name is None:
            return AssertionResult(assertion, False, "max_tool_calls requires tool")
        if assertion.max is None:
            return AssertionResult(assertion, False, "max_tool_calls requires max")
        count = trace.mocks.call_count(name)
        ok = count <= int(assertion.max)
        return AssertionResult(
            assertion,
            ok,
            f"{name} called {count} time(s); max allowed {int(assertion.max)}",
        )

    if t == AssertionType.min_tool_calls:
        name = assertion.tool
        if name is None:
            return AssertionResult(assertion, False, "min_tool_calls requires tool")
        if assertion.min is None:
            return AssertionResult(assertion, False, "min_tool_calls requires min")
        count = trace.mocks.call_count(name)
        ok = count >= int(assertion.min)
        return AssertionResult(
            assertion,
            ok,
            f"{name} called {count} time(s); min required {int(assertion.min)}",
        )

    if t == AssertionType.max_repeats:
        name = assertion.tool
        if name is None:
            return AssertionResult(assertion, False, "max_repeats requires tool")
        if assertion.max is None:
            return AssertionResult(assertion, False, "max_repeats requires max")
        streak = trace.mocks.max_consecutive_repeats(name)
        ok = streak <= int(assertion.max)
        return AssertionResult(
            assertion,
            ok,
            f"{name} consecutive repeats={streak}; max allowed {int(assertion.max)}",
        )

    if t == AssertionType.max_tokens:
        if assertion.max is None:
            return AssertionResult(assertion, False, "max_tokens requires max")
        used = trace.total_tokens
        ok = used <= int(assertion.max)
        return AssertionResult(
            assertion,
            ok,
            f"tokens used={used}; max allowed {int(assertion.max)}",
        )

    if t == AssertionType.max_duration_sec:
        if assertion.max is None:
            return AssertionResult(assertion, False, "max_duration_sec requires max")
        ok = trace.duration_sec <= float(assertion.max)
        return AssertionResult(
            assertion,
            ok,
            f"duration={trace.duration_sec:.2f}s; max allowed {float(assertion.max):.2f}s",
        )

    if t == AssertionType.must_not_contain:
        needle = assertion.value or ""
        if not needle:
            return AssertionResult(assertion, False, "must_not_contain requires value")
        hay = trace.final_text or ""
        # Also scan tool results — injection exfil often lands in tool transcript.
        tool_blob = "\n".join(r.result for r in trace.mocks.history)
        found = needle in hay or needle in tool_blob
        # Fail if the forbidden string appears in the *final answer*.
        # Tool mock bodies may contain the needle by design (e.g. inject payloads).
        found_final = needle in hay
        ok = not found_final
        return AssertionResult(
            assertion,
            ok,
            f"final answer {'contains' if found_final else 'does not contain'} {needle!r}"
            + (f" (also in tool transcript)" if found and not found_final else ""),
        )

    if t == AssertionType.must_stop:
        ok = trace.stopped_cleanly
        reason = trace.stop_reason or "unknown"
        return AssertionResult(
            assertion,
            ok,
            f"stopped_cleanly={ok} ({reason})",
        )

    return AssertionResult(assertion, False, f"unsupported assertion type {t}")
