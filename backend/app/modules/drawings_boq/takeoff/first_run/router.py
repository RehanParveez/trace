from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.permissions import require_permission
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from app.modules.drawings_boq.takeoff.first_run.schemas import FirstRunReport, FirstRunStarted
from app.modules.drawings_boq.takeoff.first_run.service import FirstRunService

router = APIRouter()
_READ = PermissionKey.DRAWING_READ
_EDIT = PermissionKey.BOQ_UPDATE

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

@router.get("/projects/{project_id}/first-run", response_model=FirstRunReport)
async def first_run_report(project_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await FirstRunService(session).report(_org(current_user), project_id)

@router.post("/projects/{project_id}/first-run", response_model=FirstRunStarted)
async def start_first_run(project_id: UUID, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db)):
  from app.modules.drawings_boq.tasks import first_run_task
  org = _org(current_user)
  drawings = await FirstRunService(session)._drawings(org, project_id)
  from app.modules.drawings_boq.takeoff.flow.service import FlowService
  await FlowService(session).record(org, project_id, "queued")
  first_run_task.apply_async(args=[str(org), str(project_id), str(current_user.id)], queue="bim_parsing")
  return {"project_id": project_id, "queued": True, "drawings": len(drawings)}
