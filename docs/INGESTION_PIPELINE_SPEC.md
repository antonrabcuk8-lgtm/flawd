# Flawd Ingestion Pipeline — Technical Spec (TZ)

Status: **spec for implementation** (not yet built)  
Goal: every catalog entry passes hard gates; everything else stays in quarantine with a rejection code.

This document is the single source of truth for Cursor when implementing the quality pipeline after the current collector + runner MVP.

---

## 1. Principles

1. **States are linear forward, rejections are typed.**  
   `raw → candidate → draft → validated → published`  
   From any gate, failure goes to `rejected` **with a rejection code** (never a silent drop).
2. **Quarantine is valuable.** Rejected rows teach filter improvement; measure why they failed.
3. **Honest trust levels in the public catalog.** Users must see `verified` / `auto-verified` / `synthetic` / `stale`.
4. **Legal hygiene.** Store **links + our own paraphrase only** — never verbatim third-party issue bodies in `database/`. Raw text may live only in local/private quarantine DB under retention limits. Respect API rate limits and source ToS.
5. **Gate 4 defines “works”.** A card is not publishable until vulnerable FAIL + hardened PASS (+ stability), unless routed to human review.

---

## 2. Lifecycle states

| State | Meaning | Where it lives |
|-------|---------|----------------|
| `raw` | Fetched finding (GitHub issue / other source), not classified | quarantine DB |
| `candidate` | Passed Gate 1 (agent failure + dedup cluster) | quarantine DB |
| `draft` | Passed Gate 2–3 (expressible + schema-valid YAML) | `drafts/` + quarantine DB |
| `validated` | Passed Gate 4 differential tests (and optional human) | quarantine DB / staging |
| `published` | In public catalog | `database/FLAWD-*.yaml` |
| `rejected` | Failed a gate | quarantine DB (immutable history of reasons) |
| `stale` | Was published; periodic recheck failed or source obsolete | `database/` flagged or moved |

### Public trust labels (published cards)

| Label | Criteria |
|-------|----------|
| `verified` | Gate 4 passed **and** human approved (Gate 5) |
| `auto-verified` | Gate 4 passed, no human yet |
| `synthetic` | Not from a single public postmortem; combat card constructed/adapted |
| `stale` | Published earlier; freshness recheck failed |

Map onto YAML field `status` (extend current `draft` / `verified`):

```text
draft | auto-verified | verified | synthetic | stale | rejected
```

`provenance` stays separate: `github-inspired | synthetic`.

---

## 3. Rejection codes

Every transition to `rejected` **must** set `rejection_code` + short `rejection_detail`.

| Code | Gate | Meaning |
|------|------|---------|
| `G1_NOT_AGENT_FAILURE` | 1 | User error / feature request / question / unrelated bug |
| `G1_TOO_VAGUE` | 1 | No concrete effect (loop, duplicate, leak, bad format, etc.) |
| `G1_DUPLICATE_MERGED` | 1 | Not a hard reject — cluster member merged into parent (status `merged`) |
| `G2_OUT_OF_SCOPE` | 2 | Needs framework internals / UI / network topology Flawd cannot mock |
| `G2_UNSUPPORTED_PRIMITIVE` | 2 | Cannot express with current mock/assertion vocabulary |
| `G3_SCHEMA_INVALID` | 3 | YAML/JSON missing required fields or fails schema |
| `G3_GENERATION_FAILED` | 3 | LLM draft unusable after N retries |
| `G4_VULN_DID_NOT_FAIL` | 4 | Vulnerable reference did not FAIL |
| `G4_HARDENED_DID_NOT_PASS` | 4 | Hardened reference did not PASS |
| `G4_FLAKY` | 4 | Results unstable across 3 runs |
| `G4_CONTROL_FALSE_POSITIVE` | 4 | Benign control case incorrectly failed |
| `G4_NEEDS_HUMAN` | 4 | Ambiguous (wrong reason / missing specialized guard) → review queue, not auto-reject |
| `G5_HUMAN_REJECT` | 5 | Human rejected |
| `G6_STALE` | 6 | Freshness recheck failed |

Use status `merged` for cluster members (not `rejected`) so metrics can separate “deduped” from “trash”.

---

