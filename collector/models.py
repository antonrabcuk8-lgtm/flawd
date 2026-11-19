"""Shared data shapes for the collector pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RawFinding:
    source: str  # "github" | "reddit"
    item_id: str
    url: str
    title: str
    body: str
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TriageResult:
    draft_id: str
    relevance: int
    title: str
    summary: str
    failure_mechanism: str
    reproduction_hints: list[str]
    tags: list[str]
    source_url: str
    source: str
    item_id: str
    raw_notes: str = ""
    prompt: str = ""
    mock_tools: list[dict[str, Any]] = field(default_factory=list)
    assertions: list[dict[str, Any]] = field(default_factory=list)

    def to_yaml_dict(self) -> dict[str, Any]:
        return {
            "id": self.draft_id,
            "status": "draft",
            "relevance": self.relevance,
            "title": self.title,
            "summary": self.summary,
            "failure_mechanism": self.failure_mechanism,
            "prompt": self.prompt or None,
            "reproduction_hints": self.reproduction_hints,
            "mock_tools": self.mock_tools,
            "assertions": self.assertions,
            "tags": self.tags,
            "source": {
                "type": self.source,
                "id": self.item_id,
                "url": self.source_url,
            },
            "notes": self.raw_notes or None,
        }
