from __future__ import annotations

from typing import Any


def to_structured_sar(*, case: dict[str, Any], draft: dict[str, Any]) -> dict[str, Any]:
    """Render the approved internal draft into a FinCEN-shaped synthetic payload."""
    if draft.get("status") != "approved":
        raise ValueError("only approved drafts can be exported")
    return {
        "schema": "aegisflow.synthetic.sar.v1",
        "filing_type": "SAR",
        "subject_accounts": case.get("account_ids", []),
        "activity_type": case.get("typology", "other"),
        "narrative": draft.get("narrative_md", ""),
        "evidence_citations": draft.get("citations", []),
        "human_approval": {"reviewed_by": draft.get("reviewed_by"), "rationale": draft.get("review_rationale")},
        "autonomous_filing": False,
    }