## 4. Gates (pass criteria)

### Gate 1 — Is this an agent failure? (+ dedup)

**Input:** `raw`  
**Output:** `candidate` or `rejected` / `merged`

**Classifier (cheap LLM or rules+LLM):**

- Positive classes (examples): tool loop, duplicate side-effect, prompt injection via tool result, malformed tool payload trust, rate-limit retry storm, missing required tool call, policy bypass.
- Negative classes: user misconfig, feature request, docs typo, pure infrastructure unrelated to agent loop.

**Dedup / clustering:**

- Embed title+paraphrase (or LLM cluster id).
- Ten issues of the same pattern → **one** scenario card with:

```yaml
source:
  type: github
  url: https://github.com/.../issues/5802   # primary
  note: "..."
sources:   # NEW optional field
  - type: github
    url: https://github.com/.../issues/AAAA
  - type: github
    url: https://github.com/.../issues/BBBB
```

**Pass:** classified as agent failure with confidence ≥ threshold AND attached to a cluster.  
**Fail:** `G1_*` codes.

---

### Gate 2 — Expressible in Flawd runner?

**Input:** `candidate`  
**Output:** `candidate` tagged expressible → proceed, or `rejected` with `G2_*`

**Ask:**

1. Can the failure be induced via client-visible OpenAI `tool_calls` + mock behaviors?
2. Allowed mock behaviors today: `success | error | timeout | malformed_json | inject`
3. Allowed assertions today: `min_tool_calls | max_tool_calls | max_repeats | max_tokens | max_duration_sec | must_not_contain | must_stop`

**Out of scope examples:** private CrewAI retry engine internals, browser pixel UI only, multi-host network partitions not mockable as tool results.

**Pass:** expressible with current primitives (or explicitly queued as `needs_runner_extension` — optional future status, not published).  
**Fail:** `G2_OUT_OF_SCOPE` / `G2_UNSUPPORTED_PRIMITIVE`.

Expect high attrition here; measure it.

---

### Gate 3 — Draft generation + hard schema

**Input:** expressible `candidate`  
**Output:** `draft` YAML or `rejected` (`G3_*`)

**Pipeline:**

1. LLM generates card (paraphrase only; strip PII/secrets — existing extractor rules).
2. Validate against **JSON Schema** / Pydantic (`runner.loader.Scenario` extended).
3. Required fields (hard fail if missing):

| Field | Notes |
|-------|-------|
| `id` | `FLAWD-YYYY-XXXX` allocated by counter |
| `title`, `summary`, `failure_mechanism` | paraphrase |
| `prompt` | user prompt for runner |
| `mock_tools` | ≥1 |
| `assertions` | ≥1; prefer min+max when “exactly N” |
| `source` | `type`, `url` (for github-inspired), `note`, `accessed` |
| `category`, `severity`, `provenance`, `mitigation` | required |
| `status` | start as `draft` |

4. Write `drafts/{id}.yaml` and quarantine row `status=draft`.

**Pass:** schema-valid draft on disk.  
**Fail:** `G3_SCHEMA_INVALID` / `G3_GENERATION_FAILED`.

---

### Gate 4 — Differential test (core)

**Input:** `draft`  
**Output:** `validated` / `rejected` / review queue (`G4_NEEDS_HUMAN`)

**Procedure:**

| Step | Target | Expected |
|------|--------|----------|
| A | `examples/vulnerable_agent.py` (or suite profile) | **FAIL** (scenario assertions fail) |
| B | `examples/hardened_agent.py` with relevant guards | **PASS** |
| C | Repeat A and B **3 times** | identical pass/fail each time |
| D | Control case (benign prompt / success-only tools variant) | must **not** spuriously FAIL hardened |

**CLI sketch (to implement):**

```bash
python -m runner.validate_card \
  --scenario drafts/FLAWD-2026-00XX.yaml \
  --vulnerable http://127.0.0.1:8000/v1/chat/completions \
  --hardened http://127.0.0.1:8001/v1/chat/completions \
  --runs 3 \
  --control
```

**Nuance — wrong-reason PASS/FAIL:**  
If hardened passes/fails for a reason unrelated to the card’s mitigation (generic max-turns, etc.), do **not** auto-reject → `G4_NEEDS_HUMAN` review queue.

