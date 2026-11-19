"""Simulate broken / hostile tool responses from scenario.mock_tools."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from runner.loader import MockTool, ToolBehavior


@dataclass
class ToolCallRecord:
    name: str
    arguments: str
    call_id: str
    result: str
    status: int | None
    behavior: ToolBehavior
    elapsed_ms: float


@dataclass
class MockToolRuntime:
    tools: dict[str, MockTool]
    history: list[ToolCallRecord] = field(default_factory=list)
    _call_counts: dict[str, int] = field(default_factory=dict)
    max_delay_ms: int | None = None  # cap sleeps (useful with --fast)

    @classmethod
    def from_list(
        cls, tools: list[MockTool], *, max_delay_ms: int | None = None
    ) -> "MockToolRuntime":
        return cls(tools={t.name: t for t in tools}, max_delay_ms=max_delay_ms)

    def openai_tools_schema(self) -> list[dict]:
        """Minimal OpenAI function-calling tool definitions."""
        schema: list[dict] = []
        for name, tool in self.tools.items():
            schema.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": (
                            f"Mock tool '{name}' (behavior={tool.behavior.value}). "
                            "Arguments are ignored by the Flawd mock server."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "input": {
                                    "type": "string",
                                    "description": "Free-form tool input",
                                }
                            },
                        },
                    },
                }
            )
        return schema

    def execute(self, name: str, *, arguments: str = "{}", call_id: str = "") -> str:
        start = time.perf_counter()
        tool = self.tools.get(name)
        if tool is None:
            result = f"ERROR: unknown tool {name!r}"
            status = 404
            behavior = ToolBehavior.error
            delay_ms = 0
        else:
            delay_ms = max(0, int(tool.delay_ms or 0))
            if self.max_delay_ms is not None:
                delay_ms = min(delay_ms, self.max_delay_ms)
            if delay_ms:
                time.sleep(delay_ms / 1000.0)
            status = tool.status
            behavior = tool.behavior
            result = self._render(tool)

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        self._call_counts[name] = self._call_counts.get(name, 0) + 1
        self.history.append(
            ToolCallRecord(
                name=name,
                arguments=arguments or "{}",
                call_id=call_id or f"call_{len(self.history)+1}",
                result=result,
                status=status,
                behavior=behavior,
                elapsed_ms=elapsed_ms,
            )
        )
        return result

    def _render(self, tool: MockTool) -> str:
        body = tool.body if tool.body is not None else ""
        if tool.behavior == ToolBehavior.success:
            return body
        if tool.behavior == ToolBehavior.inject:
            return body
        if tool.behavior == ToolBehavior.malformed_json:
            return body
        if tool.behavior == ToolBehavior.timeout:
            # delay already applied; return gateway-style failure text
            return body or f"ERROR {tool.status or 504}: tool timed out"
        if tool.behavior == ToolBehavior.error:
            code = tool.status or 500
            return body or f"ERROR {code}"
        return body

    def call_count(self, name: str | None = None) -> int:
        if name is None:
            return len(self.history)
        return self._call_counts.get(name, 0)

    def max_consecutive_repeats(self, name: str) -> int:
        best = 0
        cur = 0
        for rec in self.history:
            if rec.name == name:
                cur += 1
                best = max(best, cur)
            else:
                cur = 0
        return best
