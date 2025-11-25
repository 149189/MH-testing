from __future__ import annotations

import html
import re
from typing import Any, Dict, Optional

# URL regex is intentionally conservative
_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
# Basic emoji and symbol range; you can refine this later
_EMOJI_RE = re.compile("[\U00010000-\U0010ffff]", flags=re.UNICODE)


def _strip_html(text: str) -> str:
    # Very lightweight HTML tag stripper; for heavy HTML use something like BeautifulSoup
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(text)


def _clean_text(raw_text: str) -> str:
    text = raw_text or ""
    text = _strip_html(text)
    # Remove URLs but keep a simple marker
    text = _URL_RE.sub(" ", text)
    # Remove emojis
    text = _EMOJI_RE.sub("", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _heuristic_language_detection(text: str) -> tuple[str, float]:
    """Very rough heuristic detector.

    This is a placeholder until you wire a proper fastText or transformer model.
    """
    if not text:
        return "und", 0.0

    # Extremely naive heuristic examples; adjust for your domains
    latin_chars = len(re.findall(r"[A-Za-z]", text))
    devanagari_chars = len(re.findall(r"[\u0900-\u097F]", text))

    total_alpha = latin_chars + devanagari_chars
    if total_alpha == 0:
        return "und", 0.1

    latin_ratio = latin_chars / total_alpha if total_alpha else 0

    if latin_ratio > 0.7:
        return "en", min(0.9, latin_ratio)
    if devanagari_chars / total_alpha > 0.7:
        # Many Indian languages in Devanagari; treat as generic "hi" for now
        return "hi", 0.8

    # Fallback: unknown
    return "und", 0.3


def detect_language(text: str) -> Dict[str, Any]:
    """Public language detection API.

    Later you can replace the internals with fastText or a transformer
    while keeping this function signature stable.
    """
    clean = _clean_text(text)
    lang, conf = _heuristic_language_detection(clean)

    # Fallback heuristics for very low confidence
    if conf < 0.3 and clean:
        # If long-ish text with lots of Latin, bump towards en
        latin_chars = len(re.findall(r"[A-Za-z]", clean))
        if latin_chars > 5:
            lang = "en"
            conf = 0.35

    return {
        "clean_text": clean,
        "language": lang,
        "confidence": float(conf),
    }


def speech_to_text_placeholder(audio_bytes: Optional[bytes] = None, *, language_hint: Optional[str] = None) -> Dict[str, Any]:
    """Placeholder for future speech-to-text integration.

    When you plug in a real STT engine (e.g., Whisper, cloud STT),
    return a structure similar to detect_language() plus raw metadata.
    """
    _ = audio_bytes, language_hint  # unused for now
    return {
        "clean_text": "",
        "language": "und",
        "confidence": 0.0,
    }


def process_text_for_ingestion(text: str) -> Dict[str, Any]:
    """Main entry used by ingestion connectors.

    Returns a structured object:
    {"clean_text": str, "language": str, "confidence": float}
    """
    return detect_language(text)
