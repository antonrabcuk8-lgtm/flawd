"""Gate 1: rule-based agent-failure classifier (cheap, no LLM required for P1)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from collector.rejection import AGENT_FAILURE_CATEGORIES, RejectionCode


@dataclass
class Classification:
    is_agent_failure: bool
    category: str | None
    confidence: float
    rejection_code: RejectionCode | None = None
    detail: str = ""


# (category, patterns, weight)
_POSITIVE: list[tuple[str, tuple[str, ...], float]] = [
    (
        "idempotency",
        ("idempoten", "re-execut", "duplicate payment", "duplicate email", "retry.*tool", "task retry"),
        0.95,
    ),
    (
        "terminal-loop",
        ("final_result", "multiple times", "calls.*again", "keeps calling", "hammer"),
        0.9,
    ),
    (
        "missing-tool-call",
        ("forget to make a tool call", "without.*tool call", "no tool call", "omit.*tool"),
        0.92,
    ),
    (
        "tool-policy",
        ("removed from request.tools", "middleware", "still runs a tool", "tool denylist", "should not.*tool"),
        0.9,
    ),
    (
        "rate-limit",
        ("429", "rate limit", "too many requests", "retry-after"),
        0.9,
    ),
    (
        "prompt-injection",
        ("prompt injection", "ignore previous", "exfiltrat", "jailbreak"),
        0.95,
    ),
    (
        "timeout",
        ("timeout", "hang", "indefinite", "stuck", "unresponsive", "websocket.*drop"),
        0.85,
    ),
    (
        "malformed-json",
        ("malformed json", "invalid json", "truncated json", "jsondecode"),
        0.88,
    ),
    (
        "malformed-result",
        ("python repr", "toolmessage.content", "not.*json", "serialize"),
        0.8,
    ),
    (
        "schema-retry",
        ("field required", "validation", "retry", "args", "required.*parameter"),
        0.75,
    ),
    (
        "context-loss",
        ("drops the context", "context var", "lost context", "checkpoint", "guardrail retry"),
        0.88,
    ),
    (
        "empty-response",
        (r"choices.?\[\s*\]", "empty choices", "indexerror", "no choices"),
        0.85,
    ),
    (
        "tool-loop",
        ("infinite loop", "tool loop", "unbounded", "keeps retry"),
        0.9,
    ),
    (
        "provider-tool-mismatch",
        ("tool calling works with", "fails with llama", "bedrock", "function calling", "tool call.*fail"),
        0.8,
    ),
    (
        "context-poison",
        ("screenshot", "poisons", "context → api 400", "blob in tool result", "grows message history"),
        0.82,
    ),
]

_NEGATIVE: tuple[str, ...] = (
    r"\bdocs?\b",
    r"\bcve\b",
    r"vulnerabilit",
    r"dependency",
    r"typo",
    r"readme",
    r"install",
    r"feature request",
    r"\bquestion:\b",
    r"how (do|can) i",
    r"import error at module",
    r"can't be extended",
    r"aws lambda crash at import",
    r"pip dependency",
    r"os\.kill",
    r"high-dpi",
    r"coordinate offset",
)


def classify_text(title: str, body: str = "") -> Classification:
    blob = f"{title}\n{body}".lower()

    for pat in _NEGATIVE:
        if re.search(pat, blob, re.IGNORECASE):
            # Still allow override if a strong positive agent signal is present.
            strong = any(
                re.search(p, blob, re.IGNORECASE)
                for _, patterns, w in _POSITIVE
                if w >= 0.9
                for p in patterns
            )
            if not strong:
                return Classification(
                    False,
                    None,
                    0.2,
                    RejectionCode.G1_NOT_AGENT_FAILURE,
                    f"matched negative pattern {pat!r}",
                )

    best_cat: str | None = None
    best_score = 0.0
    hits: list[str] = []
    for cat, patterns, weight in _POSITIVE:
        for p in patterns:
            if re.search(p, blob, re.IGNORECASE):
                score = weight
                if score > best_score:
                    best_score = score
                    best_cat = cat
                hits.append(f"{cat}:{p}")
                break

    if best_cat and best_score >= 0.75:
        conf = min(0.98, best_score + 0.02 * max(0, len(hits) - 1))
        return Classification(True, best_cat, conf, None, f"hits={hits[:5]}")

    if best_cat:
        return Classification(
            False,
            best_cat,
            best_score,
            RejectionCode.G1_TOO_VAGUE,
            f"weak signal hits={hits[:5]}",
        )

    return Classification(
        False,
        None,
        0.1,
        RejectionCode.G1_TOO_VAGUE,
        "no agent-failure markers",
    )


def known_categories() -> tuple[str, ...]:
    return AGENT_FAILURE_CATEGORIES
