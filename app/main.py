from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.controllers.v1.router import api_router
from app.config import Settings, get_settings
from app.core.db_handlers import sqlalchemy_exception_handler
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.core.logging import get_logger, setup_logging
from app.db.database import database
from app.db.sync_database import shutdown_sync_engine
from app.redis.client import redis_client
from app.middleware.api_response import ApiResponseOrderMiddleware
from app.middleware.trace import TraceLoggingMiddleware
from app.schemas.common import ApiResponse, success


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logger.info("应用启动: %s v%s", settings.app_name, settings.app_version)
    logger.info("日志目录: %s/%s", settings.log_dir, settings.log_file)
    await database.startup(settings.database_url, echo=settings.debug)
    await redis_client.startup(settings.redis_url)
    routes = [getattr(r, "path", None) for r in app.routes if getattr(r, "path", None)]
    logger.info("已注册路由: %s", ", ".join(sorted(r for r in routes if r)))
    yield
    logger.info("应用关闭")
    await redis_client.shutdown()
    await database.shutdown()
    shutdown_sync_engine()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(ApiResponseOrderMiddleware)
    app.add_middleware(TraceLoggingMiddleware)

    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/", tags=["root"], response_model=ApiResponse[dict])
    async def root() -> ApiResponse[dict]:
        return success(data={"welcome": settings.app_name})

    return app


app = create_app()


def _init_logging() -> None:
    setup_logging(get_settings())


_init_logging()
logger = get_logger(__name__)
