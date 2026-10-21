from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.takeoff.reading_score.service import ReadingScoreService
from app.modules.drawings_boq.takeoff.reading_score.schemas import (ImportLabelsRequest, LabelTemplateResponse, DeleteLabelsResponse, ScoreListResponse, ScoreResponse, CompareResponse, DeriveLabelsResponse, ImportLabelsResponse,
  LabelsSummaryResponse, RunScoreRequest
)

router = APIRouter()
_READ = PermissionKey.DRAWING_READ
_EDIT = PermissionKey.BOQ_UPDATE

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

@router.get("/takeoff/reading-labels/template", response_model=LabelTemplateResponse)
async def label_template(current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return ReadingScoreService(session).label_template()

@router.get("/drawings/{drawing_id}/takeoff/reading-labels", response_model=LabelsSummaryResponse)
async def labels_summary(drawing_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await ReadingScoreService(session).labels_summary(_org(current_user), drawing_id)

@router.post("/drawings/{drawing_id}/takeoff/reading-labels/derive", response_model=DeriveLabelsResponse)
async def derive_labels(drawing_id: UUID, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db)):
  return await ReadingScoreService(session).derive_labels(_org(current_user), current_user.id, drawing_id)

@router.post("/drawings/{drawing_id}/takeoff/reading-labels/import", response_model=ImportLabelsResponse)
async def import_labels(drawing_id: UUID, payload: ImportLabelsRequest, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db)):
  return await ReadingScoreService(session).import_labels(_org(current_user), current_user.id, drawing_id, payload)

@router.delete("/drawings/{drawing_id}/takeoff/reading-labels", response_model=DeleteLabelsResponse)
async def delete_labels(drawing_id: UUID, source: str | None = Query(default=None, description="REGISTER or IMPORT; leave out for both."),
  current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db)):
  return await ReadingScoreService(session).delete_labels(_org(current_user), drawing_id, source)

@router.get("/drawings/{drawing_id}/takeoff/reading-scores", response_model=ScoreListResponse)
async def list_scores(drawing_id: UUID, limit: int = Query(default=50, ge=1, le=200), current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await ReadingScoreService(session).list_scores(_org(current_user), drawing_id, limit)

@router.post("/drawings/{drawing_id}/takeoff/reading-scores", response_model=ScoreResponse)
async def run_score(drawing_id: UUID, payload: RunScoreRequest, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db)):
  return await ReadingScoreService(session).run_score(_org(current_user), current_user.id, drawing_id, payload)

@router.get("/drawings/{drawing_id}/takeoff/reading-scores/compare", response_model=CompareResponse)
async def compare_scores(drawing_id: UUID, a: UUID, b: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await ReadingScoreService(session).compare(_org(current_user), drawing_id, a, b)

@router.get("/takeoff/reading-scores/{score_id}", response_model=ScoreResponse)
async def get_score(score_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await ReadingScoreService(session).get_score(_org(current_user), score_id)