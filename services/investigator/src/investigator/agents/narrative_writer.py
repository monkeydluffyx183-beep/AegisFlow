from __future__ import annotations

from typing import Any


def write_narrative(findings: list[dict[str, Any]], evidence_ids: list[str]) -> dict[str, Any]:
    # Deliberately plain and citation-forward; the platform's investigation.py supplies the full template.
    claims = " ".join(str(item.get("kind", "finding")) for item in findings)
    return {"narrative": f"Investigation findings include {claims}.", "citations": [{"evidence_id": item} for item in evidence_ids]}
