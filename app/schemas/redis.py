from pydantic import BaseModel, Field


class RedisSetBody(BaseModel):
    value: str = Field(..., min_length=1, description="缓存值")
    ttl: int | None = Field(None, ge=1, description="过期时间（秒），不传则永久")
