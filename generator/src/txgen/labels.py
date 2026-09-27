from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_labels(rows: list[dict[str, Any]], path: str = "data/ground_truth.jsonl") -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps({"transaction_id": row.get("id"), "labels": row.get("labels", []), "ring_id": row.get("ring_id")}) + "\n")
