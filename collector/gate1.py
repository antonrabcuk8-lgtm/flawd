"""CLI: import state.db → quarantine, run Gate 1 classify + cluster.

Usage:
  python -m collector.gate1 --from-state
  python -m collector.gate1 --report
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from collector.classify import classify_text
from collector.cluster import apply_clusters
from collector.quarantine import (
    DEFAULT_PIPELINE_DB,
    funnel_counts,
    list_clusters,
    list_findings,
    log_gate,
    reject_counts,
    update_finding,
    upsert_raw,
)
from collector.rejection import FindingState
from collector.state import DEFAULT_DB as STATE_DB


def import_from_state(state_db: Path = STATE_DB) -> int:
    if not state_db.exists():
        raise FileNotFoundError(f"state.db not found: {state_db}")
    conn = sqlite3.connect(state_db)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT source, item_id, url, title, raw_body, meta_json FROM seen_items"
    ).fetchall()
    conn.close()
    n = 0
    for r in rows:
        meta = {}
        if r["meta_json"]:
            try:
                meta = json.loads(r["meta_json"])
            except json.JSONDecodeError:
                meta = {}
        upsert_raw(
            source_type=r["source"],
            source_id=str(r["item_id"]),
            url=r["url"],
            title=r["title"],
            raw_body=r["raw_body"],
            meta=meta,
        )
        n += 1
    return n


def run_gate1() -> dict:
    raws = list_findings(state=FindingState.RAW.value)
    # Also re-process any leftovers still raw only.
    stats = {"raw": len(raws), "candidate": 0, "rejected": 0}
    for r in raws:
        result = classify_text(r["title"] or "", r["raw_body"] or "")
        if result.is_agent_failure and result.category:
            update_finding(
                r["finding_pk"],
                state=FindingState.CANDIDATE.value,
                category=result.category,
                confidence=result.confidence,
                rejection_code=None,
                rejection_detail=None,
            )
            log_gate(
                r["finding_pk"],
                "G1",
                "pass",
                detail=f"{result.category} conf={result.confidence:.2f} {result.detail}",
            )
            stats["candidate"] += 1
        else:
            code = (result.rejection_code.value if result.rejection_code else "G1_TOO_VAGUE")
            update_finding(
                r["finding_pk"],
                state=FindingState.REJECTED.value,
                category=result.category,
                confidence=result.confidence,
                rejection_code=code,
                rejection_detail=result.detail,
            )
            log_gate(r["finding_pk"], "G1", "reject", code=code, detail=result.detail)
            stats["rejected"] += 1

    cluster_stats = apply_clusters()
    stats["clusters"] = cluster_stats["clusters"]
    stats["merged"] = cluster_stats["merged"]
    return stats


def print_report() -> None:
    print("=== funnel ===")
    for k, v in sorted(funnel_counts().items()):
        print(f"  {k}: {v}")
    print("=== rejects ===")
    for k, v in sorted(reject_counts().items()):
        print(f"  {k}: {v}")
    print("=== clusters (top) ===")
    for c in list_clusters()[:30]:
        print(
            f"  n={c['member_count']} [{c['category']}] {c['label'][:90]}"
        )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Flawd Gate 1 — classify + cluster")
    p.add_argument("--from-state", action="store_true", help="Import rows from state.db")
    p.add_argument("--state-db", type=Path, default=STATE_DB)
    p.add_argument("--run", action="store_true", help="Run classify+cluster on raw rows")
    p.add_argument("--report", action="store_true", help="Print funnel/cluster report")
    args = p.parse_args(argv)

    if not any([args.from_state, args.run, args.report]):
        args.from_state = True
        args.run = True
        args.report = True

    if args.from_state:
        n = import_from_state(args.state_db)
        print(f"Imported {n} rows into {DEFAULT_PIPELINE_DB.name}")

    if args.run:
        stats = run_gate1()
        print(f"Gate1: {stats}")

    if args.report:
        print_report()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
