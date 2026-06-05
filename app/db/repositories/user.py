from typing import Any

from sqlalchemy import Table, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.serializers import row_to_dict


class UserRepository:
    def __init__(self, session: AsyncSession, table: Table) -> None:
        self._session = session
        self._table = table

    async def get_by_id(self, user_id: int) -> dict[str, Any] | None:
        stmt = select(self._table).where(self._table.c.id == user_id)
        row = (await self._session.execute(stmt)).mappings().first()
        return row_to_dict(row) if row else None
