from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.config import Settings, get_settings
from app.core.db_handlers import sqlalchemy_exception_handler
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.db.database import database
from app.middleware.api_response import ApiResponseOrderMiddleware
from app.schemas.common import ApiResponse, success


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    await database.startup(settings.database_url, echo=settings.debug)
    routes = [getattr(r, "path", None) for r in app.routes if getattr(r, "path", None)]
    print(f"[{settings.app_name}] 已注册路由: {', '.join(sorted(r for r in routes if r))}")
    yield
    await database.shutdown()


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
