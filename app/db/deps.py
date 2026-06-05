from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import database
from app.db.repositories.user import UserRepository


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in database.session():
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_user_repository(session: DbSession) -> UserRepository:
    return UserRepository(session, database.users_table)


UserRepo = Annotated[UserRepository, Depends(get_user_repository)]
