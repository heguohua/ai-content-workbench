"""会话路由"""

from fastapi import APIRouter, Depends
from databases import Database

from app.database import get_db
from app.deps import require_login
from app.schemas.common import BaseResponse
from app.schemas.session import ChatMessageVO, ChatSessionVO, SessionCreateRequest
from app.schemas.user import LoginUserVO
from app.services.session_service import SessionService

router = APIRouter(prefix="/session", tags=["会话管理"])


@router.post("/create", response_model=BaseResponse[ChatSessionVO])
async def create_session(
    request: SessionCreateRequest,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    service = SessionService(db)
    session = await service.create_session(request, current_user)
    return BaseResponse.success(data=session)


@router.get("/{session_id}", response_model=BaseResponse[ChatSessionVO])
async def get_session(
    session_id: int,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    service = SessionService(db)
    session = await service.get_session(session_id, current_user)
    return BaseResponse.success(data=session)


@router.get("/{session_id}/messages", response_model=BaseResponse[list[ChatMessageVO]])
async def list_session_messages(
    session_id: int,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    service = SessionService(db)
    messages = await service.list_messages(session_id, current_user)
    return BaseResponse.success(data=messages)
