from __future__ import annotations

from typing import Any, Dict

from ..celery_app import celery_app


def enqueue_normalized_post(payload: Dict[str, Any]) -> None:
    """Send a normalized payload to the `process_post` Celery task."""
    celery_app.send_task("process_post", args=[payload])
