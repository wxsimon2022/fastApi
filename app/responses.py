import json
from typing import Any

from starlette.responses import Response

from app.schemas.common import api_body


def encode_api_body(code: int, data: Any = None, message: str = "ok") -> bytes:
    """按 code → data → message 顺序序列化为 JSON 字节。"""
    return json.dumps(
        api_body(code, data, message),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


class ApiJSONResponse(Response):
    media_type = "application/json"

    def __init__(
        self,
        code: int = 0,
        data: Any = None,
        message: str = "ok",
        status_code: int = 200,
    ) -> None:
        super().__init__(
            content=encode_api_body(code, data, message),
            status_code=status_code,
            media_type="application/json",
        )


def api_json(
    code: int = 0,
    data: Any = None,
    message: str = "ok",
    status_code: int = 200,
) -> ApiJSONResponse:
    return ApiJSONResponse(code=code, data=data, message=message, status_code=status_code)
