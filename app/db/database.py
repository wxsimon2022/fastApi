from collections.abc import AsyncGenerator

from sqlalchemy import MetaData, Table
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.tables import USERS


class Database:
    """异步数据库组件：管理连接池、Session 与表元数据。"""

    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        self._metadata = MetaData()
        self._users_table: Table | None = None

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError("数据库未初始化，请先调用 database.startup()")
        return self._engine

    @property
    def users_table(self) -> Table:
        if self._users_table is None:
            raise RuntimeError("用户表元数据未加载")
        return self._users_table

    async def startup(self, url: str, *, echo: bool = False) -> None:
        self._engine = create_async_engine(
            url,
            echo=echo,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        await self._reflect_tables()

    async def shutdown(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
        self._engine = None
        self._session_factory = None
        self._users_table = None
        self._metadata = MetaData()

    async def _reflect_tables(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(
                lambda sync_conn: self._metadata.reflect(
                    bind=sync_conn,
                    only=[USERS],
                )
            )
        self._users_table = self._metadata.tables[USERS]

    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        if self._session_factory is None:
            raise RuntimeError("数据库未初始化，请先调用 database.startup()")
        async with self._session_factory() as session:
            yield session


database = Database()
