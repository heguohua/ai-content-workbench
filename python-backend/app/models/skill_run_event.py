"""Skill 运行事件 ORM 模型"""

from sqlalchemy import Column, BigInteger, String, DateTime, Integer, SmallInteger, Text
from sqlalchemy.sql import func

from app.database import Base


class SkillRunEvent(Base):
    """Skill 运行事件表"""

    __tablename__ = "skill_run_event"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="id")
    event_key = Column("eventKey", String(64), nullable=False, unique=True, comment="事件唯一键")
    run_id = Column("runId", BigInteger, nullable=False, comment="所属运行 ID")
    event_type = Column("eventType", String(64), nullable=False, comment="事件类型")
    seq_no = Column("seqNo", Integer, nullable=False, comment="事件序号")
    payload_json = Column("payloadJson", Text, nullable=True, comment="事件载荷 JSON")
    create_time = Column("createTime", DateTime, nullable=False, default=func.now(), comment="创建时间")
    is_delete = Column("isDelete", SmallInteger, nullable=False, default=0, comment="是否删除")
