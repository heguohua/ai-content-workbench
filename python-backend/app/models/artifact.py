"""产物 ORM 模型"""

from sqlalchemy import Column, BigInteger, String, DateTime, Integer, SmallInteger, Text
from sqlalchemy.sql import func

from app.database import Base


class Artifact(Base):
    """产物表"""

    __tablename__ = "artifact"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="id")
    artifact_key = Column("artifactKey", String(64), nullable=False, unique=True, comment="产物唯一键")
    session_id = Column("sessionId", BigInteger, nullable=False, comment="所属会话 ID")
    source_run_id = Column("sourceRunId", BigInteger, nullable=True, comment="来源运行 ID")
    artifact_type = Column("artifactType", String(64), nullable=False, comment="产物类型")
    title = Column(String(256), nullable=False, comment="产物标题")
    version = Column(Integer, nullable=False, default=1, comment="版本号")
    status = Column(String(32), nullable=False, default="ACTIVE", comment="状态")
    content_json = Column("contentJson", Text, nullable=False, comment="产物内容 JSON")
    meta_json = Column("metaJson", Text, nullable=True, comment="元数据 JSON")
    create_time = Column("createTime", DateTime, nullable=False, default=func.now(), comment="创建时间")
    update_time = Column("updateTime", DateTime, nullable=False, default=func.now(), onupdate=func.now(), comment="更新时间")
    is_delete = Column("isDelete", SmallInteger, nullable=False, default=0, comment="是否删除")
