"""项目 ORM 模型"""

from sqlalchemy import Column, BigInteger, String, DateTime, SmallInteger, Text
from sqlalchemy.sql import func

from app.database import Base


class Project(Base):
    """AI 项目表"""

    __tablename__ = "project"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="id")
    project_key = Column("projectKey", String(64), nullable=False, unique=True, comment="项目唯一键")
    name = Column(String(128), nullable=False, comment="项目名称")
    description = Column(String(512), nullable=True, comment="项目描述")
    project_skill_id = Column("projectSkillId", String(128), nullable=False, comment="项目 Skill ID")
    owner_user_id = Column("ownerUserId", BigInteger, nullable=False, comment="所属用户 ID")
    status = Column(String(32), nullable=False, default="ACTIVE", comment="状态")
    config_json = Column("configJson", Text, nullable=True, comment="项目配置 JSON")
    create_time = Column("createTime", DateTime, nullable=False, default=func.now(), comment="创建时间")
    update_time = Column("updateTime", DateTime, nullable=False, default=func.now(), onupdate=func.now(), comment="更新时间")
    is_delete = Column("isDelete", SmallInteger, nullable=False, default=0, comment="是否删除")
