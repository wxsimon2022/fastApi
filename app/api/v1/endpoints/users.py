from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.db.tables import O_USERS
from app.db.session import get_db
from app.db.utils import serialize_row
from app.schemas.common import ApiResponse, success

router = APIRouter(prefix="/users", tags=["users"])


async def _get_user_by_id(db: AsyncSession, user_id: int) -> ApiResponse[dict]:
    try:
        result = await db.execute(
            text(f"SELECT * FROM `{O_USERS}` WHERE id = :id"),
            {"id": user_id},
        )
    except SQLAlchemyError as exc:
        raise AppException("数据库连接失败", code=500, data=str(exc.orig)) from exc

    row = result.mappings().first()
    if row is None:
        raise AppException("用户不存在", code=404)
    return success(data=serialize_row(row))


@router.get("/1", response_model=ApiResponse[dict])
async def get_user_one(db: AsyncSession = Depends(get_db)) -> ApiResponse[dict]:
    """测试接口：查询用户表 id=1 的记录。"""
    return await _get_user_by_id(db, 1)


@router.get("/test", response_model=ApiResponse[dict], include_in_schema=False)
async def get_user_test(db: AsyncSession = Depends(get_db)) -> ApiResponse[dict]:
    """兼容旧路径。"""
    return await _get_user_by_id(db, 1)
