"""
同步数据库连接（供线程池查库使用）。

说明
----
FastAPI 主链路使用异步 SQLAlchemy（aiomysql）。
多线程场景下 AsyncSession 不能跨线程共享，因此在线程池内使用
独立的同步 Engine + Session（pymysql），每个线程各自开连接查库。
"""

from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.db.models.users import Users
from app.db.serializers import row_to_dict

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _sync_database_url(settings: Settings) -> str:
    """将异步驱动 URL 转为同步 pymysql URL。"""
    return settings.database_url.replace("mysql+aiomysql", "mysql+pymysql")


def get_sync_session_factory() -> sessionmaker[Session]:
    """懒加载同步 Session 工厂（线程池内每次 with factory() 独立连接）。"""
    global _engine, _session_factory
    if _session_factory is None:
        settings = get_settings()
        _engine = create_engine(
            _sync_database_url(settings),
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        _session_factory = sessionmaker(
            bind=_engine,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


def shutdown_sync_engine() -> None:
    """应用关闭时释放同步连接池。"""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


def query_user_by_id_sync(
    user_id: int,
    columns: list[str] | None = None,
) -> dict | None:
    """
    在线程内按 id 查用户。

    必须在 ThreadPoolExecutor 的工作线程中调用；
    每次调用独立 Session，保证线程安全。
    """
    factory = get_sync_session_factory()
    table = Users.__table__

    with factory() as session:
        if columns:
            stmt = select(*[table.c[col] for col in columns]).where(table.c.id == user_id)
        else:
            stmt = select(table).where(table.c.id == user_id)

        row = session.execute(stmt).mappings().first()
        return row_to_dict(row) if row else None
