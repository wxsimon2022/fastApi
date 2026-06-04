from fastapi import APIRouter

from app.config import get_settings
from app.schemas.common import ApiResponse, success

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiResponse[dict])
async def health_check() -> ApiResponse[dict]:
    settings = get_settings()
    return success(
        data={
            "status": "ok",
            "app": settings.app_name,
            "version": settings.app_version,
        }
    )
