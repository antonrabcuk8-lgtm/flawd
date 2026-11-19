"""Serialize runner results to JSON or Markdown for PRs / archives."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def build_report(
    *,
    target: str,
    rows: list[dict[str, Any]],
    passed: int,
    failed: int,
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target": target,
        "summary": {
            "total": passed + failed,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(passed / max(passed + failed, 1), 4),
        },
        "results": rows,
    }


def write_json_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# Flawd crash-test report",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Target: `{report['target']}`",
        f"- Result: **{s['passed']}/{s['total']} passed** ({s['failed']} failed)",
        "",
        "| ID | Status | Reason |",
        "|----|--------|--------|",
    ]
    for row in report["results"]:
        reason = str(row.get("reason", "")).replace("|", "\\|")
        lines.append(f"| {row['id']} | {row['status']} | {reason} |")
    lines.append("")
    return "\n".join(lines)


def write_markdown_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(report), encoding="utf-8")


def write_report(path: Path, report: dict[str, Any], *, fmt: str) -> None:
    fmt = fmt.lower().strip()
    if fmt == "json" or path.suffix.lower() == ".json":
        write_json_report(path, report)
        return
    if fmt in {"markdown", "md"} or path.suffix.lower() in {".md", ".markdown"}:
        write_markdown_report(path, report)
        return
    raise ValueError(f"unsupported report format: {fmt!r}")
