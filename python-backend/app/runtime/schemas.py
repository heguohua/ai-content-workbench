"""Skill Runtime 内部模型"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class SkillDefinition(BaseModel):
    """Skill 定义"""

    id: str
    kind: Literal["project", "atomic"]
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


class SkillEvent(BaseModel):
    """Skill 事件"""

    type: str
    run_id: int = Field(..., alias="runId")
    skill_id: str = Field(..., alias="skillId")
    session_id: int = Field(..., alias="sessionId")
    data: dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True
