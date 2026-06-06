import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import Settings


def setup_logging(settings: Settings) -> None:
    """初始化日志：控制台 + 文件（目录由 LOG_DIR 指定）。"""
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        log_dir / settings.log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # SQL 日志仅在 DEBUG 时输出，避免刷屏
    sqlalchemy_level = logging.INFO if settings.debug else logging.WARNING
    logging.getLogger("sqlalchemy.engine").setLevel(sqlalchemy_level)


def get_logger(name: str) -> logging.Logger:
    """获取模块 logger，用法: logger = get_logger(__name__)"""
    return logging.getLogger(name)
