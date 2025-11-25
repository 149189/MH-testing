from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter

from monitoring.metrics import get_metrics_snapshot

router = APIRouter(tags=["analytics"])


@router.get("/analytics")
async def get_analytics() -> Dict[str, Any]:
    """Return a snapshot of verification and review metrics.

    This is a lightweight, in-memory dashboard endpoint.
    """
    return get_metrics_snapshot()
