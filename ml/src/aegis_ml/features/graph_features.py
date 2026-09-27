from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable
from typing import Any


def compute_graph_features(edges: Iterable[dict[str, Any]], known_fraud: set[str]) -> dict[str, dict[str, float]]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        adjacency[edge["src_id"]].add(edge["dst_id"])
        adjacency[edge["dst_id"]].add(edge["src_id"])
    output: dict[str, dict[str, float]] = {}
    for root in adjacency:
        queue = deque([(root, 0)])
        seen = {root}
        distance = None
        while queue:
            node, depth = queue.popleft()
            if node in known_fraud and node != root:
                distance = depth
                break
            for neighbor in adjacency[node]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append((neighbor, depth + 1))
        component_size = len(seen)
        output[root] = {"component_size": float(component_size), "distance_to_known_fraud": float(distance if distance is not None else 99), "risk_propagation": round(1 / max(1, distance or 1) if distance is not None else 0.0, 4), "pagerank_proxy": round(1 - 1 / max(1, component_size), 4)}
    return output
