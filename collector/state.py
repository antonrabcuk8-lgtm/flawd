"""SQLite store: dedup IDs + raw post text for re-triage without re-fetch."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from collector.models import RawFinding

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "state.db"


def _connect(db_path: Path = DEFAULT_DB) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_columns(conn: sqlite3.Connection) -> None:
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(seen_items)")}
    for name, ddl in (
        ("raw_body", "TEXT"),
        ("meta_json", "TEXT"),
    ):
        if name not in cols:
            conn.execute(f"ALTER TABLE seen_items ADD COLUMN {name} {ddl}")


def init_db(db_path: Path = DEFAULT_DB) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_items (
                source    TEXT NOT NULL,
                item_id   TEXT NOT NULL,
                url       TEXT,
                title     TEXT,
                raw_body  TEXT,
                meta_json TEXT,
                status    TEXT NOT NULL DEFAULT 'seen',
                score     INTEGER,
                draft_id  TEXT,
                seen_at   TEXT NOT NULL,
                PRIMARY KEY (source, item_id)
            )
            """
        )
        _ensure_columns(conn)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS draft_counter (
                year  INTEGER PRIMARY KEY,
                last  INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.commit()


@contextmanager
def db_session(db_path: Path = DEFAULT_DB) -> Iterator[sqlite3.Connection]:
    init_db(db_path)
    conn = _connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def is_seen(source: str, item_id: str, db_path: Path = DEFAULT_DB) -> bool:
    with db_session(db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM seen_items WHERE source = ? AND item_id = ?",
            (source, item_id),
        ).fetchone()
        return row is not None


def mark_seen(
    source: str,
    item_id: str,
    *,
    url: str | None = None,
    title: str | None = None,
    raw_body: str | None = None,
    meta: dict[str, Any] | None = None,
    status: str = "seen",
    score: int | None = None,
    draft_id: str | None = None,
    db_path: Path = DEFAULT_DB,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    meta_json = json.dumps(meta, ensure_ascii=False) if meta is not None else None
    with db_session(db_path) as conn:
        conn.execute(
            """
            INSERT INTO seen_items (
                source, item_id, url, title, raw_body, meta_json,
                status, score, draft_id, seen_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, item_id) DO UPDATE SET
                status = excluded.status,
                score = COALESCE(excluded.score, seen_items.score),
                draft_id = COALESCE(excluded.draft_id, seen_items.draft_id),
                url = COALESCE(excluded.url, seen_items.url),
                title = COALESCE(excluded.title, seen_items.title),
                raw_body = COALESCE(excluded.raw_body, seen_items.raw_body),
                meta_json = COALESCE(excluded.meta_json, seen_items.meta_json),
                seen_at = excluded.seen_at
            """,
            (
                source,
                item_id,
                url,
                title,
                raw_body,
                meta_json,
                status,
                score,
                draft_id,
                now,
            ),
        )


def save_finding(finding: RawFinding, *, status: str = "queued", db_path: Path = DEFAULT_DB) -> None:
    """Persist a filtered finding including raw body for later LLM re-triage."""
    mark_seen(
        finding.source,
        finding.item_id,
        url=finding.url,
        title=finding.title,
        raw_body=finding.body,
        meta=finding.meta,
        status=status,
        db_path=db_path,
    )


def row_to_finding(row: sqlite3.Row) -> RawFinding:
    meta: dict[str, Any] = {}
    if row["meta_json"]:
        try:
            meta = json.loads(row["meta_json"])
        except json.JSONDecodeError:
            meta = {}
    return RawFinding(
        source=row["source"],
        item_id=row["item_id"],
        url=row["url"] or "",
        title=row["title"] or "",
        body=row["raw_body"] or "",
        meta=meta,
    )


def list_by_status(
    status: str | tuple[str, ...],
    *,
    limit: int = 0,
    db_path: Path = DEFAULT_DB,
) -> list[RawFinding]:
    statuses = (status,) if isinstance(status, str) else status
    placeholders = ",".join("?" * len(statuses))
    sql = (
        f"SELECT * FROM seen_items WHERE status IN ({placeholders}) "
        "ORDER BY seen_at ASC"
    )
    params: list[Any] = list(statuses)
    if limit and limit > 0:
        sql += " LIMIT ?"
        params.append(limit)
    with db_session(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [row_to_finding(r) for r in rows]


def count_by_source(db_path: Path = DEFAULT_DB) -> dict[str, int]:
    with db_session(db_path) as conn:
        rows = conn.execute(
            "SELECT source, COUNT(*) AS n FROM seen_items GROUP BY source"
        ).fetchall()
    return {row["source"]: int(row["n"]) for row in rows}


def next_draft_id(year: int | None = None, db_path: Path = DEFAULT_DB) -> str:
    """Allocate the next FLAWD-YYYY-XXXX identifier."""
    year = year or datetime.now(timezone.utc).year
    with db_session(db_path) as conn:
        conn.execute(
            "INSERT INTO draft_counter (year, last) VALUES (?, 0) ON CONFLICT(year) DO NOTHING",
            (year,),
        )
        row = conn.execute(
            "SELECT last FROM draft_counter WHERE year = ?", (year,)
        ).fetchone()
        nxt = int(row["last"]) + 1
        conn.execute(
            "UPDATE draft_counter SET last = ? WHERE year = ?", (nxt, year)
        )
        return f"FLAWD-{year}-{nxt:04d}"
