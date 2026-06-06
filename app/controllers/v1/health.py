from fastapi import APIRouter

from app.config import get_settings
from app.core.logging import get_logger
from app.schemas.common import ApiResponse, success

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


@router.get("/health", response_model=ApiResponse[dict])
async def health_check() -> ApiResponse[dict]:
    settings = get_settings()
    logger.info(
        "[服务正常]health check, app=%s version=%s",
        settings.app_name,
        settings.app_version,
    )
    return success(
        data={
            "status": "ok",
            "app": settings.app_name,
            "version": settings.app_version,
        }
    )
