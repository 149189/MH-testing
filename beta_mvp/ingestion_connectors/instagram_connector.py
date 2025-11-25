from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from . import enqueue_normalized_post
from ..utils.language_processor import process_text_for_ingestion


def build_instagram_payload(
    *,
    post_id: str,
    caption: Optional[str],
    comments: Optional[List[Dict[str, Any]]] = None,
    alt_text: Optional[str] = None,
    media_url: Optional[str] = None,
    media_type: Optional[str] = None,
    owner_id: Optional[str] = None,
    timestamp: Optional[str] = None,
    raw: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a normalized payload for an Instagram post or reel."""

    ts = timestamp or datetime.utcnow().isoformat() + "Z"
    raw_text = caption or ""
    lp = process_text_for_ingestion(raw_text)

    return {
        "platform": "instagram",
        "platform_message_id": post_id,
        "timestamp": ts,
        "author": {
            "id": owner_id,
        },
        "content": {
            "raw_text": raw_text,
            "alt_text": alt_text,
            "media_url": media_url,
            "media_type": media_type,
            "comments": comments or [],
        },
        "language_analysis": lp,
        "meta": {
            "raw": raw or {},
        },
    }


def ingest_instagram_post(
    *,
    post_id: str,
    caption: Optional[str],
    comments: Optional[List[Dict[str, Any]]] = None,
    alt_text: Optional[str] = None,
    media_url: Optional[str] = None,
    media_type: Optional[str] = None,
    owner_id: Optional[str] = None,
    timestamp: Optional[str] = None,
    raw: Optional[Dict[str, Any]] = None,
) -> None:
    """Public entrypoint for Instagram ingestion.

    Your Instagram Graph API webhook or poller should call this function.
    """
    payload = build_instagram_payload(
        post_id=post_id,
        caption=caption,
        comments=comments,
        alt_text=alt_text,
        media_url=media_url,
        media_type=media_type,
        owner_id=owner_id,
        timestamp=timestamp,
        raw=raw,
    )
    enqueue_normalized_post(payload)
    print(f"[Instagram] Enqueued post {post_id}")
