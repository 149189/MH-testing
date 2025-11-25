from __future__ import annotations

from typing import Any, Dict, List, Literal, Tuple

StanceLabel = Literal["support", "refute", "neutral"]


def _stance_weight(stance: StanceLabel) -> float:
    if stance == "support":
        return 1.0
    if stance == "refute":
        return -1.0
    return 0.0


def _aggregate_score(
    stances: List[Dict[str, Any]],
    evidences: List[Dict[str, Any]],
) -> Tuple[float, float, List[Dict[str, Any]]]:
    """Compute weighted score and selected evidence.

    We assume stances and evidences are aligned over evidence items.
    Returns (score, abs_score_for_confidence, evidence_used).
    """
    total = 0.0
    weight_sum = 0.0
    evidence_used: List[Dict[str, Any]] = []

    for stance, ev in zip(stances, evidences):
        s_label = stance.get("stance", "neutral")
        s_conf = float(stance.get("confidence", 0.0))
        s_w = _stance_weight(s_label) * s_conf

        src_cred = float(ev.get("source_credibility", 0.0))
        recency = float(ev.get("recency_score", 0.0))

        # Combine credibility and recency (simple average for now)
        src_weight = 0.5 * src_cred + 0.5 * recency

        contribution = s_w * src_weight
        total += contribution
        weight_sum += abs(contribution)

        if s_label != "neutral":
            evidence_used.append(ev)

    confidence = min(1.0, weight_sum) if weight_sum > 0 else 0.0
    return total, confidence, evidence_used


def _verdict_from_score(score: float) -> str:
    if score >= 0.6:
        return "Likely True"
    if score <= -0.6:
        return "Likely False"
    return "Unverified"


def classify_veracity(
    *,
    claims: List[Dict[str, Any]],
    evidence_results: List[Dict[str, Any]],
    stances: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Compute final veracity per claim.

    We expect:
      - claims: list of enriched claim dicts
      - evidence_results: [{"claim_id": ..., "evidence": [e1, e2, ...]}, ...]
      - stances: flat list corresponding to all (claim, evidence) pairs in
        the same nested iteration order used by the pipeline.

    Returns one object per claim:
    {
      "claim_id": "...",
      "verdict": "Likely True|Likely False|Unverified",
      "score": float,
      "confidence": float,
      "explanation": str,
      "evidence_used": [evidence_json,...],
    }
    """
    results: List[Dict[str, Any]] = []

    # Pointer into flat stance list
    stance_idx = 0

    for claim, ev_block in zip(claims, evidence_results):
        cid = str(claim.get("claim_id", ""))
        ev_list = ev_block.get("evidence", []) or []
        n = len(ev_list)

        block_stances = stances[stance_idx : stance_idx + n]
        stance_idx += n

        score, conf, evidence_used = _aggregate_score(block_stances, ev_list)
        verdict = _verdict_from_score(score)

        explanation = (
            f"Aggregated stance from {len(ev_list)} evidence items. "
            f"Score {score:.3f} mapped to verdict '{verdict}'."
        )

        results.append(
            {
                "claim_id": cid,
                "verdict": verdict,
                "score": float(score),
                "confidence": float(conf),
                "explanation": explanation,
                "evidence_used": evidence_used,
            }
        )

    return results
