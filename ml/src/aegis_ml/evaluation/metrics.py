from __future__ import annotations

from collections.abc import Iterable


def recall_at_fpr(labels: Iterable[int], scores: Iterable[float], target_fpr: float = 0.01) -> float:
    rows = list(zip(labels, scores))
    pairs = sorted(((score, label) for label, score in rows), reverse=True)
    negatives = sum(1 for label, _ in rows if not label)
    positives = sum(1 for label, _ in rows if label)
    if not positives:
        return 0.0
    max_false_positives = max(1, int(negatives * target_fpr))
    false_positives = true_positives = 0
    for _, label in pairs:
        if label:
            true_positives += 1
        else:
            false_positives += 1
            if false_positives > max_false_positives:
                break
    return true_positives / positives


def precision_recall(labels: Iterable[int], scores: Iterable[float], threshold: float = 0.5) -> dict[str, float]:
    rows = list(zip(labels, scores))
    tp = sum(1 for label, score in rows if label and score >= threshold)
    fp = sum(1 for label, score in rows if not label and score >= threshold)
    fn = sum(1 for label, score in rows if label and score < threshold)
    return {"precision": tp / max(1, tp + fp), "recall": tp / max(1, tp + fn)}
