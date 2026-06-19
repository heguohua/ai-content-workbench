"""会话相关请求/响应模型"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    """创建会话请求"""

    project_id: int = Field(..., alias="projectId", description="项目 ID")
    title: str = Field(..., min_length=1, max_length=256, description="会话标题")
    meta_json: Optional[dict[str, Any]] = Field(None, alias="metaJson", description="附加信息")

    class Config:
        populate_by_name = True


class ChatSessionVO(BaseModel):
    """会话视图对象"""

    id: int
    session_key: str = Field(..., alias="sessionKey")
    project_id: int = Field(..., alias="projectId")
    title: str
    status: str
    last_message_at: Optional[str] = Field(None, alias="lastMessageAt")
    meta_json: Optional[dict[str, Any]] = Field(None, alias="metaJson")
    create_time: str = Field(..., alias="createTime")
    update_time: str = Field(..., alias="updateTime")

    class Config:
        populate_by_name = True


class ChatMessageVO(BaseModel):
    """消息视图对象"""

    id: int
    message_key: str = Field(..., alias="messageKey")
    session_id: int = Field(..., alias="sessionId")
    run_id: Optional[int] = Field(None, alias="runId")
    role: str
    message_type: str = Field(..., alias="messageType")
    content_text: Optional[str] = Field(None, alias="contentText")
    content_json: Optional[dict[str, Any]] = Field(None, alias="contentJson")
    status: str
    create_time: str = Field(..., alias="createTime")

    class Config:
        populate_by_name = True
