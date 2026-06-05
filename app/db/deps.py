from collections.abc import AsyncGenerator, Callable
from typing import Annotated, TypeVar

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.schema import Table

from app.db.database import database
from app.db.repositories.base import BaseRepository
from app.db.repositories.user import UserRepository

TRepo = TypeVar("TRepo", bound=BaseRepository)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in database.session():
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]


def repository_factory(
    repo_class: type[TRepo],
    table_getter: Callable[[], Table],
) -> Callable[..., TRepo]:
    def _get_repository(session: DbSession) -> TRepo:
        return repo_class(session, table_getter())

    return _get_repository


get_user_repository = repository_factory(UserRepository, lambda: database.users_table)
UserRepo = Annotated[UserRepository, Depends(get_user_repository)]
