from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    redis = None  # type: ignore

# Basic English stopword set; extend as needed
_STOPWORDS = {
    "the",
    "a",
    "an",
    "of",
    "and",
    "or",
    "to",
    "in",
    "on",
    "for",
    "with",
    "at",
    "by",
    "from",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
}

_TOKEN_RE = re.compile(r"\w+")

_CACHE_TTL_SECONDS_DEFAULT = 7 * 24 * 60 * 60  # 7 days


def _get_redis_client():  # type: ignore[no-untyped-def]
    if redis is None:
        return None
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        return redis.from_url(url)
    except Exception:
        return None


_redis_client = _get_redis_client()


def generate_claim_fingerprint(text: str) -> str:
    """Generate a stable fingerprint based on sorted tokens without stopwords."""
    lowered = (text or "").lower()
    tokens = _TOKEN_RE.findall(lowered)
    filtered = [t for t in tokens if t not in _STOPWORDS]
    filtered.sort()
    return "|".join(filtered)


def get_cached_verdict(fingerprint: str) -> Optional[Dict[str, Any]]:
    """Return cached verdict JSON for a fingerprint if available."""
    if not fingerprint or _redis_client is None:
        return None
    try:
        raw = _redis_client.get(f"claim_verdict:{fingerprint}")
    except Exception:
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        return None
    return None


def set_cached_verdict(
    fingerprint: str,
    verdict: Dict[str, Any],
    ttl_seconds: Optional[int] = None,
) -> None:
    """Store verdict JSON in Redis with configurable expiry."""
    if not fingerprint or _redis_client is None:
        return
    ttl = ttl_seconds or int(os.getenv("CACHE_TTL_SECONDS", str(_CACHE_TTL_SECONDS_DEFAULT)))
    try:
        payload = json.dumps(verdict)
        _redis_client.setex(f"claim_verdict:{fingerprint}", ttl, payload)
    except Exception:
        # Cache failures must never break the main pipeline
        return
