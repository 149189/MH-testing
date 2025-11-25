from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

# Placeholders for Redis and FAISS integrations; wire in real clients later.
try:
    import redis  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    redis = None  # type: ignore

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    faiss = None  # type: ignore


@dataclass
class Evidence:
    id: str
    source: str
    url: Optional[str]
    title: Optional[str]
    snippet: str
    published_at: Optional[datetime]
    source_credibility: float
    semantic_score: float
    recency_score: float

    @property
    def final_score(self) -> float:
        """Simple weighted score; tune weights later."""
        return (
            0.5 * self.semantic_score
            + 0.3 * self.source_credibility
            + 0.2 * self.recency_score
        )


class Retriever:
    """Multi-source evidence retriever.

    This is a skeleton that combines several backends:
      1. Cache lookup (Redis)
      2. Vector search (FAISS)
      3. Web search placeholder
      4. Site-specific search (gov, fact-checks)
    and returns a ranked JSON evidence list.
    """

    def __init__(self) -> None:
        self._redis_client = self._init_redis()
        self._faiss_index = self._init_faiss()

    def _init_redis(self):  # type: ignore[no-untyped-def]
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        if redis is None:
            return None
        try:
            return redis.from_url(url)
        except Exception:
            return None

    def _init_faiss(self):  # type: ignore[no-untyped-def]
        # In a real implementation you would load an index file from disk.
        # For now we just return None as a placeholder.
        return None if faiss is None else None

    # ---- Public API ----

    def retrieve_for_claim(self, claim: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Retrieve ranked evidence list for a single claim.

        Returns a list of JSON objects sorted by final score descending.
        """
        text = str(claim.get("text", ""))
        if not text:
            return []

        candidates: List[Evidence] = []

        candidates.extend(self._from_cache(text))
        candidates.extend(self._from_vector_search(text))
        candidates.extend(self._from_web_search(text))
        candidates.extend(self._from_site_specific(text))

        # Rank by final score
        ranked = sorted(candidates, key=lambda e: e.final_score, reverse=True)

        return [self._to_json(e) for e in ranked]

    # ---- Backends (stubs) ----

    def _from_cache(self, query: str) -> List[Evidence]:
        # TODO: add a scheme for cache keys; for now this is a stub.
        return []

    def _from_vector_search(self, query: str) -> List[Evidence]:
        # TODO: embed query, search FAISS index, map back to metadata.
        return []

    def _from_web_search(self, query: str) -> List[Evidence]:
        # Placeholder for generic web search; return empty for now.
        return []

    def _from_site_specific(self, query: str) -> List[Evidence]:
        # Placeholder for gov / fact-check sites integration.
        return []

    # ---- Helpers ----

    def _to_json(self, e: Evidence) -> Dict[str, Any]:
        return {
            "id": e.id,
            "source": e.source,
            "url": e.url,
            "title": e.title,
            "snippet": e.snippet,
            "published_at": e.published_at.isoformat() + "Z" if e.published_at else None,
            "source_credibility": e.source_credibility,
            "semantic_score": e.semantic_score,
            "recency_score": e.recency_score,
            "final_score": e.final_score,
        }


_default_retriever: Optional[Retriever] = None


def get_retriever() -> Retriever:
    global _default_retriever
    if _default_retriever is None:
        _default_retriever = Retriever()
    return _default_retriever


def retrieve_evidence_for_claims(claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convenience function to retrieve evidence for a list of claims.

    Returns a list with the same length and order as `claims`, where each
    element is a dict:
    {
      "claim_id": "...",
      "evidence": [ ... ranked evidence list ... ]
    }
    """
    retriever = get_retriever()
    results: List[Dict[str, Any]] = []

    for claim in claims:
        if not isinstance(claim, dict):
            continue
        cid = str(claim.get("claim_id", ""))
        evidence_list = retriever.retrieve_for_claim(claim)
        results.append({"claim_id": cid, "evidence": evidence_list})

    return results
