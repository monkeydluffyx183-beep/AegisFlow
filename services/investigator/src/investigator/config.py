import os
from dataclasses import dataclass


@dataclass(frozen=True)
class InvestigatorConfig:
    max_agent_turns: int = int(os.getenv("MAX_AGENT_TURNS", "12"))
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    corpus_version: str = "synthetic-news-2026.09"
    require_human_approval: bool = True
