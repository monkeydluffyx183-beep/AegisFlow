from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable


def cohort_review_rates(rows: Iterable[dict[str, object]], cohort_key: str = "cohort") -> dict[str, float]:
    totals: defaultdict[str, int] = defaultdict(int)
    flagged: defaultdict[str, int] = defaultdict(int)
    for row in rows:
        cohort = str(row.get(cohort_key, "unknown"))
        totals[cohort] += 1
        flagged[cohort] += int(row.get("decision") in {"review", "decline"})
    return {cohort: flagged[cohort] / max(1, total) for cohort, total in totals.items()}


def disparate_impact(rates: dict[str, float], reference: str | None = None) -> dict[str, float]:
    if not rates:
        return {}
    ref_key = reference or max(rates, key=rates.get)
    ref = max(rates[ref_key], 1e-9)
    return {key: round(value / ref, 4) for key, value in rates.items()}
