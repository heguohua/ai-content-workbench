"""产物相关请求/响应模型"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ArtifactUpdateRequest(BaseModel):
    """更新产物请求"""

    title: Optional[str] = Field(None, max_length=256, description="产物标题")
    content_json: dict[str, Any] = Field(..., alias="contentJson", description="产物内容")
    meta_json: Optional[dict[str, Any]] = Field(None, alias="metaJson", description="元数据")

    class Config:
        populate_by_name = True


class ArtifactVO(BaseModel):
    """产物视图对象"""

    id: int
    artifact_key: str = Field(..., alias="artifactKey")
    session_id: int = Field(..., alias="sessionId")
    source_run_id: Optional[int] = Field(None, alias="sourceRunId")
    artifact_type: str = Field(..., alias="artifactType")
    title: str
    version: int
    status: str
    content_json: dict[str, Any] = Field(..., alias="contentJson")
    meta_json: Optional[dict[str, Any]] = Field(None, alias="metaJson")
    create_time: str = Field(..., alias="createTime")
    update_time: str = Field(..., alias="updateTime")

    class Config:
        populate_by_name = True
