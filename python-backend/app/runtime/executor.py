"""Skill 执行器"""

import asyncio
import json
import uuid
from datetime import datetime

from databases import Database

from app.exceptions import ErrorCode, throw_if_not
from app.managers.sse_manager import sse_emitter_manager
from app.runtime.context import SkillContext
from app.runtime.registry import skill_registry
from app.schemas.skill import SkillRunVO
from app.services.session_service import SessionService


class SkillExecutor:
    """Skill 执行器"""

    def __init__(self):
        self._run_locks: dict[int, asyncio.Lock] = {}

    async def execute(self, db: Database, session_id: int, skill_id: str, input_data: dict, current_user) -> SkillRunVO:
        """启动运行"""
        session_service = SessionService(db)
        await session_service.get_session(session_id, current_user)
        skill = skill_registry.get(skill_id)
        now = datetime.now()
        run_key = f"run_{uuid.uuid4().hex[:16]}"
        run_id = await db.execute(
            query="""
                INSERT INTO skill_run (
                    runKey, sessionId, parentRunId, skillId, skillKind, status, inputJson, outputJson, contextJson,
                    errorMessage, startedAt, completedAt, createTime, updateTime, isDelete
                ) VALUES (
                    :runKey, :sessionId, NULL, :skillId, :skillKind, :status, :inputJson, NULL, NULL,
                    NULL, :startedAt, NULL, :createTime, :updateTime, 0
                )
            """,
            values={
                "runKey": run_key,
                "sessionId": session_id,
                "skillId": skill.definition.id,
                "skillKind": skill.definition.kind,
                "status": "RUNNING",
                "inputJson": json.dumps(input_data, ensure_ascii=False),
                "startedAt": now,
                "createTime": now,
                "updateTime": now,
            },
        )
        ctx = SkillContext(db, session_id, run_id, skill.definition.id, current_user)
        ctx.set_event_publisher(lambda event: self._persist_event(db, run_id, event))
        await ctx.add_message("user", "text", content_text=input_data.get("topic") or "启动项目")
        asyncio.create_task(self._run_skill(db, run_id, skill, ctx, input_data))
        row = await db.fetch_one("SELECT * FROM skill_run WHERE id = :id", {"id": run_id})
        return self._to_vo(row)

    async def resume(self, db: Database, run_id: int, action: str, payload: dict, current_user) -> SkillRunVO:
        """继续运行"""
        run_row = await db.fetch_one("SELECT * FROM skill_run WHERE id = :id AND isDelete = 0", {"id": run_id})
        throw_if_not(run_row, ErrorCode.NOT_FOUND_ERROR, "运行不存在")
        throw_if_not(
            run_row["status"] == "WAITING_INPUT",
            ErrorCode.OPERATION_ERROR,
            "当前运行不在等待输入状态",
        )
        session_service = SessionService(db)
        await session_service.get_session(run_row["sessionId"], current_user)
        skill = skill_registry.get(run_row["skillId"])
        ctx = SkillContext(db, run_row["sessionId"], run_id, run_row["skillId"], current_user)
        ctx.set_event_publisher(lambda event: self._persist_event(db, run_id, event))
        await ctx.add_message("user", "action", content_json={"action": action, "payload": payload})
        await db.execute(
            query="UPDATE skill_run SET status = :status, updateTime = :updateTime WHERE id = :id",
            values={"id": run_id, "status": "RUNNING", "updateTime": datetime.now()},
        )
        asyncio.create_task(self._resume_skill(db, run_id, skill, ctx, action, payload))
        row = await db.fetch_one("SELECT * FROM skill_run WHERE id = :id", {"id": run_id})
        return self._to_vo(row)

    def create_stream(self, run_id: int, current_user):
        """创建 SSE 流"""
        return sse_emitter_manager.create_emitter(
            f"skill_run_{run_id}",
            replay_messages=self._load_replay_messages,
            close_after_replay=self._should_close_after_replay,
        )

    async def _run_skill(self, db: Database, run_id: int, skill, ctx: SkillContext, input_data: dict):
        """后台执行 Skill"""
        try:
            async for event in skill.run(ctx, input_data):
                await self._persist_event(db, run_id, event)
            await ctx.flush_events()
        except Exception as exc:
            await self._persist_event(db, run_id, ctx.event("run.failed", {"message": str(exc)}))
        finally:
            if not self._run_locks.get(run_id, asyncio.Lock()).locked():
                self._run_locks.pop(run_id, None)

    async def _resume_skill(self, db: Database, run_id: int, skill, ctx: SkillContext, action: str, payload: dict):
        """后台继续执行 Skill"""
        try:
            async for event in skill.resume(ctx, action, payload):
                await self._persist_event(db, run_id, event)
            await ctx.flush_events()
        except Exception as exc:
            await self._persist_event(db, run_id, ctx.event("run.failed", {"message": str(exc)}))
        finally:
            if not self._run_locks.get(run_id, asyncio.Lock()).locked():
                self._run_locks.pop(run_id, None)

    async def _load_replay_messages(self, task_id: str) -> list[str]:
        """读取已持久化事件，用于 SSE 连接后回放。"""
        try:
            run_id = int(task_id.replace("skill_run_", ""))
        except ValueError:
            return []
        from app.database import database

        rows = await database.fetch_all(
            query="""
                SELECT payloadJson
                FROM skill_run_event
                WHERE runId = :runId AND isDelete = 0
                ORDER BY seqNo ASC
            """,
            values={"runId": run_id},
        )
        return [row["payloadJson"] for row in rows if row["payloadJson"]]

    async def _should_close_after_replay(self, task_id: str) -> bool:
        """终态 run 回放完历史事件后直接关闭连接。"""
        try:
            run_id = int(task_id.replace("skill_run_", ""))
        except ValueError:
            return True
        from app.database import database

        status = await database.fetch_val(
            query="SELECT status FROM skill_run WHERE id = :runId AND isDelete = 0",
            values={"runId": run_id},
        )
        return status in {"COMPLETED", "FAILED"}

    async def _persist_event(self, db: Database, run_id: int, event):
        """持久化并推送事件"""
        lock = self._run_locks.setdefault(run_id, asyncio.Lock())
        async with lock:
            seq_no = await db.fetch_val(
                "SELECT COALESCE(MAX(seqNo), 0) + 1 FROM skill_run_event WHERE runId = :runId AND isDelete = 0",
                {"runId": run_id},
            )
            await db.execute(
                query="""
                    INSERT INTO skill_run_event (
                        eventKey, runId, eventType, seqNo, payloadJson, createTime, isDelete
                    ) VALUES (
                        :eventKey, :runId, :eventType, :seqNo, :payloadJson, :createTime, 0
                    )
                """,
                values={
                    "eventKey": f"evt_{uuid.uuid4().hex[:16]}",
                    "runId": run_id,
                    "eventType": event.type,
                    "seqNo": seq_no,
                    "payloadJson": event.model_dump_json(by_alias=True, exclude_none=True),
                    "createTime": datetime.now(),
                },
            )
            await self._persist_event_message(db, event)
            status_map = {
                "run.waiting_input": "WAITING_INPUT",
                "run.completed": "COMPLETED",
                "run.failed": "FAILED",
            }
            if event.type in status_map:
                output_json = event.data.get("output") if event.type == "run.completed" else None
                await db.execute(
                    query="""
                        UPDATE skill_run
                        SET status = :status,
                            outputJson = COALESCE(:outputJson, outputJson),
                            errorMessage = :errorMessage,
                            completedAt = :completedAt,
                            updateTime = :updateTime
                        WHERE id = :id
                    """,
                    values={
                        "id": run_id,
                        "status": status_map[event.type],
                        "outputJson": json.dumps(output_json, ensure_ascii=False) if output_json is not None else None,
                        "errorMessage": event.data.get("message") if event.type == "run.failed" else None,
                        "completedAt": datetime.now() if event.type in {"run.completed", "run.failed"} else None,
                        "updateTime": datetime.now(),
                    },
                )
            sse_emitter_manager.send(f"skill_run_{run_id}", event.model_dump_json(by_alias=True))
            if event.type in {"run.completed", "run.failed"}:
                sse_emitter_manager.complete(f"skill_run_{run_id}")

    async def _persist_event_message(self, db: Database, event):
        """把关键运行事件同步为聊天消息，支持错过 SSE 后恢复 UI。"""
        message_text = None
        message_type = "status"
        content_json = None

        if event.type == "run.started":
            message_text = "Article Studio 已启动"
        elif event.type == "skill.call.started":
            message_text = f"{event.data.get('skillId')} 正在运行..."
        elif event.type == "message.delta":
            await self._append_delta_message(db, event)
            return
        elif event.type == "artifact.updated":
            await self._upsert_artifact_message(db, event)
            return
            message_text = event.data.get("message")
            message_type = "card"
            content_json = event.data
        elif event.type == "run.waiting_input":
            message_text = event.data.get("message")
            message_type = "card"
            content_json = event.data
        elif event.type == "run.completed":
            message_text = "文章生成完成"
        elif event.type == "run.failed":
            message_text = event.data.get("message") or "运行失败"

        if not message_text:
            return

        now = datetime.now()
        await db.execute(
            query="""
                INSERT INTO chat_message (
                    messageKey, sessionId, runId, role, messageType, contentText, contentJson, status, createTime, updateTime
                ) VALUES (
                    :messageKey, :sessionId, :runId, :role, :messageType, :contentText, :contentJson, :status, :createTime, :updateTime
                )
            """,
            values={
                "messageKey": f"msg_{uuid.uuid4().hex[:16]}",
                "sessionId": event.session_id,
                "runId": event.run_id,
                "role": "assistant" if message_type == "card" else "tool",
                "messageType": message_type,
                "contentText": message_text,
                "contentJson": json.dumps(content_json, ensure_ascii=False) if content_json is not None else None,
                "status": "COMPLETED",
                "createTime": now,
                "updateTime": now,
            },
        )

    async def _upsert_artifact_message(self, db: Database, event):
        """同一类产物在聊天时间线中保持一张持续更新的卡片。"""
        artifact_type = event.data.get("artifactType")
        if not artifact_type:
            return
        if artifact_type not in {"markdown", "image-pack"}:
            return

        message_key = f"artifact_{event.run_id}_{artifact_type}"
        row = await db.fetch_one(
            query="""
                SELECT id, contentJson
                FROM chat_message
                WHERE messageKey = :messageKey AND isDelete = 0
            """,
            values={"messageKey": message_key},
        )
        now = datetime.now()
        next_data = dict(event.data)
        if row:
            current_data = json.loads(row["contentJson"]) if row["contentJson"] else {}
            if artifact_type == "image-pack":
                image_map = {}
                for image in [*(current_data.get("images") or []), *(next_data.get("images") or [])]:
                    key = image.get("placeholderId") or image.get("url") or f"{image.get('position')}_{image.get('keywords')}"
                    image_map[key] = image
                next_data = {**current_data, **next_data, "images": list(image_map.values())}
            else:
                next_data = {**current_data, **next_data}
            await db.execute(
                query="""
                    UPDATE chat_message
                    SET contentText = :contentText,
                        contentJson = :contentJson,
                        updateTime = :updateTime
                    WHERE id = :id
                """,
                values={
                    "id": row["id"],
                    "contentText": next_data.get("message") or event.data.get("message") or artifact_type,
                    "contentJson": json.dumps(next_data, ensure_ascii=False),
                    "updateTime": now,
                },
            )
            return

        await db.execute(
            query="""
                INSERT INTO chat_message (
                    messageKey, sessionId, runId, role, messageType, contentText, contentJson, status, createTime, updateTime
                ) VALUES (
                    :messageKey, :sessionId, :runId, :role, :messageType, :contentText, :contentJson, :status, :createTime, :updateTime
                )
            """,
            values={
                "messageKey": message_key,
                "sessionId": event.session_id,
                "runId": event.run_id,
                "role": "assistant",
                "messageType": "card",
                "contentText": next_data.get("message") or artifact_type,
                "contentJson": json.dumps(next_data, ensure_ascii=False),
                "status": "COMPLETED",
                "createTime": now,
                "updateTime": now,
            },
        )

    async def _append_delta_message(self, db: Database, event):
        """把流式片段合并成同一条聊天消息。"""
        target = event.data.get("target", "stream")
        text = event.data.get("text") or ""
        if not text:
            return

        message_key = f"stream_{event.run_id}_{target}"
        row = await db.fetch_one(
            query="""
                SELECT id, contentText, contentJson
                FROM chat_message
                WHERE messageKey = :messageKey AND isDelete = 0
            """,
            values={"messageKey": message_key},
        )
        now = datetime.now()
        if row:
            content_json = json.loads(row["contentJson"]) if row["contentJson"] else {}
            content_json.update(event.data)
            content_json["text"] = (content_json.get("text") or row["contentText"] or "") + text
            await db.execute(
                query="""
                    UPDATE chat_message
                    SET contentText = :contentText,
                        contentJson = :contentJson,
                        updateTime = :updateTime
                    WHERE id = :id
                """,
                values={
                    "id": row["id"],
                    "contentText": (row["contentText"] or "") + text,
                    "contentJson": json.dumps(content_json, ensure_ascii=False),
                    "updateTime": now,
                },
            )
            return

        content_json = {**event.data, "text": text}
        await db.execute(
            query="""
                INSERT INTO chat_message (
                    messageKey, sessionId, runId, role, messageType, contentText, contentJson, status, createTime, updateTime
                ) VALUES (
                    :messageKey, :sessionId, :runId, :role, :messageType, :contentText, :contentJson, :status, :createTime, :updateTime
                )
            """,
            values={
                "messageKey": message_key,
                "sessionId": event.session_id,
                "runId": event.run_id,
                "role": "assistant",
                "messageType": "delta",
                "contentText": text,
                "contentJson": json.dumps(content_json, ensure_ascii=False),
                "status": "STREAMING",
                "createTime": now,
                "updateTime": now,
            },
        )

    def _to_vo(self, row) -> SkillRunVO:
        return SkillRunVO(
            id=row["id"],
            runKey=row["runKey"],
            sessionId=row["sessionId"],
            parentRunId=row["parentRunId"],
            skillId=row["skillId"],
            skillKind=row["skillKind"],
            status=row["status"],
            inputJson=json.loads(row["inputJson"]) if row["inputJson"] else {},
            outputJson=json.loads(row["outputJson"]) if row["outputJson"] else None,
            contextJson=json.loads(row["contextJson"]) if row["contextJson"] else None,
            errorMessage=row["errorMessage"],
            startedAt=row["startedAt"].isoformat() if row["startedAt"] else None,
            completedAt=row["completedAt"].isoformat() if row["completedAt"] else None,
            createTime=row["createTime"].isoformat(),
            updateTime=row["updateTime"].isoformat(),
        )


skill_executor = SkillExecutor()
