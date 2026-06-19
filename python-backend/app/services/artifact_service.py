"""产物服务"""

import json
import uuid
from datetime import datetime

from databases import Database

from app.exceptions import ErrorCode, throw_if_not
from app.schemas.artifact import ArtifactUpdateRequest, ArtifactVO
from app.schemas.user import LoginUserVO


class ArtifactService:
    """产物服务"""

    def __init__(self, db: Database):
        self.db = db

    async def list_by_session(self, session_id: int, current_user: LoginUserVO) -> list[ArtifactVO]:
        """查询会话下产物"""
        rows = await self.db.fetch_all(
            query="""
                SELECT a.*
                FROM artifact a
                JOIN chat_session s ON a.sessionId = s.id
                JOIN project p ON s.projectId = p.id
                WHERE a.sessionId = :sessionId
                  AND a.isDelete = 0
                  AND s.isDelete = 0
                  AND p.isDelete = 0
                  AND p.ownerUserId = :userId
                ORDER BY a.updateTime DESC
            """,
            values={"sessionId": session_id, "userId": current_user.id},
        )
        return [self._to_vo(row) for row in rows]

    async def update_artifact(
        self,
        artifact_id: int,
        request: ArtifactUpdateRequest,
        current_user: LoginUserVO,
    ) -> ArtifactVO:
        """更新产物"""
        row = await self.db.fetch_one(
            query="""
                SELECT a.*
                FROM artifact a
                JOIN chat_session s ON a.sessionId = s.id
                JOIN project p ON s.projectId = p.id
                WHERE a.id = :artifactId
                  AND a.isDelete = 0
                  AND s.isDelete = 0
                  AND p.isDelete = 0
                  AND p.ownerUserId = :userId
            """,
            values={"artifactId": artifact_id, "userId": current_user.id},
        )
        throw_if_not(row, ErrorCode.NOT_FOUND_ERROR, "产物不存在")
        now = datetime.now()
        title = request.title or row["title"]
        meta_json = request.meta_json
        await self.db.execute(
            query="""
                UPDATE artifact
                SET title = :title,
                    contentJson = :contentJson,
                    metaJson = :metaJson,
                    version = version + 1,
                    updateTime = :updateTime
                WHERE id = :artifactId
            """,
            values={
                "artifactId": artifact_id,
                "title": title,
                "contentJson": json.dumps(request.content_json, ensure_ascii=False),
                "metaJson": json.dumps(meta_json, ensure_ascii=False) if meta_json is not None else row["metaJson"],
                "updateTime": now,
            },
        )
        updated = await self.db.fetch_one("SELECT * FROM artifact WHERE id = :id", {"id": artifact_id})
        return self._to_vo(updated)

    async def upsert_by_session_and_type(
        self,
        session_id: int,
        artifact_type: str,
        title: str,
        content_json: dict,
        source_run_id: int | None = None,
    ) -> dict:
        """按会话和类型更新或创建产物"""
        row = await self.db.fetch_one(
            query="""
                SELECT *
                FROM artifact
                WHERE sessionId = :sessionId
                  AND artifactType = :artifactType
                  AND isDelete = 0
                LIMIT 1
            """,
            values={"sessionId": session_id, "artifactType": artifact_type},
        )
        now = datetime.now()
        if row:
            await self.db.execute(
                query="""
                    UPDATE artifact
                    SET title = :title,
                        sourceRunId = :sourceRunId,
                        contentJson = :contentJson,
                        version = version + 1,
                        updateTime = :updateTime
                    WHERE id = :id
                """,
                values={
                    "id": row["id"],
                    "title": title,
                    "sourceRunId": source_run_id,
                    "contentJson": json.dumps(content_json, ensure_ascii=False),
                    "updateTime": now,
                },
            )
            updated = await self.db.fetch_one("SELECT * FROM artifact WHERE id = :id", {"id": row["id"]})
            return self._to_dict(updated)

        artifact_key = f"art_{uuid.uuid4().hex[:16]}"
        await self.db.execute(
            query="""
                INSERT INTO artifact (
                    artifactKey, sessionId, sourceRunId, artifactType, title, version, status, contentJson, metaJson, createTime, updateTime, isDelete
                ) VALUES (
                    :artifactKey, :sessionId, :sourceRunId, :artifactType, :title, 1, :status, :contentJson, NULL, :createTime, :updateTime, 0
                )
            """,
            values={
                "artifactKey": artifact_key,
                "sessionId": session_id,
                "sourceRunId": source_run_id,
                "artifactType": artifact_type,
                "title": title,
                "status": "ACTIVE",
                "contentJson": json.dumps(content_json, ensure_ascii=False),
                "createTime": now,
                "updateTime": now,
            },
        )
        created = await self.db.fetch_one("SELECT * FROM artifact WHERE artifactKey = :artifactKey", {"artifactKey": artifact_key})
        return self._to_dict(created)

    def _to_vo(self, row) -> ArtifactVO:
        return ArtifactVO(
            id=row["id"],
            artifactKey=row["artifactKey"],
            sessionId=row["sessionId"],
            sourceRunId=row["sourceRunId"],
            artifactType=row["artifactType"],
            title=row["title"],
            version=row["version"],
            status=row["status"],
            contentJson=json.loads(row["contentJson"]) if row["contentJson"] else {},
            metaJson=json.loads(row["metaJson"]) if row["metaJson"] else None,
            createTime=row["createTime"].isoformat(),
            updateTime=row["updateTime"].isoformat(),
        )

    def _to_dict(self, row) -> dict:
        return self._to_vo(row).model_dump(by_alias=True)
