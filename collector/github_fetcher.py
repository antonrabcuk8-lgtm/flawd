"""GitHub Search API fetcher for agent-framework bug issues."""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any

import requests

from collector.models import RawFinding
from collector.state import is_seen

log = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
USER_AGENT = "Flawd-BugCollector/0.1 (+research; contact: local)"

# Curated agent-framework repos only (no broad cross-repo sweep).
DEFAULT_QUERIES = [
    'repo:langchain-ai/langchain is:issue label:bug state:open comments:>2',
    'repo:Significant-Gravitas/AutoGPT is:issue label:bug state:open comments:>3',
    'repo:microsoft/autogen is:issue label:bug state:open comments:>2',
    'repo:crewAIInc/crewAI is:issue label:bug state:open comments:>2',
    'repo:pydantic/pydantic-ai is:issue label:bug state:open comments:>2',
    'repo:openai/openai-agents-python is:issue label:bug state:open comments:>1',
    'repo:browser-use/browser-use is:issue label:bug state:open comments:>3',
]

MIN_COMMENTS_WITHOUT_BUG_LABEL = 8

# Strong failure vocabulary — short tokens use word boundaries so
# "user-agent" / "installer" / "catalog" do not false-positive.
_STRONG_PHRASES = (
    "tool call",
    "tool-call",
    "tool calling",
    "function call",
    "prompt injection",
    "infinite loop",
    "stuck in a loop",
    "agent loop",
    "wrong tool",
    "re-invok",
    "multi-agent",
    "hallucin",
)
_STRONG_WORDS = re.compile(
    r"\b(agent|loop|stuck|planner|orchestrat\w*|autonomous|crew)\b",
    re.IGNORECASE,
)
_NOISE_TITLE = re.compile(
    r"\b(docs?|cve|vulnerabilit|dependency|dependencies|typo|readme|install)\b",
    re.IGNORECASE,
)


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _has_agent_failure_signal(title: str, body: str) -> bool:
    blob = f"{title}\n{body}".lower()
    if any(p in blob for p in _STRONG_PHRASES):
        return True
    return bool(_STRONG_WORDS.search(blob))


def _passes_signal_filter(issue: dict[str, Any]) -> bool:
    """Keep concrete agent-failure bugs; drop generic framework noise."""
    labels = {str(lbl.get("name", "")).lower() for lbl in issue.get("labels", [])}
    has_bug = (
        "bug" in labels
        or "bugfix" in labels
        or "type: bug" in labels
        or any("bug" in name for name in labels)
    )
    comments = int(issue.get("comments") or 0)
    if not has_bug and comments < MIN_COMMENTS_WITHOUT_BUG_LABEL:
        return False

    title = issue.get("title") or ""
    body = issue.get("body") or ""
    if _NOISE_TITLE.search(title) and comments < 10:
        return False
    return _has_agent_failure_signal(title, body)


def search_issues(
    query: str,
    *,
    per_page: int = 30,
    max_pages: int = 1,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    sess = session or requests.Session()
    results: list[dict[str, Any]] = []

    for page in range(1, max_pages + 1):
        resp = sess.get(
            f"{GITHUB_API}/search/issues",
            headers=_headers(),
            params={
                "q": query,
                "sort": "updated",
                "order": "desc",
                "per_page": per_page,
                "page": page,
            },
            timeout=30,
        )
        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            reset = int(resp.headers.get("X-RateLimit-Reset", "0") or 0)
            wait = max(reset - int(time.time()), 5)
            log.warning("GitHub rate limit hit; sleeping %ss", wait)
            time.sleep(wait)
            resp = sess.get(
                f"{GITHUB_API}/search/issues",
                headers=_headers(),
                params={
                    "q": query,
                    "sort": "updated",
                    "order": "desc",
                    "per_page": per_page,
                    "page": page,
                },
                timeout=30,
            )

        resp.raise_for_status()
        payload = resp.json()
        items = payload.get("items") or []
        results.extend(items)
        if len(items) < per_page:
            break
        # Stay under ~30 search req/min on free tier.
        time.sleep(2.1)

    return results


def fetch_github(
    queries: list[str] | None = None,
    *,
    skip_seen: bool = True,
) -> list[RawFinding]:
    queries = queries or DEFAULT_QUERIES
    findings: list[RawFinding] = []
    seen_ids: set[str] = set()

    with requests.Session() as sess:
        for query in queries:
            log.info("GitHub search: %s", query)
            try:
                issues = search_issues(query, session=sess)
            except requests.HTTPError as exc:
                log.error("GitHub search failed for %r: %s", query, exc)
                continue

            for issue in issues:
                if "pull_request" in issue:
                    continue
                if not _passes_signal_filter(issue):
                    continue

                item_id = str(issue["id"])
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)

                if skip_seen and is_seen("github", item_id):
                    continue

                body = (issue.get("body") or "").strip()
                title = (issue.get("title") or "").strip()
                if not title and not body:
                    continue

                labels = [lbl.get("name") for lbl in issue.get("labels", [])]
                findings.append(
                    RawFinding(
                        source="github",
                        item_id=item_id,
                        url=issue.get("html_url") or "",
                        title=title,
                        body=body[:8000],
                        meta={
                            "repo": (issue.get("repository_url") or "").rsplit("/", 2)[-2:],
                            "comments": issue.get("comments"),
                            "labels": labels,
                            "updated_at": issue.get("updated_at"),
                            "query": query,
                        },
                    )
                )

    log.info("GitHub: %s new signal findings", len(findings))
    return findings


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for f in fetch_github()[:5]:
        print(f"[{f.source}] {f.title}\n  {f.url}\n")
