from app.db.models.messages import Messages
from app.db.repositories.base import BaseRepository


class MessageRepository(BaseRepository):
    """c_messages 数据访问。"""

    model = Messages

    # 列表 /all 接口默认返回字段，可按需修改
    ALL_LIST_COLUMNS = ["id", "conversation_id", "role", "content", "created_at"]
