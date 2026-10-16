from __future__ import annotations

from typing import Any


def search_media(entity_ids: list[str], corpus: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    corpus = corpus or []
    matches = [article for article in corpus if set(entity_ids).intersection(article.get("entities", []))]
    return {"kind": "MediaFinding", "matches": matches[:3], "no_adverse_media": not bool(matches), "corpus_version": "synthetic-news-2026.09"}
