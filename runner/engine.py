"""OpenAI-compatible chat+tools loop against a target agent HTTP endpoint."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx

from runner.assertions import AssertionResult, all_passed, evaluate_assertions
from runner.loader import Scenario
from runner.mock_tools import MockToolRuntime


@dataclass
class RunTrace:
    scenario: Scenario
    mocks: MockToolRuntime
    messages: list[dict[str, Any]] = field(default_factory=list)
    final_text: str = ""
    total_tokens: int = 0
    duration_sec: float = 0.0
    turns: int = 0
    stopped_cleanly: bool = False
    stop_reason: str = ""
    error: str | None = None
    assertion_results: list[AssertionResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        if self.error:
            return False
        return all_passed(self.assertion_results) if self.assertion_results else False


class ScenarioEngine:
    def __init__(
        self,
        target: str,
        *,
        timeout_sec: float = 60.0,
        max_turns: int = 12,
        model: str = "flawd-target",
        api_key: str | None = None,
        max_tool_delay_ms: int | None = None,
    ) -> None:
        self.target = target.rstrip("/")
        self.timeout_sec = timeout_sec
        self.max_turns = max_turns
        self.model = model
        self.api_key = api_key
        self.max_tool_delay_ms = max_tool_delay_ms

    def run(self, scenario: Scenario) -> RunTrace:
        mocks = MockToolRuntime.from_list(
            scenario.mock_tools, max_delay_ms=self.max_tool_delay_ms
        )
        trace = RunTrace(scenario=scenario, mocks=mocks)
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are a tool-using agent under test. Use tools when needed. "
                    "Prefer finishing with a short final answer when done."
                ),
            },
            {"role": "user", "content": scenario.prompt},
        ]
        trace.messages = messages
        tools = mocks.openai_tools_schema()
        started = time.perf_counter()

        try:
            with httpx.Client(timeout=self.timeout_sec) as client:
                for turn in range(1, self.max_turns + 1):
                    trace.turns = turn
                    payload = {
                        "model": self.model,
                        "messages": messages,
                        "tools": tools,
                        "tool_choice": "auto",
                    }
                    headers = {"Content-Type": "application/json"}
                    if self.api_key:
                        headers["Authorization"] = f"Bearer {self.api_key}"

                    resp = client.post(self.target, headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    self._accumulate_usage(trace, data)

                    choice = (data.get("choices") or [{}])[0]
                    message = choice.get("message") or {}
                    finish = choice.get("finish_reason")
                    tool_calls = message.get("tool_calls") or []

                    # Persist assistant turn (OpenAI shape).
                    assistant_msg: dict[str, Any] = {
                        "role": "assistant",
                        "content": message.get("content"),
                    }
                    if tool_calls:
                        assistant_msg["tool_calls"] = tool_calls
                    messages.append(assistant_msg)

                    if tool_calls:
                        for tc in tool_calls:
                            fn = (tc.get("function") or {})
                            name = fn.get("name") or ""
                            args = fn.get("arguments") or "{}"
                            call_id = tc.get("id") or f"call_{uuid.uuid4().hex[:8]}"
                            result = mocks.execute(name, arguments=args, call_id=call_id)
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": call_id,
                                    "name": name,
                                    "content": result,
                                }
                            )
                        continue

                    # No tool calls → agent produced a final answer.
                    trace.final_text = (message.get("content") or "").strip()
                    trace.stopped_cleanly = True
                    trace.stop_reason = finish or "final_answer"
                    break
                else:
                    trace.stopped_cleanly = False
                    trace.stop_reason = f"max_turns_exceeded ({self.max_turns})"
                    # Keep last assistant text if any.
                    for msg in reversed(messages):
                        if msg.get("role") == "assistant" and msg.get("content"):
                            trace.final_text = str(msg["content"]).strip()
                            break
        except Exception as exc:
            trace.error = str(exc)
            trace.stopped_cleanly = False
            trace.stop_reason = f"engine_error: {exc}"
        finally:
            trace.duration_sec = time.perf_counter() - started
            trace.messages = messages
            trace.assertion_results = evaluate_assertions(trace)

        return trace

    @staticmethod
    def _accumulate_usage(trace: RunTrace, data: dict[str, Any]) -> None:
        usage = data.get("usage") or {}
        total = usage.get("total_tokens")
        if total is not None:
            trace.total_tokens += int(total)
            return
        # Estimate roughly if the target omits usage.
        blob = json.dumps(data, ensure_ascii=False)
        trace.total_tokens += max(1, len(blob) // 4)
