from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.permissions import require_permission
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from app.modules.drawings_boq.takeoff.questions.schemas import AnswerRequest, QuestionsResponse
from app.modules.drawings_boq.takeoff.questions.service import QuestionsService

router = APIRouter()
_READ = PermissionKey.DRAWING_READ
_EDIT = PermissionKey.BOQ_UPDATE

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

@router.get("/projects/{project_id}/questions", response_model=QuestionsResponse)
async def project_questions(project_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await QuestionsService(session).view(_org(current_user), project_id)

@router.get("/projects/{project_id}/questions/client-page", response_class=PlainTextResponse)
async def client_page(project_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return PlainTextResponse(await QuestionsService(session).client_page(_org(current_user), project_id), media_type="text/markdown; charset=utf-8")

@router.post("/projects/{project_id}/questions/{qid}/answer", response_model=QuestionsResponse)
async def answer_question(project_id: UUID, qid: str, payload: AnswerRequest, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db)):
  return await QuestionsService(session).answer(_org(current_user), current_user.id, project_id, qid, payload.value)
