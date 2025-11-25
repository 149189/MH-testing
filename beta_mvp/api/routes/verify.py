from __future__ import annotations

from typing import Any, Dict, List, Optional

from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from celery_app import celery_app

router = APIRouter(tags=["verify"])


class MediaItem(BaseModel):
    type: str = Field(..., description="Type of media, e.g. image, video, audio")
    url: Optional[str] = Field(None, description="Public or fetchable URL to the media")


class VerifyRequest(BaseModel):
    platform: str = Field(..., description="Source platform, e.g. discord, telegram, instagram")
    text: str = Field(..., min_length=1, description="User-visible text content to verify")
    media: List[MediaItem] = Field(default_factory=list, description="Optional media items")


class VerifyTaskCreated(BaseModel):
    task_id: str


class VerifyStatus(BaseModel):
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/verify", response_model=VerifyTaskCreated)
async def create_verification(request: VerifyRequest) -> VerifyTaskCreated:
    # Build a minimal payload compatible with process_post
    payload: Dict[str, Any] = {
        "platform": request.platform,
        "content": {
            "raw_text": request.text,
            "media": [m.dict() for m in request.media],
        },
    }

    task = celery_app.send_task("process_post", args=[payload])
    return VerifyTaskCreated(task_id=task.id)


@router.get("/verify/{task_id}", response_model=VerifyStatus)
async def get_verification(task_id: str) -> VerifyStatus:
    result = AsyncResult(task_id, app=celery_app)

    if result.failed():
        # Include a safe string representation of the error
        return VerifyStatus(status="FAILURE", error=str(result.result))

    if not result.ready():
        return VerifyStatus(status=result.status)

    value = result.result
    if not isinstance(value, dict):
        # Unexpected result type from Celery task
        raise HTTPException(status_code=500, detail="Task returned unexpected result format")

    return VerifyStatus(status="SUCCESS", result=value)
