from __future__ import annotations

from collections.abc import Iterable


def evidence_recall(expected_entities: Iterable[str], found_entities: Iterable[str]) -> float:
    expected, found = set(expected_entities), set(found_entities)
    return len(expected & found) / max(1, len(expected))


def narrative_faithfulness(claim_evidence_ids: Iterable[str], evidence_ids: Iterable[str]) -> float:
    claims, evidence = list(claim_evidence_ids), set(evidence_ids)
    return sum(item in evidence for item in claims) / max(1, len(claims))
