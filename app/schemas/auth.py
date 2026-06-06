from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """登录请求体。"""

    username: str = Field(..., min_length=1, description="用户名")
    password: str = Field(..., min_length=1, description="明文密码")


class TokenData(BaseModel):
    """登录成功返回的 token 信息。"""

    access_token: str = Field(..., description="JWT，请求头：Authorization: Bearer <token>")
    token_type: str = Field("bearer", description="固定 bearer")
    expires_in: int = Field(..., description="有效秒数，与 Redis TTL 一致")
