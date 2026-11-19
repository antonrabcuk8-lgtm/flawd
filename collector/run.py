"""CLI entrypoint: fetch → filter → LLM triage → YAML drafts.

Usage:
  python -m collector.run --dry-run -v
  python -m collector.run --from-db --limit 15
  python -m collector.run --source github
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

from collector.extractor import extract_and_save
from collector.github_fetcher import fetch_github
from collector.models import RawFinding
from collector.reddit_fetcher import fetch_reddit
from collector.state import count_by_source, init_db, list_by_status, save_finding

log = logging.getLogger("flawd.collector")


def _load_env() -> None:
    root = Path(__file__).resolve().parent.parent
    load_dotenv(root / ".env")


def collect(source: str) -> list[RawFinding]:
    findings: list[RawFinding] = []
    if source in ("all", "github"):
        findings.extend(fetch_github())
    if source in ("all", "reddit"):
        findings.extend(fetch_reddit())
    return findings


def _print_summary(findings: list[RawFinding]) -> None:
    by_source = Counter(f.source for f in findings)
    print("\n=== dry-run summary ===")
    print(f"total candidates: {len(findings)}")
    for src, n in sorted(by_source.items()):
        print(f"  {src}: {n}")
    if len(findings) > 100:
        print(
            "WARNING: >100 candidates — tighten Reddit MIN_UPVOTES "
            "and/or GitHub queries before paying for LLM triage."
        )
    print("=======================\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Flawd Bug Collector pipeline")
    parser.add_argument(
        "--source",
        choices=("all", "github", "reddit"),
        default="all",
        help="Which fetcher(s) to run",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max findings to triage/print (0 = no limit)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch + filter only; queue raw text in state.db; skip LLM",
    )
    parser.add_argument(
        "--from-db",
        action="store_true",
        help="Triage queued items already stored in state.db (no re-fetch)",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="With --dry-run: print only, do not write state.db",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Debug logging",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    _load_env()
    init_db()

    if args.from_db:
        findings = list_by_status("queued", limit=args.limit or 0)
        log.info("Loaded %s queued findings from state.db", len(findings))
    else:
        findings = collect(args.source)
        if args.limit and args.limit > 0 and not args.dry_run:
            findings = findings[: args.limit]

    log.info("Collected %s new findings after filters", len(findings))

    if args.dry_run:
        to_show = findings[: args.limit] if args.limit and args.limit > 0 else findings
        _print_summary(findings)
        for f in to_show:
            ups = f.meta.get("ups") or f.meta.get("comments")
            extra = f" ups/comments={ups}" if ups is not None else ""
            print(f"[{f.source}]{extra} {f.title}\n  {f.url}\n")
            if not args.no_persist:
                save_finding(f, status="queued")
        if not args.no_persist:
            log.info("Queued %s findings (with raw_body) in state.db", len(findings))
            log.info("DB counts by source: %s", count_by_source())
        return 0

    if not findings:
        log.info("Nothing new to triage.")
        return 0

    if not (os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY")):
        log.error(
            "Set OPENAI_API_KEY or GEMINI_API_KEY (and FLAWD_LLM_PROVIDER) before triage."
        )
        return 1

    # Ensure raw bodies are on disk before spending tokens.
    for f in findings:
        save_finding(f, status="queued")

    paths = extract_and_save(findings)
    log.info("Wrote %s drafts → drafts/", len(paths))
    for p in paths:
        print(p.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
