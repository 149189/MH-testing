from fastapi import APIRouter

from api.routes import health  # type: ignore[import]

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
