from __future__ import annotations

import math
from collections.abc import Iterable


def _bins(values: list[float], edges: list[float]) -> list[float]:
    counts = [0] * (len(edges) + 1)
    for value in values:
        index = 0
        while index < len(edges) and value > edges[index]:
            index += 1
        counts[index] += 1
    total = max(1, len(values))
    return [count / total for count in counts]


def population_stability_index(expected: Iterable[float], actual: Iterable[float], bins: int = 10) -> float:
    baseline = sorted(float(x) for x in expected)
    current = [float(x) for x in actual]
    if not baseline or not current:
        return 0.0
    edges = [baseline[min(len(baseline) - 1, int(len(baseline) * idx / bins))] for idx in range(1, bins)]
    expected_dist = _bins(baseline, edges)
    actual_dist = _bins(current, edges)
    return round(sum((a - e) * math.log(max(a, 1e-6) / max(e, 1e-6)) for e, a in zip(expected_dist, actual_dist)), 6)
