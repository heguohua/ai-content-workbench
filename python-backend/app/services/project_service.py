"""项目服务"""

import json
import uuid
from datetime import datetime
from typing import List, Tuple

from databases import Database
from sqlalchemy import and_, func, select

from app.exceptions import ErrorCode, throw_if_not
from app.models.project import Project
from app.schemas.project import ProjectCreateRequest, ProjectQueryRequest, ProjectVO
from app.schemas.user import LoginUserVO


class ProjectService:
    """项目服务"""

    def __init__(self, db: Database):
        self.db = db

    async def create_project(self, request: ProjectCreateRequest, current_user: LoginUserVO) -> ProjectVO:
        """创建项目"""
        now = datetime.now()
        project_key = f"proj_{uuid.uuid4().hex[:16]}"
        await self.db.execute(
            query="""
                INSERT INTO project (
                    projectKey, name, description, projectSkillId, ownerUserId, status, configJson, createTime, updateTime, isDelete
                ) VALUES (
                    :projectKey, :name, :description, :projectSkillId, :ownerUserId, :status, :configJson, :createTime, :updateTime, 0
                )
            """,
            values={
                "projectKey": project_key,
                "name": request.name,
                "description": request.description,
                "projectSkillId": request.project_skill_id,
                "ownerUserId": current_user.id,
                "status": "ACTIVE",
                "configJson": json.dumps(request.config_json, ensure_ascii=False) if request.config_json else None,
                "createTime": now,
                "updateTime": now,
            },
        )
        row = await self.db.fetch_one(
            select(Project).where(and_(Project.project_key == project_key, Project.is_delete == 0))
        )
        return self._to_vo(row)

    async def list_projects(self, request: ProjectQueryRequest, current_user: LoginUserVO) -> Tuple[List[ProjectVO], int]:
        """分页查询项目"""
        conditions = [Project.is_delete == 0, Project.owner_user_id == current_user.id]
        if request.name:
            conditions.append(Project.name.like(f"%{request.name}%"))
        if request.project_skill_id:
            conditions.append(Project.project_skill_id == request.project_skill_id)
        if request.status:
            conditions.append(Project.status == request.status)

        total = await self.db.fetch_val(select(func.count(Project.id)).where(and_(*conditions)))
        rows = await self.db.fetch_all(
            select(Project)
            .where(and_(*conditions))
            .order_by(Project.update_time.desc())
            .limit(request.page_size)
            .offset((request.current - 1) * request.page_size)
        )
        return [self._to_vo(row) for row in rows], total

    async def get_project(self, project_id: int, current_user: LoginUserVO) -> ProjectVO:
        """查询项目"""
        row = await self.db.fetch_one(
            select(Project).where(
                and_(
                    Project.id == project_id,
                    Project.owner_user_id == current_user.id,
                    Project.is_delete == 0,
                )
            )
        )
        throw_if_not(row, ErrorCode.NOT_FOUND_ERROR, "项目不存在")
        return self._to_vo(row)

    def _to_vo(self, row) -> ProjectVO:
        return ProjectVO(
            id=row["id"],
            projectKey=row["projectKey"],
            name=row["name"],
            description=row["description"],
            projectSkillId=row["projectSkillId"],
            ownerUserId=row["ownerUserId"],
            status=row["status"],
            configJson=json.loads(row["configJson"]) if row["configJson"] else None,
            createTime=row["createTime"].isoformat(),
            updateTime=row["updateTime"].isoformat(),
        )
