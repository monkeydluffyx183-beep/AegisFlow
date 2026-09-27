from __future__ import annotations

from typing import Any


def retrieve(corpus: list[dict[str, Any]], entity_ids: set[str], limit: int = 3) -> list[dict[str, Any]]:
    """Entity-filtered lexical fallback with an interface compatible with Qdrant retrieval."""
    scored = []
    for row in corpus:
        overlap = len(entity_ids.intersection(set(row.get("entities", []))))
        if overlap:
            scored.append((overlap, row))
    return [row for _, row in sorted(scored, key=lambda pair: pair[0], reverse=True)[:limit]]
