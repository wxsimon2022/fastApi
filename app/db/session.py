from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(database_url: str, *, echo: bool = False) -> None:
    global _engine, _session_factory
    _engine = create_async_engine(database_url, echo=echo)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def close_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if _session_factory is None:
        raise RuntimeError("数据库未初始化，请检查 DATABASE_URL 配置")
    async with _session_factory() as session:
        yield session
