from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def ingest_news(corpus_path: str, output_path: str) -> int:
    """Prepare synthetic article chunks; embeddings are a deployment concern."""
    source = Path(corpus_path)
    rows: list[dict[str, Any]] = []
    if source.exists():
        for line in source.read_text().splitlines():
            if line.strip():
                article = json.loads(line)
                rows.append({"article_id": article.get("article_id"), "entities": article.get("entities", []), "text": article.get("text", ""), "source": article.get("source", "synthetic")})
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(json.dumps(row) for row in rows) + ("\n" if rows else ""))
    return len(rows)
