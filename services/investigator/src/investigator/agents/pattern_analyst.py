from __future__ import annotations

from typing import Any

from investigator.tools.typology_tools import typology_scan, velocity_summary


def analyze_pattern(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    return {"kind": "PatternFinding", "matches": typology_scan(transactions), "velocity": velocity_summary(transactions)}
