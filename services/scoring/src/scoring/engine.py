from __future__ import annotations

import time
import uuid
from typing import Any

from .decision import Thresholds, choose_decision, model_probability
from .explain import reason_codes
from .feature_reader import OnlineFeatureReader
from .rules import evaluate_rules
from .schemas import DecisionResult, ReasonCode, RuleHit, ScoreRequest


class ScoringEngine:
    """Hybrid champion/rules scorer with a deterministic demo model.

    The method keeps the latency-critical path free of database calls. Persistence happens
    in the API after this object returns, matching the gateway/scorer separation in the
    architecture document.
    """

    def __init__(self, thresholds: Thresholds | None = None) -> None:
        self.feature_reader = OnlineFeatureReader()
        self.thresholds = thresholds or Thresholds()
        self.model_version = "fraud-champion-2026.09"
        self.challenger_version = "fraud-challenger-graph-v2"
        self.shadow_scored = 0
        self.shadow_disagreements = 0

    def update_thresholds(self, review: float, decline: float) -> None:
        if not (0 < review < decline < 1):
            raise ValueError("thresholds must satisfy 0 < review < decline < 1")
        self.thresholds = Thresholds(review=review, decline=decline)

    def seed_account(self, account_id: str, **values: Any) -> None:
        self.feature_reader.seed_account(account_id, **values)

    def score(self, request: ScoreRequest) -> DecisionResult:
        started = time.perf_counter()
        features_snapshot = self.feature_reader.read(request)
        features = features_snapshot.values
        hits_data = evaluate_rules(request, features)
        probability = model_probability(features)
        challenger_prob = model_probability(features, challenger=True)
        decision = choose_decision(probability, hits_data, self.thresholds)
        challenger_decision = choose_decision(challenger_prob, hits_data, self.thresholds)
        self.shadow_scored += 1
        if challenger_decision != decision:
            self.shadow_disagreements += 1
        reasons = reason_codes(features, probability)
        # Rules are appended only when they add a visible, auditable reason not already present.
        for hit in hits_data:
            code = hit.rule_id
            if not any(item["code"] == code for item in reasons):
                reasons.append({"code": code, "label": hit.label, "contribution": 0.9 if hit.action == "decline" else 0.55, "direction": "increases_risk"})
        transaction_id = request.id or str(uuid.uuid4())
        elapsed_ms = (time.perf_counter() - started) * 1000
        return DecisionResult(
            transaction_id=transaction_id,
            decision=decision,
            score=round(probability, 6),
            calibrated_prob=round(probability, 6),
            reason_codes=[ReasonCode(**item) for item in reasons[:5]],
            rule_hits=[RuleHit(rule_id=x.rule_id, label=x.label, severity=x.severity, action=x.action, detail=x.detail) for x in hits_data],
            features=features,
            model_version=self.model_version,
            challenger={"version": self.challenger_version, "probability": round(challenger_prob, 6), "disagreement": challenger_decision != decision, "decision": challenger_decision},
            latency_ms=round(elapsed_ms, 3),
            degraded=not features_snapshot.hit,
            feature_store_hit=features_snapshot.hit,
        )

    @property
    def shadow_disagreement_rate(self) -> float:
        return self.shadow_disagreements / self.shadow_scored if self.shadow_scored else 0.0
