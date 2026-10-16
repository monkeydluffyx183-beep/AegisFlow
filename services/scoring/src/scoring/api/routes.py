from __future__ import annotations

from fastapi import APIRouter

from ..engine import ScoringEngine
from ..schemas import ScoreRequest

router = APIRouter(prefix="/score", tags=["scoring"])
_engine = ScoringEngine()


@router.post("")
def score(payload: ScoreRequest):
    result = _engine.score(payload)
    _engine.feature_reader.observe(payload)
    return result
