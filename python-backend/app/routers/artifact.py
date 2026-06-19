"""产物路由"""

from fastapi import APIRouter, Depends
from databases import Database

from app.database import get_db
from app.deps import require_login
from app.schemas.artifact import ArtifactUpdateRequest, ArtifactVO
from app.schemas.common import BaseResponse
from app.schemas.user import LoginUserVO
from app.services.artifact_service import ArtifactService

router = APIRouter(prefix="/artifact", tags=["产物管理"])


@router.get("/session/{session_id}", response_model=BaseResponse[list[ArtifactVO]])
async def list_artifacts(
    session_id: int,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    service = ArtifactService(db)
    artifacts = await service.list_by_session(session_id, current_user)
    return BaseResponse.success(data=artifacts)


@router.post("/{artifact_id}/update", response_model=BaseResponse[ArtifactVO])
async def update_artifact(
    artifact_id: int,
    request: ArtifactUpdateRequest,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    service = ArtifactService(db)
    artifact = await service.update_artifact(artifact_id, request, current_user)
    return BaseResponse.success(data=artifact)
