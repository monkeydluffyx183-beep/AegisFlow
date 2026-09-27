from __future__ import annotations

from typing import Any


def disposition_to_label(disposition: str) -> int | None:
    return {"fraud": 1, "not_fraud": 0, "sar_filed": 1}.get(disposition)


def feedback_row(*, transaction_id: str, disposition: str, rationale: str, reviewed_at: str) -> dict[str, Any] | None:
    label = disposition_to_label(disposition)
    if label is None:
        return None
    return {"transaction_id": transaction_id, "label": label, "label_source": "analyst_disposition", "rationale": rationale, "reviewed_at": reviewed_at}