**Pass:** A fail, B pass, C stable, D clean (or human override later).  
**Fail:** `G4_VULN_DID_NOT_FAIL`, `G4_HARDENED_DID_NOT_PASS`, `G4_FLAKY`, `G4_CONTROL_FALSE_POSITIVE`.

---

### Gate 5 — Human sampling

**Input:** `validated` (auto)  
**Output:** `published` with `verified` or stays `auto-verified`

| Phase | Policy |
|-------|--------|
| First ~50 published | human reviews **100%** |
| After that | review random **10–20%** + all low-confidence / `G4_NEEDS_HUMAN` |

**Metric:** of auto-approved sample, what % would human reject? If rising → tighten Gates 1–4.

---

### Gate 6 — Publish + freshness

**Publish:** move/copy YAML to `database/`, update `database/README.md` catalog row, set trust label.

**Freshness job (cron / Actions):**

1. Re-run Gate 4 on published cards periodically.
2. Optionally HEAD/check primary `source.url` (issue closed ≠ auto-stale, but note it).
3. If differential behavior breaks → mark `stale` + open issue.

Without Gate 6 the catalog silently rots.

---

## 5. Modules to implement

```text
flawd/
├── collector/                 # existing fetch + raw store
│   ├── github_fetcher.py
│   ├── classify.py            # NEW Gate 1
│   ├── cluster.py             # NEW dedup / merge sources[]
│   ├── expressibility.py      # NEW Gate 2
│   ├── extractor.py           # Gate 3 (extend schema)
│   └── promote.py             # NEW draft→validate→publish orchestration
├── runner/
│   ├── validate_card.py       # NEW Gate 4 CLI
│   ├── loader.py              # schema source of truth
│   └── ...
├── drafts/                    # Gate 3 outputs
├── database/                  # published only
├── quarantine/                # optional export of rejected summaries (no raw copyrighted bodies)
└── docs/INGESTION_PIPELINE_SPEC.md
```

Suggested CLI entrypoints:

```bash
python -m collector.run --dry-run                 # raw intake (exists)
python -m collector.classify --limit 50           # Gate 1
python -m collector.promote --from candidate      # Gates 2–3
python -m runner.validate_card --scenario ...     # Gate 4
python -m collector.publish --id FLAWD-...        # Gate 5/6 helper
python -m collector.freshness --all               # Gate 6
```

---

## 6. Quarantine database schema

Extend beyond today’s `seen_items` (or replace with `pipeline.db`):

### `findings`

| Column | Type | Notes |
|--------|------|-------|
| finding_pk | TEXT PK | `github:{id}` |
| source_type | TEXT | github / reddit / … |
| source_id | TEXT | |
| url | TEXT | |
| title | TEXT | |
| raw_body | TEXT | local only; not published |
| cluster_id | TEXT NULL | Gate 1 |
| state | TEXT | raw/candidate/draft/validated/published/rejected/merged |
| rejection_code | TEXT NULL | |
| rejection_detail | TEXT NULL | |
| confidence | REAL NULL | classifier |
| draft_id | TEXT NULL | FLAWD-… |
| created_at / updated_at | TEXT | ISO-8601 |

### `clusters`

| Column | Type | Notes |
|--------|------|-------|
| cluster_id | TEXT PK | |
| pattern_key | TEXT | normalized pattern |
| primary_finding_pk | TEXT | |
| member_count | INT | |
| label | TEXT | short pattern name |

### `gate_runs`

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| draft_id | TEXT | |
| gate | TEXT | G4 / G6 |
| target | TEXT | vulnerable / hardened / control |
| run_index | INT | 1..3 |
| passed | INT | 0/1 |
| detail_json | TEXT | assertion results |
| created_at | TEXT | |

### `metrics_daily` (optional rollup)

| Column | Notes |
|--------|-------|
| day | |
| raw_in / candidate_out / draft_out / validated_out / published_out | funnel |
| reject_counts_json | by `rejection_code` |
| human_sample_reject_rate | Gate 5 |
| median_hours_raw_to_published | |

---

## 7. YAML schema (published card)

Aligned with current `runner.loader.Scenario`, plus pipeline fields:

