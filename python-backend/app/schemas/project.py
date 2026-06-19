"""项目相关请求/响应模型"""

from typing import Any, Optional

from pydantic import BaseModel, Field

from app.schemas.common import PageRequest


class ProjectCreateRequest(BaseModel):
    """创建项目请求"""

    name: str = Field(..., min_length=1, max_length=128, description="项目名称")
    description: Optional[str] = Field(None, max_length=512, description="项目描述")
    project_skill_id: str = Field(..., alias="projectSkillId", min_length=1, description="项目 Skill ID")
    config_json: Optional[dict[str, Any]] = Field(None, alias="configJson", description="项目配置")

    class Config:
        populate_by_name = True


class ProjectQueryRequest(PageRequest):
    """项目查询请求"""

    name: Optional[str] = Field(None, description="项目名称")
    project_skill_id: Optional[str] = Field(None, alias="projectSkillId", description="项目 Skill ID")
    status: Optional[str] = Field(None, description="状态")

    class Config:
        populate_by_name = True


class ProjectVO(BaseModel):
    """项目视图对象"""

    id: int
    project_key: str = Field(..., alias="projectKey")
    name: str
    description: Optional[str] = None
    project_skill_id: str = Field(..., alias="projectSkillId")
    owner_user_id: int = Field(..., alias="ownerUserId")
    status: str
    config_json: Optional[dict[str, Any]] = Field(None, alias="configJson")
    create_time: str = Field(..., alias="createTime")
    update_time: str = Field(..., alias="updateTime")

    class Config:
        populate_by_name = True
