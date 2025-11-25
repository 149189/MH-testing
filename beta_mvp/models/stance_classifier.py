from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Literal

import google.generativeai as genai

StanceLabel = Literal["support", "refute", "neutral"]

_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

if _GEMINI_API_KEY:
    genai.configure(api_key=_GEMINI_API_KEY)


_SYSTEM_PROMPT = (
    "You are a stance detection engine. "
    "Does this evidence support, refute, or remain neutral to the claim? "
    "Return JSON only."
)


def _build_user_prompt_single(claim: str, evidence: str) -> str:
    return (
        "Determine the stance of the evidence with respect to the claim.\n"
        "Stance must be one of: support, refute, neutral.\n"
        "Return a JSON object: {\"stance\": \"support|refute|neutral\", \"confidence\": number between 0 and 1}.\n\n"
        f"Claim: {claim}\n\nEvidence: {evidence}\n\n"
        "JSON only, no extra text."
    )


def _parse_single(content: str) -> Dict[str, Any]:
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            stance = data.get("stance", "neutral")
            if stance not in ("support", "refute", "neutral"):
                stance = "neutral"
            conf = float(data.get("confidence", 0.0))
            conf = max(0.0, min(1.0, conf))
            return {"stance": stance, "confidence": conf}
    except Exception:
        pass
    return {"stance": "neutral", "confidence": 0.0}


def classify_stance(claim_text: str, evidence_snippet: str) -> Dict[str, Any]:
    """Classify stance for a single claim/evidence pair.

    Returns: {"stance": "support|refute|neutral", "confidence": 0..1}
    """
    if not claim_text or not evidence_snippet or not _GEMINI_API_KEY:
        return {"stance": "neutral", "confidence": 0.0}

    prompt = _SYSTEM_PROMPT + "\n\n" + _build_user_prompt_single(
        claim_text,
        evidence_snippet,
    )

    model = genai.GenerativeModel(_GEMINI_MODEL)
    response = model.generate_content(prompt)
    content = (response.text or "").strip()
    return _parse_single(content)


def classify_stance_batch(pairs: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Batch stance detection.

    Each input item should be {"claim": str, "evidence": str}.
    Returns a list of results with the same length/order.
    """
    results: List[Dict[str, Any]] = []

    if not _GEMINI_API_KEY:
        # Fast path: everything neutral if no model available
        return [{"stance": "neutral", "confidence": 0.0} for _ in pairs]

    for item in pairs:
        claim = item.get("claim", "")
        evidence = item.get("evidence", "")
        results.append(classify_stance(claim, evidence))

    return results
