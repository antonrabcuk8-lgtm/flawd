# Flawd scenario catalog (`FLAWD-2026`)

## Status meanings

| Status | Meaning |
|--------|---------|
| `draft` | Writable card; may not yet pass the dual reference-agent check |
| `verified` | Reproduced under the Flawd runner: **FAIL** on `examples/vulnerable_agent.py` and **PASS** on `examples/hardened_agent.py` |

`verified` does **not** mean “CVE assigned”, “vendor confirmed”, or “CrewAI/LangChain bug still open”. It only means Flawd’s reference harness demonstrates the failure mode and the mitigation pattern.

## Provenance key

- **github-inspired** — grounded in a public GitHub issue; the runnable harness (`prompt` / `mock_tools` / `assertions`) is a Flawd adaptation
- **synthetic** — constructed combat card for a well-known failure class (may cite related issues for motivation)

## Verified suite

| ID | Title | Category | Severity | Provenance | Source |
|----|-------|----------|----------|------------|--------|
| [FLAWD-2026-0001](FLAWD-2026-0001.yaml) | Re-execution of an already succeeded side-effecting tool on retry | idempotency | critical | github-inspired | [crewAI#5802](https://github.com/crewAIInc/crewAI/issues/5802) |
| [FLAWD-2026-0002](FLAWD-2026-0002.yaml) | Guardrail retry drops upstream context | context-loss | high | github-inspired | [crewAI#8219](https://github.com/crewAIInc/crewAI/issues/8219) |
| [FLAWD-2026-0003](FLAWD-2026-0003.yaml) | Missing required tool call accepted as success | missing-tool-call | high | github-inspired | [langchain#36349](https://github.com/langchain-ai/langchain/issues/36349) |
| [FLAWD-2026-0004](FLAWD-2026-0004.yaml) | Terminal tool called repeatedly | terminal-loop | medium | github-inspired | [pydantic-ai#1429](https://github.com/pydantic/pydantic-ai/issues/1429) |
| [FLAWD-2026-0005](FLAWD-2026-0005.yaml) | Middleware-removed tool still executable | tool-policy | critical | github-inspired | [langchain#41801](https://github.com/langchain-ai/langchain/issues/41801) |
| [FLAWD-2026-0006](FLAWD-2026-0006.yaml) | Empty/malformed upstream response retry storm | empty-response | medium | synthetic | motivated by [langchain#41813](https://github.com/langchain-ai/langchain/issues/41813) |
| [FLAWD-2026-0007](FLAWD-2026-0007.yaml) | Bad tool schema → validation retry loop | schema-retry | high | github-inspired | [pydantic-ai#8350](https://github.com/pydantic/pydantic-ai/issues/8350) |
| [FLAWD-2026-0008](FLAWD-2026-0008.yaml) | Python-repr tool result trusted as data | malformed-result | medium | github-inspired | [langchain#41761](https://github.com/langchain-ai/langchain/issues/41761) |
| [FLAWD-2026-0009](FLAWD-2026-0009.yaml) | HTTP 429 unbounded tool retry | rate-limit | critical | synthetic | — |
| [FLAWD-2026-0010](FLAWD-2026-0010.yaml) | Prompt injection inside tool result | prompt-injection | critical | synthetic | — |
| [FLAWD-2026-0011](FLAWD-2026-0011.yaml) | Tool timeout/hang without circuit breaker | timeout | high | synthetic | motivated by [browser-use#4579](https://github.com/browser-use/browser-use/issues/4579) |
| [FLAWD-2026-0012](FLAWD-2026-0012.yaml) | Truncated JSON tool payload trusted | malformed-json | medium | synthetic | motivated by [langchain#41238](https://github.com/langchain-ai/langchain/issues/41238) |

**Verified counts:** 7 github-inspired · 5 synthetic

## Draft follow-ups (from #5802 discussion)

| ID | Title | Status |
|----|-------|--------|
| [FLAWD-2026-0013](FLAWD-2026-0013.yaml) | Two intentional identical charges must both execute | draft |
| [FLAWD-2026-0014](FLAWD-2026-0014.yaml) | Retry with changed arguments is a new side effect | draft |
| [FLAWD-2026-0015](FLAWD-2026-0015.yaml) | Lost response after charge must not blindly re-fire | draft |

## Required fields

Every card must include:

- `source` (`type`, optional `url`, `note`, preferred `accessed`)
- `category`, `severity`, `provenance`, `mitigation`
- `prompt`, `mock_tools`, `assertions` (prefer `min_tool_calls` + `max_tool_calls` when a tool must run exactly N times)
