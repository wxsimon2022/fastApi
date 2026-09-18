from datetime import datetime
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Conversations(Base):
    """c_conversations 表。"""

    __tablename__ = "c_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer)
    agent_name: Mapped[str] = mapped_column(String(32),comment="对话的代理人名称")
    thread_id: Mapped[str] = mapped_column(String(64),comment="对话的线程ID")
    title: Mapped[str] = mapped_column(String(128),comment="对话标题")
    created_at: Mapped[datetime] = mapped_column(DateTime,comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime,comment="更新时间")
