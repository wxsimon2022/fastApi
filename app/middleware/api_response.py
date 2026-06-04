import json
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


SKIP_UNIFIED_PATHS = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}


class ApiResponseOrderMiddleware(BaseHTTPMiddleware):
    """将 API JSON 响应统一为 {code, data, message} 结构。"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        if request.url.path in SKIP_UNIFIED_PATHS:
            return response

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        body = b"".join([chunk async for chunk in response.body_iterator])
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        from app.responses import encode_api_body

        if isinstance(payload, dict) and "code" in payload:
            ordered = encode_api_body(
                payload["code"],
                payload.get("data"),
                payload.get("message", "ok"),
            )
        else:
            code = 0 if response.status_code < 400 else response.status_code
            ordered = encode_api_body(code, payload, "ok")

        headers = dict(response.headers)
        headers.pop("content-length", None)
        return Response(
            content=ordered,
            status_code=response.status_code,
            headers=headers,
            media_type="application/json",
        )
