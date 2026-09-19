import logging
import re
from contextvars import ContextVar, Token
from logging.handlers import RotatingFileHandler
from pathlib import Path
from uuid import uuid4

from app.config import Settings


TRACE_ID_HEADER = "X-Trace-ID"
_TRACE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="-")


def get_trace_id() -> str:
    """获取当前请求或任务的 trace id。"""
    return _trace_id_ctx.get()


def set_trace_id(trace_id: str) -> Token[str]:
    """设置当前上下文的 trace id，并返回用于恢复上下文的 token。"""
    return _trace_id_ctx.set(trace_id)


def reset_trace_id(token: Token[str]) -> None:
    """恢复设置 trace id 前的上下文。"""
    _trace_id_ctx.reset(token)


def resolve_trace_id(candidate: str | None) -> str:
    """使用合法的上游 trace id，否则生成新的 trace id。"""
    if candidate and _TRACE_ID_PATTERN.fullmatch(candidate):
        return candidate
    return uuid4().hex


class TraceIdFilter(logging.Filter):
    """将当前上下文的 trace id 注入每条日志。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id()
        return True


def setup_logging(settings: Settings) -> None:
    """初始化日志：控制台 + 文件（目录由 LOG_DIR 指定）。"""
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(trace_id)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    trace_filter = TraceIdFilter()

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.addFilter(trace_filter)
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        log_dir / settings.log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(trace_filter)
    root.addHandler(file_handler)

    # SQL 日志仅在 DEBUG 时输出，避免刷屏
    sqlalchemy_level = logging.INFO if settings.debug else logging.WARNING
    logging.getLogger("sqlalchemy.engine").setLevel(sqlalchemy_level)


def get_logger(name: str) -> logging.Logger:
    """获取模块 logger，用法: logger = get_logger(__name__)"""
    return logging.getLogger(name)
