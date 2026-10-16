from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class FindingUnavailable:
    specialist: str
    reason: str


@dataclass
class CaseState:
    case_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    findings: list[dict[str, Any] | FindingUnavailable] = field(default_factory=list)
    draft: str | None = None
    citations: list[dict[str, Any]] = field(default_factory=list)
    qa_verdict: Literal["pending", "pass", "fail"] = "pending"
    qa_notes: list[str] = field(default_factory=list)
    turns: int = 0
