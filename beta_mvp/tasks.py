from __future__ import annotations

from typing import Any, Dict
import time

from celery.utils.log import get_task_logger

from .celery_app import celery_app
from .agents.claim_extractor_agent import extract_claims
from .models.translation_pipeline import translate_and_canonicalize_claims
from .rag.retriever import retrieve_evidence_for_claims
from .models.stance_classifier import classify_stance_batch
from .models.veracity_classifier import classify_veracity
from .monitoring.metrics import record_verification_time, record_language
from .utils.cache_manager import (
    generate_claim_fingerprint,
    get_cached_verdict,
    set_cached_verdict,
)

logger = get_task_logger(__name__)


@celery_app.task(name="process_post")
def process_post(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize entrypoint for all ingestion connectors.

    For now, this runs claim extraction on the normalized text, then applies
    translation + canonicalization on the extracted claims, and logs the
    enriched claims along with the payload. Verification, RAG, and
    persistence logic will be added later.
    """
    # Prefer language-processed clean_text if available
    start_time = time.monotonic()
    clean_text: str = ""
    language_analysis = payload.get("language_analysis") or {}
    if isinstance(language_analysis, dict):
        clean_text = language_analysis.get("clean_text") or ""

    if not clean_text:
        content = payload.get("content") or {}
        if isinstance(content, dict):
            clean_text = content.get("raw_text") or ""

    # Cache check at the very beginning of the pipeline
    fingerprint = generate_claim_fingerprint(clean_text)
    cached = get_cached_verdict(fingerprint)
    if cached is not None:
        logger.info("Cache hit for claim", extra={"payload": payload})
        return cached

    claims = extract_claims(clean_text)

    # Use detected language as source for translation pipeline when available
    source_lang: str | None = None
    if isinstance(language_analysis, dict):
        lang_value = language_analysis.get("language")
        if isinstance(lang_value, str):
            source_lang = lang_value
            record_language(lang_value)

    enriched_claims = translate_and_canonicalize_claims(
        claims,
        source_language=source_lang,
    )

    # Retrieve multi-source evidence for each claim
    evidence_results = retrieve_evidence_for_claims(enriched_claims)

    # Prepare stance detection inputs for all (claim, evidence) pairs
    stance_inputs = []
    for claim, ev in zip(enriched_claims, evidence_results):
        claim_text = str(claim.get("text", ""))
        for ev_item in ev.get("evidence", []):
            snippet = str(ev_item.get("snippet", ""))
            stance_inputs.append({"claim": claim_text, "evidence": snippet})

    stances = classify_stance_batch(stance_inputs) if stance_inputs else []

    # Compute final veracity per claim
    veracity = classify_veracity(
        claims=enriched_claims,
        evidence_results=evidence_results,
        stances=stances,
    )

    result: Dict[str, Any] = {
        "payload": payload,
        "claims": enriched_claims,
        "evidence": evidence_results,
        "stances": stances,
        "veracity": veracity,
    }

    logger.info("Processed post payload", extra=result)

    # Store in cache for future identical claims
    set_cached_verdict(fingerprint, result)

    # Record verification time metric
    duration = time.monotonic() - start_time
    record_verification_time(duration)

    return result
