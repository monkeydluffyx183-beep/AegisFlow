import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CaseworkConfig:
    jwt_secret: str = os.getenv("JWT_SECRET", "local-only-change-me")
    default_sla_hours: int = 8
    evidence_citation_required: bool = True
