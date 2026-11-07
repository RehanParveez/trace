from __future__ import annotations
from fastapi import APIRouter, Depends, Query, Response
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from uuid import UUID
from app.modules.drawings_boq.pricing.priced.schemas import PricedResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.modules.drawings_boq.pricing.priced.service import PricedService

router = APIRouter(tags=["Priced BOQ"])
_READ = PermissionKey.DRAWING_READ
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

@router.get("/projects/{project_id}/priced", response_model=PricedResponse)
async def project_priced(project_id: UUID, profile: str | None = Query(None, description="PRIVATE_QS (default) or MRS_PB."), rate_book_id: UUID | None = Query(None, description="One rate book; the default stack when omitted."),
    current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await PricedService(session).priced(_org(current_user), project_id, profile, rate_book_id)

@router.get("/projects/{project_id}/priced.xlsx")
async def project_priced_xlsx(project_id: UUID, profile: str | None = Query(None), rate_book_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  data = await PricedService(session).workbook(_org(current_user), project_id, profile, rate_book_id)
  return Response(content=data, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="priced-boq-{project_id}.xlsx"'})