```yaml
id: FLAWD-2026-0001
status: verified          # draft | auto-verified | verified | synthetic | stale
provenance: github-inspired
category: idempotency
severity: critical
mitigation: "..."
title: "..."
summary: "..."            # our paraphrase only
failure_mechanism: "..."
prompt: "..."
reproduction_hints: []
mock_tools:
  - name: charge_card
    behavior: success     # success|error|timeout|malformed_json|inject
    status: 200
    delay_ms: 0
    body: '{"ok": true}'
assertions:
  - type: min_tool_calls
    tool: charge_card
    min: 1
  - type: max_tool_calls
    tool: charge_card
    max: 1
  - type: must_stop
source:
  type: github
  url: https://github.com/org/repo/issues/123
  accessed: "2026-11-19"
  note: "Inspired by ...; Flawd tests ..."
sources: []               # optional extras from cluster
tags: []
notes: null
validation:
  vulnerable_fail: true
  hardened_pass: true
  runs: 3
  last_validated_at: "2026-11-19T12:00:00Z"
```

JSON Schema artifact to add: `schemas/flawd_scenario.schema.json` (generated from Pydantic or hand-maintained; Gate 3 loads it).

---

## 8. Reference agents (Gate 4 dependency)

Gate 4 is only as strong as the reference agents.

| Agent | Role |
|-------|------|
| `examples/vulnerable_agent.py` | Intentionally fails suite (no guards) |
| `examples/hardened_agent.py` | Generalized guards; may need **per-category plugins** so new categories don’t pass/fail for the wrong reason |

**Follow-up work (explicit):**

1. Pluggable guard modules (idempotency, injection filter, retry budget, tool denylist, JSON validate).
2. Per-scenario `required_guards: [idempotency]` — if hardened lacks guard → `G4_NEEDS_HUMAN` / skip auto-verify.
3. Control-case generator (success-only tools, benign prompt).

Do not inflate `verified` until this is solid.

---

## 9. Metrics to measure from day one

| Metric | Definition |
|--------|------------|
| Precision@published | Among human-sampled published cards, % human would keep |
| Funnel conversion | raw→candidate→draft→validated→published rates |
| Reject mix | histogram of `rejection_code` |
| Dedup ratio | merged / raw |
| Time-to-publish | hours from `raw.created_at` to `published` |
| Flake rate | share of drafts hitting `G4_FLAKY` |
| Stale rate | share of catalog marked `stale` per month |

Dashboard: start with SQL queries + a Markdown report from `python -m collector.metrics`.

---

## 10. Implementation phases (suggested)

| Phase | Deliverable |
|-------|-------------|
| **P0** | This spec + JSON Schema file + `rejection_code` enum in code |
| **P1** | Quarantine schema migration; Gate 1 classify + cluster |
| **P2** | Gate 2 expressibility checker; Gate 3 schema enforcement on extractor |
| **P3** | `runner.validate_card` (Gate 4) + CI job on new drafts |
| **P4** | Human review queue + publish helper; trust labels in README/catalog |
| **P5** | Freshness cron (Gate 6) + metrics report |

---

## 11. Non-goals (for this pipeline)

- Claiming official CVE assignment
- Scraping and republishing full upstream issue text
- Supporting agents that never emit client-side `tool_calls` (document as protocol limitation)
- Auto-publishing without Gate 4

---

## 12. Acceptance test for the pipeline itself

The pipeline is “done” for v1 when:

1. A known-good card like `FLAWD-2026-0001` goes `draft → validated → published` with Gate 4 green.
2. A feature-request issue is rejected with `G1_NOT_AGENT_FAILURE`.
3. A framework-internal-only bug is rejected with `G2_OUT_OF_SCOPE`.
4. A schema-broken draft never lands in `database/`.
5. Funnel metrics for one batch (≥50 raw) are printable in one command.

---

## 13. Open questions (resolve during P1)

1. Confidence threshold for Gate 1 auto-pass?
2. Single hardened binary vs multiple hardened profiles per category?
3. Retention period for `raw_body` in quarantine?
4. Should `auto-verified` appear in the public README table or only `verified`?

---

*End of TZ. Implement gate-by-gate; do not skip Gate 4 to inflate catalog size.*
