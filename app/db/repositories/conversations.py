from app.db.models.conversations import Conversations
from app.db.repositories.base import BaseRepository


class ConversationRepository(BaseRepository):
    """c_conversations 数据访问。"""

    model = Conversations

    # 列表查询默认返回字段，可按需修改
    ALL_LIST_COLUMNS = ["id", "user_id", "agent_name", "thread_id", "title"]
