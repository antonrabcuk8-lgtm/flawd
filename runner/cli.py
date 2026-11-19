"""CLI: python -m runner.cli --target http://localhost:8000/v1/chat/completions"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from runner.engine import ScenarioEngine
from runner.loader import DEFAULT_DATABASE, load_database
from runner.report import build_report, render_markdown, write_report


def _fmt_reason(trace) -> str:
    if trace.error:
        return f"engine error: {trace.error}"
    fails = [r for r in trace.assertion_results if not r.passed]
    if not fails:
        return "all assertions passed"
    parts = [f"{r.assertion.type.value}: {r.detail}" for r in fails]
    return "; ".join(parts)


def _print_table(rows: list[tuple[str, str, str]]) -> None:
    id_w = max(len("ID"), max(len(r[0]) for r in rows))
    st_w = max(len("STATUS"), max(len(r[1]) for r in rows))
    print()
    print(f"{'ID'.ljust(id_w)}  {'STATUS'.ljust(st_w)}  REASON")
    print(f"{'-' * id_w}  {'-' * st_w}  {'-' * 40}")
    for sid, status, reason in rows:
        print(f"{sid.ljust(id_w)}  {status.ljust(st_w)}  {reason}")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Flawd scenario runner")
    parser.add_argument(
        "--target",
        required=True,
        help="OpenAI-compatible chat completions URL "
        "(e.g. http://localhost:8000/v1/chat/completions)",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
        help="Path to database/ YAML directory",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        default=[],
        help="Limit to scenario id (repeatable)",
    )
    parser.add_argument("--max-turns", type=int, default=12)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--model", default="flawd-target")
    parser.add_argument("--api-key", default=None, help="Optional Bearer token for target")
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Cap mock tool delays at 200ms (faster local smoke runs)",
    )
    parser.add_argument(
        "--include-drafts",
        action="store_true",
        help="Also load non-verified scenarios",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Write results to a file (e.g. report.json or report.md)",
    )
    parser.add_argument(
        "--format",
        choices=("table", "json", "markdown", "md"),
        default="table",
        help="Console format; also selects file format if --report has no known suffix",
    )
    args = parser.parse_args(argv)

    scenarios = load_database(
        args.database,
        only_verified=not args.include_drafts,
        scenario_ids=args.scenario or None,
    )
    if not scenarios:
        print("No scenarios loaded.", file=sys.stderr)
        return 2

    engine = ScenarioEngine(
        args.target,
        timeout_sec=args.timeout,
        max_turns=args.max_turns,
        model=args.model,
        api_key=args.api_key,
        max_tool_delay_ms=200 if args.fast else None,
    )

    table_rows: list[tuple[str, str, str]] = []
    report_rows: list[dict] = []
    failures = 0
    for scenario in scenarios:
        print(f"→ running {scenario.id}: {scenario.title}")
        trace = engine.run(scenario)
        status = "PASS" if trace.passed else "FAIL"
        reason = _fmt_reason(trace)
        if not trace.passed:
            failures += 1
        table_rows.append((scenario.id, status, reason))
        report_rows.append(
            {
                "id": scenario.id,
                "title": scenario.title,
                "status": status,
                "reason": reason,
                "turns": trace.turns,
                "duration_sec": round(trace.duration_sec, 3),
                "total_tokens": trace.total_tokens,
                "tool_calls": [
                    {"name": r.name, "status": r.status, "behavior": r.behavior.value}
                    for r in trace.mocks.history
                ],
                "assertions": [
                    {
                        "type": r.assertion.type.value,
                        "passed": r.passed,
                        "detail": r.detail,
                    }
                    for r in trace.assertion_results
                ],
            }
        )

    passed = len(table_rows) - failures
    report = build_report(
        target=args.target,
        rows=report_rows,
        passed=passed,
        failed=failures,
    )

    fmt = args.format
    if fmt == "table":
        _print_table(table_rows)
    elif fmt in {"markdown", "md"}:
        print(render_markdown(report))
    elif fmt == "json":
        import json

        print(json.dumps(report, indent=2, ensure_ascii=False))

    print(f"Summary: {passed}/{len(table_rows)} passed, {failures} failed")

    if args.report:
        # Infer format from extension when --format is still the default table.
        out_fmt = fmt
        if fmt == "table":
            suf = args.report.suffix.lower()
            if suf == ".json":
                out_fmt = "json"
            elif suf in {".md", ".markdown"}:
                out_fmt = "markdown"
            else:
                out_fmt = "json"
        write_report(args.report, report, fmt=out_fmt)
        print(f"Wrote report → {args.report}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
