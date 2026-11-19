# Flawd scenario catalog (`FLAWD-2026`)

## Status meanings

| Status | Meaning |
|--------|---------|
| `draft` | Writable card; may not yet pass the dual reference-agent check |
| `verified` | Reproduced under the Flawd runner: **FAIL** on `examples/vulnerable_agent.py` and **PASS** on `examples/hardened_agent.py` |

`verified` does **not** mean “CVE assigned”, “vendor confirmed”, or “upstream bug still open”.

## Provenance key

- **github-inspired** — grounded in a public GitHub issue; harness is a Flawd adaptation
- **synthetic** — constructed combat card (may cite related issues for motivation)

## Verified suite (25)

| ID | Category | Severity | Provenance |
|----|----------|----------|------------|
| [0001](FLAWD-2026-0001.yaml) | idempotency | critical | github-inspired |
| [0002](FLAWD-2026-0002.yaml) | context-loss | high | github-inspired |
| [0003](FLAWD-2026-0003.yaml) | missing-tool-call | high | github-inspired |
| [0004](FLAWD-2026-0004.yaml) | terminal-loop | medium | github-inspired |
| [0005](FLAWD-2026-0005.yaml) | tool-policy | critical | github-inspired |
| [0006](FLAWD-2026-0006.yaml) | empty-response | medium | synthetic |
| [0007](FLAWD-2026-0007.yaml) | schema-retry | high | github-inspired |
| [0008](FLAWD-2026-0008.yaml) | malformed-result | medium | github-inspired |
| [0009](FLAWD-2026-0009.yaml) | rate-limit | critical | synthetic |
| [0010](FLAWD-2026-0010.yaml) | prompt-injection | critical | synthetic |
| [0011](FLAWD-2026-0011.yaml) | timeout | high | synthetic |
| [0012](FLAWD-2026-0012.yaml) | malformed-json | medium | synthetic |
| [0016](FLAWD-2026-0016.yaml) | provider-tool-mismatch | high | github-inspired |
| [0017](FLAWD-2026-0017.yaml) | context-poison | high | github-inspired |
| [0018](FLAWD-2026-0018.yaml) | context-loss | medium | github-inspired |
| [0019](FLAWD-2026-0019.yaml) | tool-policy | high | github-inspired |
| [0020](FLAWD-2026-0020.yaml) | timeout | high | github-inspired |
| [0021](FLAWD-2026-0021.yaml) | context-loss | medium | github-inspired |
| [0022](FLAWD-2026-0022.yaml) | timeout | medium | github-inspired |
| [0023](FLAWD-2026-0023.yaml) | tool-policy | high | github-inspired |
| [0024](FLAWD-2026-0024.yaml) | context-loss | high | github-inspired |
| [0025](FLAWD-2026-0025.yaml) | tool-policy | critical | github-inspired |
| [0026](FLAWD-2026-0026.yaml) | timeout | medium | github-inspired |
| [0027](FLAWD-2026-0027.yaml) | schema-retry | medium | synthetic |
| [0028](FLAWD-2026-0028.yaml) | missing-tool-call | high | synthetic |

**Counts:** 25 verified (≈19 github-inspired · ≈6 synthetic) · 3 draft follow-ups (`0013`–`0015`)

## Draft follow-ups

| ID | Title | Status |
|----|-------|--------|
| [0013](FLAWD-2026-0013.yaml) | Two intentional identical charges | draft |
| [0014](FLAWD-2026-0014.yaml) | Retry with changed arguments | draft |
| [0015](FLAWD-2026-0015.yaml) | Lost response after charge | draft |

## Required fields

- `source` (`type`, optional `url`, `note`, preferred `accessed`)
- `category`, `severity`, `provenance`, `mitigation`
- `prompt`, `mock_tools`, `assertions` (prefer `min_tool_calls` + `max_tool_calls` for exactly-N)
