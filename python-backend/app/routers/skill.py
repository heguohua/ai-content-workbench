"""Skill 路由"""

from fastapi import APIRouter, Depends
from databases import Database

from app.database import get_db
from app.deps import require_login
from app.runtime.executor import skill_executor
from app.runtime.registry import skill_registry
from app.schemas.common import BaseResponse
from app.schemas.skill import SkillDefinitionVO, SkillRunActionRequest, SkillRunCreateRequest, SkillRunVO
from app.schemas.user import LoginUserVO

router = APIRouter(prefix="/skill", tags=["Skill Runtime"])


@router.get("/definitions", response_model=BaseResponse[list[SkillDefinitionVO]])
async def list_skills(current_user: LoginUserVO = Depends(require_login)):
    return BaseResponse.success(data=skill_registry.list())


@router.post("/run", response_model=BaseResponse[SkillRunVO])
async def create_skill_run(
    request: SkillRunCreateRequest,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    run = await skill_executor.execute(
        db=db,
        session_id=request.session_id,
        skill_id=request.skill_id,
        input_data=request.input,
        current_user=current_user,
    )
    return BaseResponse.success(data=run)


@router.post("/run/{run_id}/action", response_model=BaseResponse[SkillRunVO])
async def continue_skill_run(
    run_id: int,
    request: SkillRunActionRequest,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    run = await skill_executor.resume(
        db=db,
        run_id=run_id,
        action=request.action,
        payload=request.payload,
        current_user=current_user,
    )
    return BaseResponse.success(data=run)


@router.get("/run/{run_id}/stream")
async def stream_skill_run(
    run_id: int,
    current_user: LoginUserVO = Depends(require_login),
):
    return skill_executor.create_stream(run_id, current_user)
