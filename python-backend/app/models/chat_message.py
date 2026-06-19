"""消息 ORM 模型"""

from sqlalchemy import Column, BigInteger, String, DateTime, SmallInteger, Text
from sqlalchemy.sql import func

from app.database import Base


class ChatMessage(Base):
    """聊天消息表"""

    __tablename__ = "chat_message"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="id")
    message_key = Column("messageKey", String(64), nullable=False, unique=True, comment="消息唯一键")
    session_id = Column("sessionId", BigInteger, nullable=False, comment="所属会话 ID")
    run_id = Column("runId", BigInteger, nullable=True, comment="关联运行 ID")
    role = Column(String(32), nullable=False, comment="消息角色")
    message_type = Column("messageType", String(32), nullable=False, comment="消息类型")
    content_text = Column("contentText", Text, nullable=True, comment="文本内容")
    content_json = Column("contentJson", Text, nullable=True, comment="结构化内容 JSON")
    status = Column(String(32), nullable=False, default="COMPLETED", comment="消息状态")
    create_time = Column("createTime", DateTime, nullable=False, default=func.now(), comment="创建时间")
    update_time = Column("updateTime", DateTime, nullable=False, default=func.now(), onupdate=func.now(), comment="更新时间")
    is_delete = Column("isDelete", SmallInteger, nullable=False, default=0, comment="是否删除")
