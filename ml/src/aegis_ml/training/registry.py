from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromotionDecision:
    promote: bool
    reason: str


def evaluate_promotion(*, champion_recall: float, challenger_recall: float, minimum_lift: float = 0.05, labeled_window: int = 10_000, minimum_window: int = 10_000, human_approved: bool = False) -> PromotionDecision:
    lift = (challenger_recall - champion_recall) / max(champion_recall, 1e-9)
    if labeled_window < minimum_window:
        return PromotionDecision(False, "labeled window is below the promotion minimum")
    if lift < minimum_lift:
        return PromotionDecision(False, f"challenger lift {lift:.2%} is below {minimum_lift:.2%}")
    if not human_approved:
        return PromotionDecision(False, "explicit human approval is required")
    return PromotionDecision(True, f"challenger lift {lift:.2%} passed policy")
