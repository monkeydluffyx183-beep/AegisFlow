from __future__ import annotations

from typing import Any


def review_narrative(narrative: str, citations: list[dict[str, Any]], evidence_ids: set[str]) -> dict[str, Any]:
    cited = {item.get("evidence_id") for item in citations}
    missing = sorted(cited - evidence_ids)
    return {"verdict": "fail" if missing or not narrative.strip() else "pass", "uncited_evidence_ids": missing, "amounts_verified": not bool(missing), "notes": [f"Unknown evidence IDs: {missing}"] if missing else []}
