# Author: 晨星
"""Retrieval evaluation metrics. All deterministic, no external deps."""
from __future__ import annotations


def recall_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Fraction of relevant items appearing in top-k."""
    if not relevant_ids:
        return 0.0
    hits = sum(1 for rid in ranked_ids[:k] if rid in relevant_ids)
    return hits / len(relevant_ids)


def reciprocal_rank(ranked_ids: list[str], relevant_ids: set[str]) -> float:
    """1/rank of the first relevant hit (0 if none)."""
    for i, rid in enumerate(ranked_ids):
        if rid in relevant_ids:
            return 1.0 / (i + 1)
    return 0.0


def keyword_coverage(answer: str, keywords: list[str]) -> float:
    """Fraction of expected keywords present in the answer."""
    if not keywords:
        return 1.0
    hits = sum(1 for kw in keywords if kw in answer)
    return hits / len(keywords)


def aggregate(per_query: list[dict[str, float]]) -> dict[str, float]:
    """Mean of each metric across queries."""
    if not per_query:
        return {}
    keys = per_query[0].keys()
    return {k: round(sum(row[k] for row in per_query) / len(per_query), 4) for k in keys}
