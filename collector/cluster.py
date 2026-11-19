"""Gate 1 dedup: cluster candidate findings by category + pattern key."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass

from collector.quarantine import list_findings, update_finding, upsert_cluster
from collector.rejection import FindingState, RejectionCode


@dataclass
class ClusterMember:
    finding_pk: str
    title: str
    url: str
    category: str
    confidence: float


def _normalize_title(title: str) -> str:
    t = title.lower()
    t = re.sub(r"`[^`]+`", " ", t)
    t = re.sub(r"\[[^\]]+\]", " ", t)
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\b(bug|fix|feat|docs|chore)\b", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    # Keep first ~12 tokens for stability.
    tokens = t.split()[:12]
    return " ".join(tokens)


def pattern_key(category: str, title: str) -> str:
    norm = _normalize_title(title)
    digest = hashlib.sha1(f"{category}|{norm}".encode("utf-8")).hexdigest()[:10]
    return f"{category}:{digest}"


def cluster_id_for(key: str) -> str:
    return f"cluster_{hashlib.sha1(key.encode()).hexdigest()[:12]}"


def build_clusters(candidates: list[ClusterMember]) -> dict[str, list[ClusterMember]]:
    groups: dict[str, list[ClusterMember]] = defaultdict(list)
    for m in candidates:
        key = pattern_key(m.category, m.title)
        groups[key].append(m)
    return dict(groups)


def apply_clusters(db_path=None) -> dict[str, int]:
    """Cluster all `candidate` findings; mark non-primary members as merged."""
    rows = list_findings(state=FindingState.CANDIDATE.value, db_path=db_path) if db_path else list_findings(state=FindingState.CANDIDATE.value)
    # Also include already-candidate rows that may be re-clustered — load candidates only.
    members: list[ClusterMember] = []
    for r in rows:
        if not r["category"]:
            continue
        members.append(
            ClusterMember(
                finding_pk=r["finding_pk"],
                title=r["title"] or "",
                url=r["url"] or "",
                category=r["category"],
                confidence=float(r["confidence"] or 0),
            )
        )

    groups = build_clusters(members)
    stats = {"clusters": 0, "merged": 0, "primaries": 0}

    for key, group in groups.items():
        group_sorted = sorted(group, key=lambda m: (-m.confidence, m.finding_pk))
        primary = group_sorted[0]
        cid = cluster_id_for(key)
        label = f"{primary.category}: {primary.title[:80]}"
        kwargs = dict(
            cluster_id=cid,
            pattern_key=key,
            category=primary.category,
            label=label,
            primary_finding_pk=primary.finding_pk,
            member_count=len(group_sorted),
        )
        if db_path is not None:
            upsert_cluster(**kwargs, db_path=db_path)
        else:
            upsert_cluster(**kwargs)
        stats["clusters"] += 1
        stats["primaries"] += 1

        update_kwargs = dict(cluster_id=cid)
        if db_path is not None:
            update_finding(primary.finding_pk, db_path=db_path, **update_kwargs)
        else:
            update_finding(primary.finding_pk, **update_kwargs)

        for m in group_sorted[1:]:
            if db_path is not None:
                update_finding(
                    m.finding_pk,
                    state=FindingState.MERGED.value,
                    cluster_id=cid,
                    rejection_code=RejectionCode.G1_DUPLICATE_MERGED.value,
                    rejection_detail=f"merged into {primary.finding_pk}",
                    db_path=db_path,
                )
            else:
                update_finding(
                    m.finding_pk,
                    state=FindingState.MERGED.value,
                    cluster_id=cid,
                    rejection_code=RejectionCode.G1_DUPLICATE_MERGED.value,
                    rejection_detail=f"merged into {primary.finding_pk}",
                )
            stats["merged"] += 1

    return stats
