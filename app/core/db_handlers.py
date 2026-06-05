from fastapi import Request
from sqlalchemy.exc import SQLAlchemyError

from app.responses import ApiJSONResponse, api_json


async def sqlalchemy_exception_handler(
    _: Request, exc: SQLAlchemyError
) -> ApiJSONResponse:
    detail = str(exc.orig) if exc.orig else str(exc)
    return api_json(code=500, data=detail, message="数据库操作失败")
