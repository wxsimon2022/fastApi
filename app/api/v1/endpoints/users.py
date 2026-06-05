from fastapi import APIRouter

from app.core.exceptions import AppException
from app.db.deps import UserRepo
from app.schemas.common import ApiResponse, success

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/1", response_model=ApiResponse[dict])
async def get_user_one(repo: UserRepo) -> ApiResponse[dict]:
    """测试接口：查询用户表 id=1 的记录。"""
    user = await repo.get_by_id(1)
    if user is None:
        raise AppException("用户不存在", code=404)
    return success(data=user)


@router.get("/test", response_model=ApiResponse[dict], include_in_schema=False)
async def get_user_test(repo: UserRepo) -> ApiResponse[dict]:
    """兼容旧路径。"""
    return await get_user_one(repo)
