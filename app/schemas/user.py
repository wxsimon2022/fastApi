from pydantic import BaseModel, Field


class UserUpdate(BaseModel):
    """更新 c_users 表，仅传需要修改的字段。"""

    username: str | None = Field(None, min_length=1, max_length=64)
    is_admin: int | None = Field(None, ge=0, le=1)
    password_hash: str | None = Field(None, min_length=1, description="密码哈希，生产环境应走加密逻辑")
