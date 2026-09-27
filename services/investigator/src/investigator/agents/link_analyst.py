from __future__ import annotations

from typing import Any


def analyze_link(graph: dict[str, Any], account_ids: list[str]) -> dict[str, Any]:
    related = [node for node in graph.get("nodes", []) if node.get("id") in account_ids or node.get("risk") in {"high", "critical"}]
    return {"kind": "RingFinding", "entities": [node["id"] for node in related], "edges": graph.get("edges", []), "confidence": 0.88 if len(related) > 2 else 0.61}
