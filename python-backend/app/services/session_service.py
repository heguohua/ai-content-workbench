"""会话服务"""

import json
import uuid
from datetime import datetime

from databases import Database
from sqlalchemy import and_, select

from app.exceptions import ErrorCode, throw_if_not
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.project import Project
from app.schemas.session import ChatMessageVO, ChatSessionVO, SessionCreateRequest
from app.schemas.user import LoginUserVO


class SessionService:
    """会话服务"""

    def __init__(self, db: Database):
        self.db = db

    async def create_session(self, request: SessionCreateRequest, current_user: LoginUserVO) -> ChatSessionVO:
        """创建会话"""
        project = await self.db.fetch_one(
            select(Project).where(
                and_(
                    Project.id == request.project_id,
                    Project.owner_user_id == current_user.id,
                    Project.is_delete == 0,
                )
            )
        )
        throw_if_not(project, ErrorCode.NOT_FOUND_ERROR, "项目不存在")

        now = datetime.now()
        session_key = f"sess_{uuid.uuid4().hex[:16]}"
        await self.db.execute(
            query="""
                INSERT INTO chat_session (
                    sessionKey, projectId, title, status, lastMessageAt, metaJson, createTime, updateTime, isDelete
                ) VALUES (
                    :sessionKey, :projectId, :title, :status, :lastMessageAt, :metaJson, :createTime, :updateTime, 0
                )
            """,
            values={
                "sessionKey": session_key,
                "projectId": request.project_id,
                "title": request.title,
                "status": "ACTIVE",
                "lastMessageAt": now,
                "metaJson": json.dumps(request.meta_json, ensure_ascii=False) if request.meta_json else None,
                "createTime": now,
                "updateTime": now,
            },
        )
        row = await self.db.fetch_one(select(ChatSession).where(and_(ChatSession.session_key == session_key, ChatSession.is_delete == 0)))
        return self._to_session_vo(row)

    async def get_session(self, session_id: int, current_user: LoginUserVO) -> ChatSessionVO:
        """获取会话"""
        row = await self._get_owned_session_row(session_id, current_user)
        return self._to_session_vo(row)

    async def list_messages(self, session_id: int, current_user: LoginUserVO) -> list[ChatMessageVO]:
        """获取消息列表"""
        await self._get_owned_session_row(session_id, current_user)
        rows = await self.db.fetch_all(
            select(ChatMessage)
            .where(and_(ChatMessage.session_id == session_id, ChatMessage.is_delete == 0))
            .order_by(ChatMessage.create_time.asc())
        )
        return [self._to_message_vo(row) for row in rows]

    async def touch_session(self, session_id: int, message_time: datetime):
        """刷新会话最近消息时间"""
        await self.db.execute(
            query="""
                UPDATE chat_session
                SET lastMessageAt = :lastMessageAt, updateTime = :updateTime
                WHERE id = :id AND isDelete = 0
            """,
            values={
                "id": session_id,
                "lastMessageAt": message_time,
                "updateTime": message_time,
            },
        )

    async def _get_owned_session_row(self, session_id: int, current_user: LoginUserVO):
        row = await self.db.fetch_one(
            query="""
                SELECT s.*
                FROM chat_session s
                JOIN project p ON s.projectId = p.id
                WHERE s.id = :sessionId
                  AND s.isDelete = 0
                  AND p.isDelete = 0
                  AND p.ownerUserId = :userId
            """,
            values={"sessionId": session_id, "userId": current_user.id},
        )
        throw_if_not(row, ErrorCode.NOT_FOUND_ERROR, "会话不存在")
        return row

    def _to_session_vo(self, row) -> ChatSessionVO:
        return ChatSessionVO(
            id=row["id"],
            sessionKey=row["sessionKey"],
            projectId=row["projectId"],
            title=row["title"],
            status=row["status"],
            lastMessageAt=row["lastMessageAt"].isoformat() if row["lastMessageAt"] else None,
            metaJson=json.loads(row["metaJson"]) if row["metaJson"] else None,
            createTime=row["createTime"].isoformat(),
            updateTime=row["updateTime"].isoformat(),
        )

    def _to_message_vo(self, row) -> ChatMessageVO:
        return ChatMessageVO(
            id=row["id"],
            messageKey=row["messageKey"],
            sessionId=row["sessionId"],
            runId=row["runId"],
            role=row["role"],
            messageType=row["messageType"],
            contentText=row["contentText"],
            contentJson=json.loads(row["contentJson"]) if row["contentJson"] else None,
            status=row["status"],
            createTime=row["createTime"].isoformat(),
        )
