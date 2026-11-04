from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from app.modules.drawings_boq.rebar.bbs_report_service import BbsReportService
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.modules.drawings_boq.rebar.bbs_report_schemas import CropsOut, QuestionListOut, ReportFindingListOut, ReportSummaryOut, SignRequest
from app.modules.drawings_boq.rebar.bbs_schemas import FindingOut

router = APIRouter(tags=["Bar bending schedule report"])
_READ = PermissionKey.DRAWING_READ
_WRITE = PermissionKey.SCHEDULE_IMPORT
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

@router.get("/bbs/{document_id}/report/summary", response_model=ReportSummaryOut)
async def bbs_report_summary(document_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await BbsReportService(session).summary(_org(current_user), document_id)

@router.get("/bbs/{document_id}/report/findings", response_model=ReportFindingListOut)
async def bbs_report_findings(document_id: UUID, finding_class: str | None = Query(default=None, max_length=14), code: str | None = Query(default=None, max_length=40),
  sheet: int | None = Query(default=None, ge=0), status: str | None = Query(default=None, max_length=10), page: int = Query(default=1, ge=1),
  page_size: int = Query(default=20, ge=1, le=200), current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await BbsReportService(session).findings(_org(current_user), document_id, finding_class, code, sheet, status, page, page_size)

@router.get("/bbs/{document_id}/report/questions", response_model=QuestionListOut)
async def bbs_report_questions(document_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await BbsReportService(session).questions(_org(current_user), document_id)

@router.get("/bbs/{document_id}/report/summary.md")
async def bbs_report_markdown(document_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  text = await BbsReportService(session).summary_md(_org(current_user), document_id)
  return Response(content=text, media_type="text/markdown; charset=utf-8")

@router.get("/bbs/{document_id}/report/export.xlsx")
async def bbs_report_xlsx(document_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  data, name = await BbsReportService(session).export_xlsx(_org(current_user), document_id)
  return Response(content=data, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{name}"'})

@router.get("/findings/{finding_id}/crops", response_model=CropsOut)
async def bbs_finding_crops(finding_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await BbsReportService(session).crops(_org(current_user), finding_id)

@router.post("/findings/{finding_id}/sign", response_model=FindingOut)
async def sign_bbs_finding(finding_id: UUID, payload: SignRequest, current_user: User = Depends(require_permission(_WRITE)), session: AsyncSession = Depends(get_db)):
  return await BbsReportService(session).sign(_org(current_user), finding_id, current_user.id, payload.reason)
