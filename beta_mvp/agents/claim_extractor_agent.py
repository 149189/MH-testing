from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List

import google.generativeai as genai

# Configure Gemini client from environment
_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

if _GEMINI_API_KEY:
    genai.configure(api_key=_GEMINI_API_KEY)


_SYSTEM_PROMPT = (
    "You are a claim extraction engine. "
    "Extract only factual claims. Ignore opinions. Output JSON only."
)


def _build_user_prompt(text: str) -> str:
    return (
        "Extract all factual claims from the following text. "
        "For each claim, produce a JSON object with keys: "
        "claim_id (uuid), text, subject, predicate, object, "
        "type (causal/descriptive/statistical/event/etc.), span (character start,end).\n\n"
        f"Text:\n{text}\n\n"
        "Return a JSON array only."
    )


def _parse_response(content: str) -> List[Dict[str, Any]]:
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    # If the model misbehaves, return empty list to keep pipeline robust
    return []


def extract_claims(normalized_text: str) -> List[Dict[str, Any]]:
    """LLM-driven claim extraction.

    Takes normalized text and returns a list of claim objects:
    [
      {
        "claim_id": "<uuid>",
        "text": "...",
        "subject": "...",
        "predicate": "...",
        "object": "...",
        "type": "causal/descriptive/statistical/event/etc.",
        "span": [start, end]
      }
    ]
    """

    if not normalized_text.strip():
        return []

    if not _GEMINI_API_KEY:
        # If no key configured, return empty list but remain callable
        return []

    prompt = _SYSTEM_PROMPT + "\n\n" + _build_user_prompt(normalized_text)

    model = genai.GenerativeModel(_GEMINI_MODEL)
    response = model.generate_content(prompt)
    content = (response.text or "").strip()
    claims = _parse_response(content)

    # Ensure each claim has a UUID
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        if "claim_id" not in claim or not claim["claim_id"]:
            claim["claim_id"] = str(uuid.uuid4())

    return claims
