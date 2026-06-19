"""会话 ORM 模型"""

from sqlalchemy import Column, BigInteger, String, DateTime, SmallInteger, Text
from sqlalchemy.sql import func

from app.database import Base


class ChatSession(Base):
    """聊天会话表"""

    __tablename__ = "chat_session"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="id")
    session_key = Column("sessionKey", String(64), nullable=False, unique=True, comment="会话唯一键")
    project_id = Column("projectId", BigInteger, nullable=False, comment="所属项目 ID")
    title = Column(String(256), nullable=False, comment="会话标题")
    status = Column(String(32), nullable=False, default="ACTIVE", comment="状态")
    last_message_at = Column("lastMessageAt", DateTime, nullable=True, comment="最后消息时间")
    meta_json = Column("metaJson", Text, nullable=True, comment="附加信息 JSON")
    create_time = Column("createTime", DateTime, nullable=False, default=func.now(), comment="创建时间")
    update_time = Column("updateTime", DateTime, nullable=False, default=func.now(), onupdate=func.now(), comment="更新时间")
    is_delete = Column("isDelete", SmallInteger, nullable=False, default=0, comment="是否删除")
