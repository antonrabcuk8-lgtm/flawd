# Flawd

[![Flawd Agent Reliability CI](https://github.com/antonrabcuk8-lgtm/flawd/actions/workflows/flawd-ci.yml/badge.svg)](https://github.com/antonrabcuk8-lgtm/flawd/actions/workflows/flawd-ci.yml)

**The Open-Source CVE Database & Crash-Test Runner for AI Agents.**

AI agents fail in production in predictable, expensive ways: infinite tool-calling loops, overnight API bill drains, hallucinated JSON parameters, and indirect prompt injections.

**Flawd** provides a standardized, machine-readable catalog of real-world agent postmortems (`FLAWD-YYYY-XXXX`) and a lightweight test runner to stress-test your agent before deployment.

## Proof of Concept: Vulnerable vs. Hardened

We tested two FastAPI agents against the core `FLAWD-2026` suite (12 real-world failure scenarios):

| Target Agent | Protection Level | Score | Outcome |
| :--- | :--- | :--- | :--- |
| `examples/vulnerable_agent.py` | Raw LLM + tools (no guards) | **0 / 12 PASS** | Caught in retry loops, leaked secrets, executed injected instructions |
| `examples/hardened_agent.py` | Retry limits, idempotency, tool denylist | **12 / 12 PASS** | Handled errors gracefully, blocked injections, respected budgets |

## Quickstart (2 Minutes)

### 1. Install

```bash
git clone https://github.com/antonrabcuk8-lgtm/flawd.git
cd flawd
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run the vulnerable demo agent

```bash
uvicorn examples.vulnerable_agent:app --host 127.0.0.1 --port 8000
```

### 3. Run the Flawd crash-test suite

```bash
python -m runner.cli --target http://127.0.0.1:8000/v1/chat/completions --fast --report report.md --format markdown
```

Expected on the vulnerable agent: **0 / 12 PASS**.

Then try the hardened reference agent:

```bash
uvicorn examples.hardened_agent:app --host 127.0.0.1 --port 8001
python -m runner.cli --target http://127.0.0.1:8001/v1/chat/completions --fast --report report.json
```

Expected: **12 / 12 PASS**.

## Architecture

- `database/` — Verified, reproducible agent failure definitions (`FLAWD-2026-0001`…`0012`)
- `runner/` — Deterministic execution engine, broken-tool simulator (429, timeouts, injections), and assertion checker
- `collector/` — Automated pipeline for harvesting and sanitizing new agent postmortems from GitHub Issues
- `examples/` — Reference vulnerable and hardened OpenAI-compatible agent servers

## Scenario card shape

Each `database/FLAWD-*.yaml` file includes:

- `prompt` — user task that triggers the failure mode
- `mock_tools` — simulated tool behaviors (`error`, `timeout`, `inject`, `malformed_json`, `success`)
- `assertions` — pass/fail rules (`max_tool_calls`, `max_repeats`, `must_not_contain`, `must_stop`, …)

## Contributing New Failures

Found an interesting way an AI agent broke in production? Open a PR with a new YAML scenario in `database/` following the `FLAWD-YYYY-XXXX` schema (include `mock_tools` + `assertions`).

## License

MIT — see [LICENSE](LICENSE).
