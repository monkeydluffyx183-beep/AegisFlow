from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .decision import model_probability


@dataclass
class LoadedModel:
    name: str
    version: str
    stage: str

    def predict_probability(self, features: dict[str, Any]) -> float:
        return model_probability(features, challenger=self.stage == "Shadow")


def load_models() -> tuple[LoadedModel, LoadedModel]:
    """MLflow registry seam; local runtime is deterministic and dependency-light."""
    return LoadedModel("fraud-champion", "fraud-champion-2026.09", "Production"), LoadedModel("fraud-challenger-graph", "fraud-challenger-graph-v2", "Shadow")
