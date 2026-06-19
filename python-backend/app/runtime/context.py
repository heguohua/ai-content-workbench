"""Skill 上下文"""

import json
import asyncio
import uuid
from datetime import datetime
from typing import Any, Awaitable, Callable, Optional

from databases import Database

from app.runtime.schemas import SkillEvent
from app.services.artifact_service import ArtifactService
from app.services.session_service import SessionService


class ArtifactContext:
    """产物上下文"""

    def __init__(self, db: Database, session_id: int, run_id: Optional[int]):
        self.db = db
        self.session_id = session_id
        self.run_id = run_id
        self.service = ArtifactService(db)

    async def upsert(self, artifact_type: str, title: str, content: dict[str, Any]):
        """按类型更新或创建产物"""
        return await self.service.upsert_by_session_and_type(
            session_id=self.session_id,
            artifact_type=artifact_type,
            title=title,
            content_json=content,
            source_run_id=self.run_id,
        )


class SkillContext:
    """Skill 执行上下文"""

    def __init__(
        self,
        db: Database,
        session_id: int,
        run_id: int,
        skill_id: str,
        current_user,
        event_publisher: Optional[Callable[[SkillEvent], Awaitable[None]]] = None,
    ):
        self.db = db
        self.session_id = session_id
        self.run_id = run_id
        self.skill_id = skill_id
        self.current_user = current_user
        self._event_publisher = event_publisher
        self._pending_event_tasks: set[asyncio.Task] = set()
        self._last_event_task: Optional[asyncio.Task] = None
        self.artifacts = ArtifactContext(db, session_id, run_id)
        self.session_service = SessionService(db)

    def set_event_publisher(self, event_publisher: Callable[[SkillEvent], Awaitable[None]]):
        """绑定事件发布器，让原子 Skill 也能实时输出。"""
        self._event_publisher = event_publisher

    def event(self, event_type: str, data: dict[str, Any]) -> SkillEvent:
        """构建事件"""
        return SkillEvent(
            type=event_type,
            runId=self.run_id,
            skillId=self.skill_id,
            sessionId=self.session_id,
            data=data,
        )

    async def emit(self, event_type: str, data: dict[str, Any]):
        """立即发布事件，用于原子 Skill 内部流式输出。"""
        if not self._event_publisher:
            return
        await self._event_publisher(self.event(event_type, data))

    def emit_nowait(self, event_type: str, data: dict[str, Any]):
        """在同步回调里安全地排队发布事件。"""
        if not self._event_publisher:
            return

        async def publish_after_previous(previous_task: Optional[asyncio.Task]):
            if previous_task:
                await previous_task
            await self.emit(event_type, data)

        task = asyncio.create_task(publish_after_previous(self._last_event_task))
        self._last_event_task = task
        self._pending_event_tasks.add(task)
        task.add_done_callback(self._pending_event_tasks.discard)

    async def flush_events(self):
        """等待已排队事件写入，避免最终产物先于流式片段到达。"""
        while self._pending_event_tasks:
            tasks = list(self._pending_event_tasks)
            await asyncio.gather(*tasks, return_exceptions=True)

    async def call_skill(self, skill_id: str, input_data: dict[str, Any]) -> dict[str, Any]:
        """调用原子 Skill"""
        from app.runtime.registry import skill_registry

        skill = skill_registry.get(skill_id)
        result = await skill.execute(self, input_data)
        await self.flush_events()
        return result

    async def add_message(
        self,
        role: str,
        message_type: str,
        content_text: Optional[str] = None,
        content_json: Optional[dict[str, Any]] = None,
    ):
        """追加消息"""
        now = datetime.now()
        await self.db.execute(
            query="""
                INSERT INTO chat_message (
                    messageKey, sessionId, runId, role, messageType, contentText, contentJson, status, createTime, updateTime
                ) VALUES (
                    :messageKey, :sessionId, :runId, :role, :messageType, :contentText, :contentJson, :status, :createTime, :updateTime
                )
            """,
            values={
                "messageKey": str(uuid.uuid4()),
                "sessionId": self.session_id,
                "runId": self.run_id,
                "role": role,
                "messageType": message_type,
                "contentText": content_text,
                "contentJson": json.dumps(content_json, ensure_ascii=False) if content_json is not None else None,
                "status": "COMPLETED",
                "createTime": now,
                "updateTime": now,
            },
        )
        await self.session_service.touch_session(self.session_id, now)
