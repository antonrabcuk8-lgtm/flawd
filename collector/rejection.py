"""Rejection / pipeline status codes for the ingestion gates."""

from __future__ import annotations

from enum import Enum


class FindingState(str, Enum):
    RAW = "raw"
    CANDIDATE = "candidate"
    DRAFT = "draft"
    VALIDATED = "validated"
    PUBLISHED = "published"
    REJECTED = "rejected"
    MERGED = "merged"
    STALE = "stale"


class RejectionCode(str, Enum):
    G1_NOT_AGENT_FAILURE = "G1_NOT_AGENT_FAILURE"
    G1_TOO_VAGUE = "G1_TOO_VAGUE"
    G1_DUPLICATE_MERGED = "G1_DUPLICATE_MERGED"
    G2_OUT_OF_SCOPE = "G2_OUT_OF_SCOPE"
    G2_UNSUPPORTED_PRIMITIVE = "G2_UNSUPPORTED_PRIMITIVE"
    G3_SCHEMA_INVALID = "G3_SCHEMA_INVALID"
    G3_GENERATION_FAILED = "G3_GENERATION_FAILED"
    G4_VULN_DID_NOT_FAIL = "G4_VULN_DID_NOT_FAIL"
    G4_HARDENED_DID_NOT_PASS = "G4_HARDENED_DID_NOT_PASS"
    G4_FLAKY = "G4_FLAKY"
    G4_CONTROL_FALSE_POSITIVE = "G4_CONTROL_FALSE_POSITIVE"
    G4_NEEDS_HUMAN = "G4_NEEDS_HUMAN"
    G5_HUMAN_REJECT = "G5_HUMAN_REJECT"
    G6_STALE = "G6_STALE"


# Cheap local taxonomy for Gate 1 (rule-based in P1; LLM later).
AGENT_FAILURE_CATEGORIES = (
    "idempotency",
    "rate-limit",
    "prompt-injection",
    "timeout",
    "malformed-json",
    "malformed-result",
    "missing-tool-call",
    "tool-policy",
    "context-loss",
    "schema-retry",
    "terminal-loop",
    "empty-response",
    "tool-loop",
    "provider-tool-mismatch",
    "context-poison",
)
