"""项目路由"""

from fastapi import APIRouter, Depends
from databases import Database

from app.database import get_db
from app.deps import require_login
from app.schemas.common import BaseResponse
from app.schemas.project import ProjectCreateRequest, ProjectQueryRequest, ProjectVO
from app.schemas.user import LoginUserVO
from app.services.project_service import ProjectService

router = APIRouter(prefix="/project", tags=["项目管理"])


@router.post("/create", response_model=BaseResponse[ProjectVO])
async def create_project(
    request: ProjectCreateRequest,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    service = ProjectService(db)
    project = await service.create_project(request, current_user)
    return BaseResponse.success(data=project)


@router.post("/list", response_model=BaseResponse[dict])
async def list_projects(
    request: ProjectQueryRequest,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    service = ProjectService(db)
    records, total = await service.list_projects(request, current_user)
    return BaseResponse.success(
        data={
            "records": records,
            "total": total,
            "current": request.current,
            "pageSize": request.page_size,
        }
    )


@router.get("/{project_id}", response_model=BaseResponse[ProjectVO])
async def get_project(
    project_id: int,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    service = ProjectService(db)
    project = await service.get_project(project_id, current_user)
    return BaseResponse.success(data=project)
