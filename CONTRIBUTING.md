# Contributing to Flawd

Thanks for helping grow an honest catalog of AI-agent failures.

## Ways to contribute

1. **Report a failure** — open a [Submit a failure](https://github.com/antonrabcuk8-lgtm/flawd/issues/new?template=submit_failure.yml) issue (no YAML required).
2. **Add a scenario card** — PR a `database/FLAWD-YYYY-XXXX.yaml` file.
3. **Improve the runner** — mocks, assertions, adapters for more agent protocols.

## Scenario schema (required)

```yaml
id: FLAWD-2026-00XX
status: draft          # draft | verified
provenance: synthetic  # github-inspired | synthetic
category: rate-limit
severity: high         # critical | high | medium | low
mitigation: "What a correct agent should do"
title: "..."
summary: "..."
failure_mechanism: "..."
prompt: "User prompt that triggers the failure"
mock_tools:
  - name: example_tool
    behavior: error    # success | error | timeout | malformed_json | inject
    status: 429
    delay_ms: 0
    body: "Too Many Requests"
assertions:
  - type: max_tool_calls
    tool: example_tool
    max: 3
source:
  type: github         # github | synthetic
  url: https://github.com/org/repo/issues/123   # required for github-inspired
  note: "What is from the issue vs what Flawd adapted"
```

Validate locally:

```bash
python -c "from runner.loader import load_scenario; print(load_scenario('database/FLAWD-2026-0001.yaml').id)"
```

## Provenance rules

- Mark **github-inspired** only when a public issue clearly motivates the failure mode, and link it.
- Mark **synthetic** when the card is a constructed combat test (even if vaguely “inspired by” the wild).
- Do not claim “CVE” assignment — Flawd IDs are project-local.

## PR checklist

- [ ] `provenance` / `source` are honest
- [ ] `mock_tools` + `assertions` make the card runnable
- [ ] Card loads via `runner.loader`
- [ ] `database/README.md` table updated
