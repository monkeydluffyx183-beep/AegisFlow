from __future__ import annotations

from collections import defaultdict, deque
from typing import Any


def khop_neighborhood(nodes: list[dict[str, Any]], edges: list[dict[str, Any]], roots: list[str], hops: int = 2) -> dict[str, Any]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        adjacency[edge["source"]].add(edge["target"])
        adjacency[edge["target"]].add(edge["source"])
    seen = set(roots)
    queue = deque((root, 0) for root in roots)
    while queue:
        node, distance = queue.popleft()
        if distance >= hops:
            continue
        for neighbor in adjacency[node]:
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append((neighbor, distance + 1))
    return {"nodes": [node for node in nodes if node.get("id") in seen], "edges": [edge for edge in edges if edge.get("source") in seen and edge.get("target") in seen]}


def path_to_known_fraud(edges: list[dict[str, Any]], root: str, known_fraud: set[str]) -> dict[str, Any] | None:
    graph: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        graph[edge["source"]].append(edge["target"])
        graph[edge["target"]].append(edge["source"])
    queue = deque([(root, [root])])
    seen = {root}
    while queue:
        current, path = queue.popleft()
        if current in known_fraud:
            return {"path": path, "hops": len(path) - 1}
        for neighbor in graph[current]:
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    return None
