# Flawd launch posts (28/28 + web catalog)

Use after GitHub Pages is live: https://antonrabcuk8-lgtm.github.io/flawd/

---

## Hacker News — Show HN

**Title:** Show HN: Flawd – crash-test suite for AI agents that charge twice

**Body:**

```text
Flawd is an open catalog of AI-agent failures (CVE-style IDs) plus a local runner
for OpenAI-compatible tool-calling agents.

We just hit 28/28 verified scenarios with differential proof:
- vulnerable reference agent: 0/28
- hardened reference agent: 28/28

Strong focus on financial footguns:
- re-charging after a downstream email failure
- collapsing two intentional invoices into one charge
- blind re-fire after a timeout instead of reconciling provider status

Install:
  pip install flawd
  flawd --target http://localhost:8000/v1/chat/completions --fast

Catalog + site: https://antonrabcuk8-lgtm.github.io/flawd/
Repo: https://github.com/antonrabcuk8-lgtm/flawd
```

---

## Reddit — r/LocalLLaMA / r/AI_Agents

**Title:** Flawd 0.2 — 28 crash-tests for tool-calling agents (double charges, retry loops, injection)

**Body:**

```text
Built Flawd as a “CVE catalog + crash-test runner” for agents that speak OpenAI
chat completions + tool_calls.

What’s new:
- 28 verified cards (idempotency / loops / injection / tool-policy / timeouts)
- pip install flawd (no clone required)
- interactive web catalog with filters
- differential CI: 0/28 vulnerable vs 28/28 hardened

Why this matters for anyone shipping payment tools:
agents love to retry. Retrying charge_card after a timeout or a failed receipt
email is how you double-bill a customer.

Try it:
pip install flawd
flawd --target http://YOUR_AGENT/v1/chat/completions --fast

Site: https://antonrabcuk8-lgtm.github.io/flawd/
GitHub: https://github.com/antonrabcuk8-lgtm/flawd

Feedback welcome — especially missing failure modes you’ve seen in prod.
```

---

## LinkedIn

```text
Shipping an AI agent that can call charge_card?
The expensive bugs are rarely “the model is dumb” — they’re retry + idempotency.

Flawd is an open failure catalog + crash-test runner for tool-calling agents.

Today:
• 28 verified scenarios
• 0/28 on an unprotected agent · 28/28 on a hardened one
• pip install flawd
• public catalog: https://antonrabcuk8-lgtm.github.io/flawd/

Highlighted financial cases:
• double charge after email failure
• false-positive idempotency collapsing two real invoices
• lost provider response → blind re-fire

If you want us to run the suite against your staging endpoint (no local setup),
there’s a Cloud Runner request on the site — testing demand before billing infra.

Repo: https://github.com/antonrabcuk8-lgtm/flawd
```
