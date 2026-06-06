from datetime import datetime
from pydantic import BaseModel, Field


class ConversationsUpdate(BaseModel):
    """更新 c_conversations 表，仅传需要修改的字段。"""

    user_id: int | None = Field(None)
    agent_name: str | None = Field(None, min_length=1)
    thread_id: str | None = Field(None, min_length=1)
    title: str | None = Field(None, min_length=1)
    created_at: datetime | None = Field(None)
    updated_at: datetime | None = Field(None)
