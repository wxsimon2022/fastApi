from collections.abc import AsyncGenerator
from typing import Annotated, TypeVar

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import database
from app.db.repositories.base import BaseRepository
from app.db.repositories.user import UserRepository
from app.db.repositories.messages import MessageRepository

TRepo = TypeVar("TRepo", bound=BaseRepository)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in database.session():
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]


def repository_factory(repo_class: type[TRepo]):
    def _get_repository(session: DbSession) -> TRepo:
        return repo_class(session)

    return _get_repository


get_user_repository = repository_factory(UserRepository)
UserRepo = Annotated[UserRepository, Depends(get_user_repository)]

get_message_repository = repository_factory(MessageRepository)
MessageRepo = Annotated[MessageRepository, Depends(get_message_repository)]
