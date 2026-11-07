from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from uuid import UUID
from app.modules.drawings_boq.rebar.bbs_prepare_schemas import PreparedOut
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.rebar.bbs_prepare_service import BbsPrepareService
from fastapi.responses import Response

router = APIRouter(tags=["Bar bending schedule preparation"])
_READ = PermissionKey.DRAWING_READ
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DOC = Query(default=None, description="A supplied bar schedule of the project that has been audited: the prepared schedule is then compared with it.")

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

@router.get("/projects/{project_id}/bbs/prepared", response_model=PreparedOut)
async def prepared_bbs(project_id: UUID, document_id: UUID | None = DOC, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  prepared, comparison = await BbsPrepareService(session).prepared(_org(current_user), project_id, document_id)
  return {"prepared": prepared, "comparison": comparison}

@router.get("/projects/{project_id}/bbs/prepared.xlsx")
async def prepared_bbs_xlsx(project_id: UUID, document_id: UUID | None = DOC, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  data, name = await BbsPrepareService(session).export_xlsx(_org(current_user), project_id, document_id)
  return Response(content=data, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{name}"'})

@router.get("/projects/{project_id}/bbs/prepared.pdf")
async def prepared_bbs_pdf(project_id: UUID, document_id: UUID | None = DOC, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  data, name = await BbsPrepareService(session).export_pdf(_org(current_user), project_id, document_id)
  return Response(content=data, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{name}"'})
