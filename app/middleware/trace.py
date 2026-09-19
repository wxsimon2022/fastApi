from time import perf_counter

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import (
    TRACE_ID_HEADER,
    get_logger,
    reset_trace_id,
    resolve_trace_id,
    set_trace_id,
)


logger = get_logger(__name__)


class TraceLoggingMiddleware:
    """为每个 HTTP 请求建立日志链路并透传 trace id。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        candidate = headers.get(TRACE_ID_HEADER) or headers.get("X-Request-ID")
        trace_id = resolve_trace_id(candidate)
        token = set_trace_id(trace_id)
        scope.setdefault("state", {})["trace_id"] = trace_id

        method = scope["method"]
        path = scope["path"]
        status_code = 500
        started_at = perf_counter()

        async def send_with_trace(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)[TRACE_ID_HEADER] = trace_id
            await send(message)

        logger.info("请求开始 method=%s path=%s", method, path)
        try:
            await self.app(scope, receive, send_with_trace)
        except Exception:
            logger.exception("请求异常 method=%s path=%s", method, path)
            raise
        else:
            duration_ms = (perf_counter() - started_at) * 1000
            logger.info(
                "请求完成 method=%s path=%s status=%s duration_ms=%.2f",
                method,
                path,
                status_code,
                duration_ms,
            )
        finally:
            reset_trace_id(token)
