"""Reddit public JSON feed fetcher (no API key required)."""

from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import quote_plus

import requests

from collector.models import RawFinding
from collector.state import is_seen

log = logging.getLogger(__name__)

# Unique UA — Reddit blocks generic library agents and hammers 429s hard.
USER_AGENT = "FlawdCollector/0.1 (research-bot)"
# www.reddit.com often returns 403 to bare scripts; old.reddit.com is friendlier.
REDDIT_BASE = "https://old.reddit.com"
SUBREDDITS = ["LocalLLaMA", "LangChain", "AutoGPT", "AI_Agents"]

# Pause between HTTP calls (queries) and between subreddits.
REQUEST_PAUSE_SEC = 2.5
SUBREDDIT_PAUSE_SEC = 3.0
MIN_UPVOTES = 10  # raised after first dry-run volume guidance

DISASTER_MARKERS = (
    "loop",
    "bill",
    "burned",
    "hallucinated",
    "hallucination",
    "stuck",
    "injection",
    "prompt injection",
    "infinite",
    "cost",
    " runaway",
    "broke",
    "crash",
    "timeout",
    "tool call",
    "wrong tool",
)

SEARCH_QUERIES = [
    "agent loop OR stuck OR hallucinated",
    "burned tokens OR bill OR cost",
    "prompt injection OR tool call failed",
]


def _headers() -> dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


def _text_blob(post: dict[str, Any]) -> str:
    data = post.get("data") or post
    title = data.get("title") or ""
    selftext = data.get("selftext") or ""
    return f"{title}\n{selftext}".lower()


def _passes_signal_filter(post: dict[str, Any]) -> bool:
    data = post.get("data") or post
    ups = int(data.get("ups") or data.get("score") or 0)
    if ups < MIN_UPVOTES:
        return False
    blob = _text_blob(post)
    return any(marker in blob for marker in DISASTER_MARKERS)


def _fetch_json(url: str, session: requests.Session, *, retries: int = 3) -> dict[str, Any]:
    last_exc: Exception | None = None
    for attempt in range(retries):
        resp = session.get(url, headers=_headers(), timeout=30)
        if resp.status_code == 429:
            wait = float(resp.headers.get("Retry-After") or (5 * (attempt + 1)))
            log.warning("Reddit 429 — sleeping %.1ss (attempt %s/%s)", wait, attempt + 1, retries)
            time.sleep(wait)
            last_exc = requests.HTTPError(f"429 for {url}", response=resp)
            continue
        if resp.status_code == 403:
            # Edge bot-wall (common on datacenter / some residential IPs).
            raise requests.HTTPError(
                f"403 Blocked for {url} — Reddit JSON feeds unavailable from this network",
                response=resp,
            )
        resp.raise_for_status()
        return resp.json()
    assert last_exc is not None
    raise last_exc


def search_subreddit(
    subreddit: str,
    query: str,
    *,
    limit: int = 25,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    sess = session or requests.Session()
    q = quote_plus(query)
    url = (
        f"{REDDIT_BASE}/r/{subreddit}/search.json"
        f"?q={q}&restrict_sr=1&sort=new&t=month&limit={limit}"
    )
    payload = _fetch_json(url, sess)
    return (payload.get("data") or {}).get("children") or []


def fetch_new(
    subreddit: str,
    *,
    limit: int = 40,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    sess = session or requests.Session()
    url = f"{REDDIT_BASE}/r/{subreddit}/new.json?limit={limit}"
    payload = _fetch_json(url, sess)
    return (payload.get("data") or {}).get("children") or []


def _to_finding(post: dict[str, Any]) -> RawFinding | None:
    data = post.get("data") or {}
    item_id = str(data.get("id") or "")
    if not item_id:
        return None

    title = (data.get("title") or "").strip()
    body = (data.get("selftext") or "").strip()
    permalink = data.get("permalink") or ""
    url = f"https://www.reddit.com{permalink}" if permalink else (data.get("url") or "")

    return RawFinding(
        source="reddit",
        item_id=item_id,
        url=url,
        title=title,
        body=body[:8000],
        meta={
            "subreddit": data.get("subreddit"),
            "ups": data.get("ups") or data.get("score"),
            "num_comments": data.get("num_comments"),
            "created_utc": data.get("created_utc"),
            "flair": data.get("link_flair_text"),
        },
    )


def fetch_reddit(
    subreddits: list[str] | None = None,
    *,
    skip_seen: bool = True,
    include_new: bool = True,
) -> list[RawFinding]:
    subreddits = subreddits or SUBREDDITS
    findings: list[RawFinding] = []
    seen_ids: set[str] = set()

    with requests.Session() as sess:
        for idx, sub in enumerate(subreddits):
            if idx > 0:
                time.sleep(SUBREDDIT_PAUSE_SEC)

            posts: list[dict[str, Any]] = []

            if include_new:
                try:
                    posts.extend(fetch_new(sub, session=sess))
                except (requests.HTTPError, requests.RequestException) as exc:
                    log.error("Reddit new-feed failed for r/%s: %s", sub, exc)
                time.sleep(REQUEST_PAUSE_SEC)

            for query in SEARCH_QUERIES:
                try:
                    posts.extend(search_subreddit(sub, query, session=sess))
                except (requests.HTTPError, requests.RequestException) as exc:
                    log.error("Reddit search failed for r/%s (%s): %s", sub, query, exc)
                time.sleep(REQUEST_PAUSE_SEC)

            for post in posts:
                data = post.get("data") or {}
                item_id = str(data.get("id") or "")
                if not item_id or item_id in seen_ids:
                    continue
                seen_ids.add(item_id)

                if not _passes_signal_filter(post):
                    continue
                if skip_seen and is_seen("reddit", item_id):
                    continue

                finding = _to_finding(post)
                if finding and (finding.title or finding.body):
                    findings.append(finding)

    log.info("Reddit: %s new signal findings", len(findings))
    return findings


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for f in fetch_reddit()[:5]:
        print(f"[{f.source}/{f.meta.get('subreddit')}] {f.title}\n  {f.url}\n")
