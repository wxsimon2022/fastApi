from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.responses import ApiJSONResponse, api_json


class AppException(Exception):
    def __init__(self, message: str, code: int = 400, data: Any = None):
        self.message = message
        self.code = code
        self.data = data
        super().__init__(message)


async def app_exception_handler(_: Request, exc: AppException) -> ApiJSONResponse:
    return api_json(code=exc.code, data=exc.data, message=exc.message)


async def validation_exception_handler(
    _: Request, exc: RequestValidationError
) -> ApiJSONResponse:
    return api_json(code=422, data=exc.errors(), message="参数校验失败")


async def http_exception_handler(
    _: Request, exc: StarletteHTTPException
) -> ApiJSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return api_json(code=exc.status_code, data=None, message=detail)
