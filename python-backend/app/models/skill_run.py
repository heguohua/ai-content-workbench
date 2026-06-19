"""Skill 运行 ORM 模型"""

from sqlalchemy import Column, BigInteger, String, DateTime, SmallInteger, Text
from sqlalchemy.sql import func

from app.database import Base


class SkillRun(Base):
    """Skill 运行表"""

    __tablename__ = "skill_run"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="id")
    run_key = Column("runKey", String(64), nullable=False, unique=True, comment="运行唯一键")
    session_id = Column("sessionId", BigInteger, nullable=False, comment="所属会话 ID")
    parent_run_id = Column("parentRunId", BigInteger, nullable=True, comment="父运行 ID")
    skill_id = Column("skillId", String(128), nullable=False, comment="Skill ID")
    skill_kind = Column("skillKind", String(32), nullable=False, comment="Skill 类型")
    status = Column(String(32), nullable=False, comment="运行状态")
    input_json = Column("inputJson", Text, nullable=False, comment="输入 JSON")
    output_json = Column("outputJson", Text, nullable=True, comment="输出 JSON")
    context_json = Column("contextJson", Text, nullable=True, comment="上下文 JSON")
    error_message = Column("errorMessage", Text, nullable=True, comment="错误信息")
    started_at = Column("startedAt", DateTime, nullable=True, comment="开始时间")
    completed_at = Column("completedAt", DateTime, nullable=True, comment="完成时间")
    create_time = Column("createTime", DateTime, nullable=False, default=func.now(), comment="创建时间")
    update_time = Column("updateTime", DateTime, nullable=False, default=func.now(), onupdate=func.now(), comment="更新时间")
    is_delete = Column("isDelete", SmallInteger, nullable=False, default=0, comment="是否删除")
