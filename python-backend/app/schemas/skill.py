"""Skill 相关请求/响应模型"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class SkillRunCreateRequest(BaseModel):
    """创建 Skill 运行请求"""

    session_id: int = Field(..., alias="sessionId", description="会话 ID")
    skill_id: str = Field(..., alias="skillId", min_length=1, description="Skill ID")
    input: dict[str, Any] = Field(..., description="输入参数")

    class Config:
        populate_by_name = True


class SkillRunActionRequest(BaseModel):
    """继续 Skill 运行请求"""

    action: str = Field(..., min_length=1, description="动作类型")
    payload: dict[str, Any] = Field(..., description="动作载荷")


class SkillDefinitionVO(BaseModel):
    """Skill 定义"""

    id: str
    kind: str
    name: str
    version: str
    description: str
    input_schema: dict[str, Any] = Field(..., alias="inputSchema")
    output_schema: dict[str, Any] = Field(..., alias="outputSchema")
    artifact_types: list[str] = Field(default_factory=list, alias="artifactTypes")
    interruptible: bool = True
    streamable: bool = True
    tags: list[str] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class SkillRunVO(BaseModel):
    """Skill 运行视图对象"""

    id: int
    run_key: str = Field(..., alias="runKey")
    session_id: int = Field(..., alias="sessionId")
    parent_run_id: Optional[int] = Field(None, alias="parentRunId")
    skill_id: str = Field(..., alias="skillId")
    skill_kind: str = Field(..., alias="skillKind")
    status: str
    input_json: dict[str, Any] = Field(..., alias="inputJson")
    output_json: Optional[dict[str, Any]] = Field(None, alias="outputJson")
    context_json: Optional[dict[str, Any]] = Field(None, alias="contextJson")
    error_message: Optional[str] = Field(None, alias="errorMessage")
    started_at: Optional[str] = Field(None, alias="startedAt")
    completed_at: Optional[str] = Field(None, alias="completedAt")
    create_time: str = Field(..., alias="createTime")
    update_time: str = Field(..., alias="updateTime")

    class Config:
        populate_by_name = True
