from __future__ import annotations

import os
import re
from typing import Any, Dict, List

# Optional: plug in a real translation provider later
# For now this module is structured so you can inject any backend.


# Very small English stopword list for canonicalization; extend as needed
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


def _dummy_translate(text: str, source_lang: str | None) -> tuple[str, float]:
    """Fallback translation when no real backend is configured.

    For now, if the detected language is English or unknown, we assume
    identity translation with relatively high confidence.
    Otherwise we still return the original text but with lower confidence
    so you can later route non-English claims to a better translation stack.
    """
    if not text:
        return "", 0.0

    if not source_lang or source_lang == "en" or source_lang == "und":
        return text, 0.9

    # Non-English but no real translation backend yet
    return text, 0.5


def _canonicalize_english(text: str) -> str:
    lowered = text.lower()
    tokens = _TOKEN_RE.findall(lowered)
    filtered = [t for t in tokens if t not in _STOPWORDS]
    # Sort tokens to get a simple canonical bag-of-words form
    filtered.sort()
    return " ".join(filtered)


def translate_and_canonicalize_claim(
    claim_text: str,
    *,
    source_language: str | None = None,
) -> Dict[str, Any]:
    """Translate a claim to English and build a canonical representation.

    Returns a structure:
    {
      "original_claim": str,
      "translated_claim": str,
      "translation_confidence": float,
      "canonical_form": str,
    }
    """
    original = claim_text or ""

    translated, confidence = _dummy_translate(original, source_language)
    canonical = _canonicalize_english(translated)

    return {
        "original_claim": original,
        "translated_claim": translated,
        "translation_confidence": float(confidence),
        "canonical_form": canonical,
    }


def translate_and_canonicalize_claims(
    claims: List[Dict[str, Any]],
    *,
    source_language: str | None = None,
) -> List[Dict[str, Any]]:
    """Apply translation + canonicalization over a list of claim objects.

    Each returned claim will have an additional key `translation` with the
    exported structure.
    """
    enriched: List[Dict[str, Any]] = []

    for claim in claims:
        if not isinstance(claim, dict):
            continue

        text = str(claim.get("text", ""))
        translation_info = translate_and_canonicalize_claim(
            text,
            source_language=source_language,
        )

        enriched_claim = dict(claim)
        enriched_claim["translation"] = translation_info
        enriched.append(enriched_claim)

    return enriched
