"""Quarantine DB for gated ingestion (pipeline.db)."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from collector.rejection import FindingState

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PIPELINE_DB = ROOT / "pipeline.db"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect(db_path: Path = DEFAULT_PIPELINE_DB) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_pipeline_db(db_path: Path = DEFAULT_PIPELINE_DB) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS findings (
                finding_pk TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                url TEXT,
                title TEXT,
                raw_body TEXT,
                meta_json TEXT,
                cluster_id TEXT,
                state TEXT NOT NULL DEFAULT 'raw',
                category TEXT,
                confidence REAL,
                rejection_code TEXT,
                rejection_detail TEXT,
                draft_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS clusters (
                cluster_id TEXT PRIMARY KEY,
                pattern_key TEXT NOT NULL,
                category TEXT,
                label TEXT,
                primary_finding_pk TEXT,
                member_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS gate_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                finding_pk TEXT NOT NULL,
                gate TEXT NOT NULL,
                outcome TEXT NOT NULL,
                code TEXT,
                detail TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


@contextmanager
def session(db_path: Path = DEFAULT_PIPELINE_DB) -> Iterator[sqlite3.Connection]:
    init_pipeline_db(db_path)
    conn = _connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert_raw(
    *,
    source_type: str,
    source_id: str,
    url: str | None,
    title: str | None,
    raw_body: str | None,
    meta: dict[str, Any] | None = None,
    db_path: Path = DEFAULT_PIPELINE_DB,
) -> str:
    pk = f"{source_type}:{source_id}"
    now = _now()
    with session(db_path) as conn:
        existing = conn.execute(
            "SELECT finding_pk FROM findings WHERE finding_pk = ?", (pk,)
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE findings SET
                    url = COALESCE(?, url),
                    title = COALESCE(?, title),
                    raw_body = COALESCE(?, raw_body),
                    meta_json = COALESCE(?, meta_json),
                    updated_at = ?
                WHERE finding_pk = ?
                """,
                (
                    url,
                    title,
                    raw_body,
                    json.dumps(meta or {}, ensure_ascii=False) if meta is not None else None,
                    now,
                    pk,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO findings (
                    finding_pk, source_type, source_id, url, title, raw_body, meta_json,
                    state, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pk,
                    source_type,
                    source_id,
                    url,
                    title,
                    raw_body,
                    json.dumps(meta or {}, ensure_ascii=False),
                    FindingState.RAW.value,
                    now,
                    now,
                ),
            )
    return pk


def log_gate(
    finding_pk: str,
    gate: str,
    outcome: str,
    *,
    code: str | None = None,
    detail: str | None = None,
    db_path: Path = DEFAULT_PIPELINE_DB,
) -> None:
    with session(db_path) as conn:
        conn.execute(
            """
            INSERT INTO gate_events (finding_pk, gate, outcome, code, detail, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (finding_pk, gate, outcome, code, detail, _now()),
        )


def update_finding(
    finding_pk: str,
    *,
    state: str | None = None,
    cluster_id: str | None = None,
    category: str | None = None,
    confidence: float | None = None,
    rejection_code: str | None = None,
    rejection_detail: str | None = None,
    draft_id: str | None = None,
    db_path: Path = DEFAULT_PIPELINE_DB,
) -> None:
    fields: list[str] = ["updated_at = ?"]
    values: list[Any] = [_now()]
    mapping = {
        "state": state,
        "cluster_id": cluster_id,
        "category": category,
        "confidence": confidence,
        "rejection_code": rejection_code,
        "rejection_detail": rejection_detail,
        "draft_id": draft_id,
    }
    for col, val in mapping.items():
        if val is not None:
            fields.append(f"{col} = ?")
            values.append(val)
    values.append(finding_pk)
    with session(db_path) as conn:
        conn.execute(
            f"UPDATE findings SET {', '.join(fields)} WHERE finding_pk = ?",
            values,
        )


def upsert_cluster(
    *,
    cluster_id: str,
    pattern_key: str,
    category: str | None,
    label: str,
    primary_finding_pk: str,
    member_count: int,
    db_path: Path = DEFAULT_PIPELINE_DB,
) -> None:
    now = _now()
    with session(db_path) as conn:
        conn.execute(
            """
            INSERT INTO clusters (
                cluster_id, pattern_key, category, label, primary_finding_pk,
                member_count, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cluster_id) DO UPDATE SET
                pattern_key = excluded.pattern_key,
                category = excluded.category,
                label = excluded.label,
                primary_finding_pk = excluded.primary_finding_pk,
                member_count = excluded.member_count,
                updated_at = excluded.updated_at
            """,
            (
                cluster_id,
                pattern_key,
                category,
                label,
                primary_finding_pk,
                member_count,
                now,
                now,
            ),
        )


def list_findings(
    *,
    state: str | None = None,
    db_path: Path = DEFAULT_PIPELINE_DB,
) -> list[sqlite3.Row]:
    with session(db_path) as conn:
        if state:
            return list(
                conn.execute(
                    "SELECT * FROM findings WHERE state = ? ORDER BY updated_at",
                    (state,),
                ).fetchall()
            )
        return list(conn.execute("SELECT * FROM findings ORDER BY updated_at").fetchall())


def funnel_counts(db_path: Path = DEFAULT_PIPELINE_DB) -> dict[str, int]:
    with session(db_path) as conn:
        rows = conn.execute(
            "SELECT state, COUNT(*) AS n FROM findings GROUP BY state"
        ).fetchall()
    return {r["state"]: int(r["n"]) for r in rows}


def reject_counts(db_path: Path = DEFAULT_PIPELINE_DB) -> dict[str, int]:
    with session(db_path) as conn:
        rows = conn.execute(
            """
            SELECT rejection_code, COUNT(*) AS n FROM findings
            WHERE state = 'rejected' AND rejection_code IS NOT NULL
            GROUP BY rejection_code
            """
        ).fetchall()
    return {r["rejection_code"]: int(r["n"]) for r in rows}


def list_clusters(db_path: Path = DEFAULT_PIPELINE_DB) -> list[sqlite3.Row]:
    with session(db_path) as conn:
        return list(
            conn.execute(
                "SELECT * FROM clusters ORDER BY member_count DESC, category"
            ).fetchall()
        )
