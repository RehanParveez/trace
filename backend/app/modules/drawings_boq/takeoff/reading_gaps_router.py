from __future__ import annotations
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.takeoff.prep_service import PrepService
from app.modules.drawings_boq.takeoff.extract.extract_repository import ExtractRepository
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.modules.drawings_boq.takeoff.reading_gaps import reading_gaps
from app.modules.identity.models import User
from app.modules.identity.enums import PermissionKey

router = APIRouter()

class LeftOutTag(BaseModel):
  tag: str
  category: str | None = None
  reason: str
  count: int
  points: list[list[float]] = Field(default_factory=list)

class SetAsideItem(BaseModel):
  id: str
  label: str | None = None
  tag: str | None = None
  category: str | None = None
  reason: str
  codes: list[str] = Field(default_factory=list)
  anchor: list[float] | None = None

class LeftOutResponse(BaseModel):
  sheet_id: UUID
  read: bool = Field(description="False when the sheet has not been read yet; then every mark would look left out, so none is listed.")
  tags: list[LeftOutTag] = Field(default_factory=list)
  set_aside: list[SetAsideItem] = Field(default_factory=list)
  summary: dict = Field(default_factory=dict)

class LeftOutService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.prep = PrepService(session)
    self.repo = ExtractRepository(session)

  async def sheet(self, org: UUID, sheet_id: UUID) -> dict:
    await self.prep._sheet(org, sheet_id)
    index = await self.prep._index(org, sheet_id)
    extraction = await self.repo.extraction(org, sheet_id)
    if extraction is None:
      return {"sheet_id": sheet_id, "read": False}
    candidates = await self.repo.candidates(org, [sheet_id])
    return {"sheet_id": sheet_id, "read": True, **reading_gaps(index.words, candidates)}

@router.get("/takeoff/sheets/{sheet_id}/left-out", response_model=LeftOutResponse)
async def get_left_out(
  sheet_id: UUID, current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db),
):
  return await LeftOutService(session).sheet(current_user.active_membership.organization_id, sheet_id)
