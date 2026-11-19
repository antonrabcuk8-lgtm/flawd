"""Load and validate FLAWD scenario YAML files with Pydantic."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE = ROOT / "database"


class ToolBehavior(str, Enum):
    success = "success"
    error = "error"
    timeout = "timeout"
    malformed_json = "malformed_json"
    inject = "inject"


class AssertionType(str, Enum):
    max_tool_calls = "max_tool_calls"
    min_tool_calls = "min_tool_calls"
    max_repeats = "max_repeats"
    max_tokens = "max_tokens"
    max_duration_sec = "max_duration_sec"
    must_not_contain = "must_not_contain"
    must_stop = "must_stop"


class MockTool(BaseModel):
    name: str
    behavior: ToolBehavior = ToolBehavior.success
    status: int | None = 200
    delay_ms: int = 0
    body: str = ""


class Assertion(BaseModel):
    type: AssertionType
    tool: str | None = None
    min: int | float | None = None
    max: int | float | None = None
    value: str | None = None


class SourceInfo(BaseModel):
    type: str = "unknown"  # github | synthetic | ...
    id: str | int | None = None
    url: str | None = None
    note: str | None = None
    accessed: str | None = None  # YYYY-MM-DD when the source URL was checked


class Scenario(BaseModel):
    id: str
    status: str = "draft"
    relevance: int = Field(default=5, ge=1, le=10)
    title: str
    summary: str = ""
    failure_mechanism: str = ""
    category: str = "uncategorized"
    severity: str = "medium"  # critical | high | medium | low
    provenance: str = "synthetic"  # github-inspired | synthetic
    mitigation: str = ""
    prompt: str
    reproduction_hints: list[str] = Field(default_factory=list)
    mock_tools: list[MockTool] = Field(default_factory=list)
    assertions: list[Assertion] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source: SourceInfo = Field(default_factory=SourceInfo)
    notes: str | None = None

    @field_validator("tags", mode="before")
    @classmethod
    def _coerce_tags(cls, value: Any) -> list[str]:
        if value is None:
            return []
        return [str(v) for v in value]

    @field_validator("mock_tools")
    @classmethod
    def _need_tools(cls, value: list[MockTool]) -> list[MockTool]:
        if not value:
            raise ValueError("scenario must declare at least one mock_tool")
        return value

    @field_validator("assertions")
    @classmethod
    def _need_assertions(cls, value: list[Assertion]) -> list[Assertion]:
        if not value:
            raise ValueError("scenario must declare at least one assertion")
        return value

    def tool_map(self) -> dict[str, MockTool]:
        return {t.name: t for t in self.mock_tools}


def load_scenario(path: Path | str) -> Scenario:
    path = Path(path)
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: expected a YAML mapping")
    scenario = Scenario.model_validate(raw)
    if scenario.id != path.stem and not path.stem.endswith(scenario.id):
        # Allow stem == id (normal case); warn-level mismatch is hard error for clarity.
        if path.stem != scenario.id:
            raise ValueError(f"{path.name}: id {scenario.id!r} != filename stem {path.stem!r}")
    return scenario


def load_database(
    database_dir: Path | str = DEFAULT_DATABASE,
    *,
    only_verified: bool = True,
    scenario_ids: list[str] | None = None,
) -> list[Scenario]:
    database_dir = Path(database_dir)
    if not database_dir.is_dir():
        raise FileNotFoundError(f"database dir not found: {database_dir}")

    scenarios: list[Scenario] = []
    for path in sorted(database_dir.glob("FLAWD-*.yaml")):
        if path.name.endswith(".example.yaml"):
            continue
        scenario = load_scenario(path)
        if only_verified and scenario.status != "verified":
            continue
        if scenario_ids and scenario.id not in scenario_ids:
            continue
        scenarios.append(scenario)
    return scenarios
