from datetime import datetime

from pydantic import BaseModel, Field


class MessagesUpdate(BaseModel):
    """更新 c_messages 表，仅传需要修改的字段。"""

    conversation_id: int | None = Field(None)
    role: str | None = Field(None, min_length=1)
    content: str | None = Field(None, min_length=1)
    created_at: datetime | None = Field(None)
