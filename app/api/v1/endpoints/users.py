from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import AppException
from app.db.session import get_db
from app.db.utils import serialize_row
from app.schemas.common import ApiResponse, success

router = APIRouter(tags=["users"])


@router.get("/users/test", response_model=ApiResponse[dict])
async def get_user_test(db: AsyncSession = Depends(get_db)) -> ApiResponse[dict]:
    """测试接口：查询用户表 id=1 的记录。"""
    settings = get_settings()
    result = await db.execute(
        text(f"SELECT * FROM `{settings.table_users}` WHERE id = :id"),
        {"id": 1},
    )
    row = result.mappings().first()
    if row is None:
        raise AppException("用户不存在", code=404)
    return success(data=serialize_row(row))
