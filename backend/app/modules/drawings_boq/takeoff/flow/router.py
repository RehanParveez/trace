from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from app.modules.drawings_boq.takeoff.flow.schemas import AccuracyReport, FlowStatus, FlowBoqResponse, SeenRequest
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.modules.drawings_boq.takeoff.flow.service import FlowService

router = APIRouter(tags=["Upload to priced BOQ"])
_READ = PermissionKey.DRAWING_READ

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

@router.get("/projects/{project_id}/flow", response_model=FlowStatus)
async def flow_status(project_id: UUID, profile: str | None = Query(None, description="A billing profile; the company's when omitted."), current_user: User = Depends(require_permission(_READ)),
    session: AsyncSession = Depends(get_db)):
  return await FlowService(session).status(_org(current_user), project_id, profile)

@router.get("/projects/{project_id}/flow/boq", response_model=FlowBoqResponse)
async def flow_boq(project_id: UUID, profile: str | None = Query(None), rate_book_id: UUID | None = Query(None, description="One rate book; the default stack when omitted."),
    current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await FlowService(session).boq(_org(current_user), project_id, profile, rate_book_id)

@router.get("/projects/{project_id}/flow/accuracy", response_model=AccuracyReport)
async def flow_accuracy(project_id: UUID, profile: str | None = Query(None), rate_book_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await FlowService(session).accuracy(_org(current_user), project_id, profile, rate_book_id)

@router.get("/projects/{project_id}/flow/export/{kind}")
async def flow_export(project_id: UUID, kind: str, profile: str | None = Query(None), rate_book_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  data, media, name = await FlowService(session).export(_org(current_user), project_id, kind, profile, rate_book_id)
  return Response(content=data, media_type=media, headers={"Content-Disposition": f'attachment; filename="{name}"'})

@router.post("/projects/{project_id}/flow/seen", status_code=204)
async def flow_seen(project_id: UUID, payload: SeenRequest, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  await FlowService(session).record(_org(current_user), project_id, f"{payload.step}_seen")
  return Response(status_code=204)
