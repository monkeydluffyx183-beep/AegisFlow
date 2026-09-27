from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ShadowMetrics:
    scored: int = 0
    disagreements: int = 0
    challenger_review_lift: float = 0.0

    def record(self, disagreement: bool) -> None:
        self.scored += 1
        self.disagreements += int(disagreement)

    @property
    def disagreement_rate(self) -> float:
        return self.disagreements / self.scored if self.scored else 0.0
