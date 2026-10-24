from __future__ import annotations
from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from app.modules.drawings_boq.pricing.import_schemas import (RateImportResponse, BulkRowsRequest, BulkRowsResponse, ImportRowResponse, ImportUpdateRequest, PublishRequest,
  PublishResponse, ReadinessResponse, ReparseRequest, RowFilter, RowUpdateRequest, SuggestResponse)
from app.modules.identity.enums import PermissionKey
from app.core.database import get_db
from app.dependencies.permissions import require_permission
from app.modules.drawings_boq.pricing.import_service import MAX_FILE_BYTES, RateImportService
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.identity.models import User
from uuid import UUID
from datetime import date
from typing import Literal
from app.modules.drawings_boq.pricing.rate_tools_service import RateToolsService
from app.modules.drawings_boq.pricing.tools_schemas import CompareResponse, EscalationFromCompareRequest, EscalationFromCompareResponse, HistoryResponse, RateGapsResponse, RefreshRequest, RefreshResponse

router = APIRouter(tags=["Rate schedules"])

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

def _cursor(response: Response, nxt) -> None:
  if nxt is not None:
    response.headers["X-Next-Cursor"] = str(nxt)

@router.post("/rate-imports", response_model=RateImportResponse, status_code=201)
async def upload_rate_schedule(
  file: UploadFile = File(...),
  layout_profile: str = Form(default="GENERIC"),
  first_page: int = Form(default=1, ge=1),
  last_page: int | None = Form(default=None, ge=1),
  book_code: str | None = Form(default=None),
  book_name: str | None = Form(default=None),
  edition: str | None = Form(default=None),
  jurisdiction: str | None = Form(default=None),
  province: str | None = Form(default=None),
  city: str | None = Form(default=None),
  currency: str = Form(default="PKR", min_length=3, max_length=3),
  effective_from: date | None = Form(default=None),
  effective_to: date | None = Form(default=None),
  current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  data = await file.read(MAX_FILE_BYTES + 1)
  svc = RateImportService(session)
  org = _org(current_user)
  imp = await svc.create(org, current_user.id, file.filename or "schedule", data, {
    "layout_profile": layout_profile, "first_page": first_page, "last_page": last_page, "book_code": book_code, "book_name": book_name, "edition": edition,
    "jurisdiction": jurisdiction, "province": province, "city": city, "currency": currency, "effective_from": effective_from, "effective_to": effective_to})
  twin = imp.duplicate_of_id
  out = await svc.dispatch(org, imp)
  out.duplicate_of_id = twin
  return out

@router.get("/rate-imports", response_model=list[RateImportResponse])
async def list_rate_imports(
  response: Response,
  status: Literal["UPLOADED", "PARSING", "REVIEW", "PUBLISHED", "FAILED", "CANCELLED"] | None = Query(default=None),
  limit: int = Query(default=50, ge=1, le=200),
  after: UUID | None = Query(default=None),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  rows, nxt = await RateImportService(session).list_imports(_org(current_user), status=status, limit=limit, after=after)
  _cursor(response, nxt)
  return rows

@router.get("/rate-imports/{import_id}", response_model=RateImportResponse)
async def get_rate_import(import_id: UUID, current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db)):
  return await RateImportService(session).get(_org(current_user), import_id)

@router.patch("/rate-imports/{import_id}", response_model=RateImportResponse)
async def update_rate_import(import_id: UUID, payload: ImportUpdateRequest, current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)),
  session: AsyncSession = Depends(get_db)):
  return await RateImportService(session).update_meta(_org(current_user), current_user.id, import_id, payload)

@router.delete("/rate-imports/{import_id}", status_code=204)
async def delete_rate_import(import_id: UUID, current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)), session: AsyncSession = Depends(get_db)):
  await RateImportService(session).delete(_org(current_user), current_user.id, import_id)
  return Response(status_code=204)

@router.post("/rate-imports/{import_id}/reparse", response_model=RateImportResponse)
async def reparse_rate_import(import_id: UUID, payload: ReparseRequest, current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)),
  session: AsyncSession = Depends(get_db)):
  svc = RateImportService(session)
  org = _org(current_user)
  imp = await svc.reparse(org, current_user.id, import_id, payload)
  return await svc.dispatch(org, imp)

@router.get("/rate-imports/{import_id}/rows", response_model=list[ImportRowResponse])
async def list_rate_import_rows(
  import_id: UUID,
  response: Response,
  filter: RowFilter | None = Query(default=None),
  chapter: str | None = Query(default=None, max_length=200),
  q: str | None = Query(default=None, max_length=100),
  after: int | None = Query(default=None, ge=0),
  limit: int = Query(default=100, ge=1, le=500),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  rows, nxt = await RateImportService(session).list_rows(_org(current_user), import_id, flt=filter, chapter=chapter, q=q, after_seq=after, limit=limit)
  _cursor(response, nxt)
  return rows

@router.get("/rate-imports/{import_id}/chapters")
async def list_rate_import_chapters(import_id: UUID, current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db)):
  return await RateImportService(session).chapters(_org(current_user), import_id)

@router.get("/rate-imports/{import_id}/samples", response_model=list[ImportRowResponse])
async def list_rate_import_samples(import_id: UUID, current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db)):
  return await RateImportService(session).samples(_org(current_user), import_id)

@router.patch("/rate-imports/{import_id}/rows/{row_id}", response_model=ImportRowResponse)
async def update_rate_import_row(import_id: UUID, row_id: UUID, payload: RowUpdateRequest, current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)),
  session: AsyncSession = Depends(get_db)):
  return await RateImportService(session).update_row(_org(current_user), current_user.id, import_id, row_id, payload)

@router.post("/rate-imports/{import_id}/rows/bulk", response_model=BulkRowsResponse)
async def bulk_rate_import_rows(import_id: UUID, payload: BulkRowsRequest, current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)),
  session: AsyncSession = Depends(get_db)):
  return await RateImportService(session).bulk(_org(current_user), current_user.id, import_id, payload)

@router.post("/rate-imports/{import_id}/suggest", response_model=SuggestResponse)
async def refresh_rate_import_suggestions(import_id: UUID, current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)), session: AsyncSession = Depends(get_db)):
  return await RateImportService(session).refresh_suggestions(_org(current_user), current_user.id, import_id)

@router.get("/rate-imports/{import_id}/readiness", response_model=ReadinessResponse)
async def rate_import_readiness(import_id: UUID, include_unmapped: bool = Query(default=False), current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db)):
  r = await RateImportService(session).readiness(_org(current_user), import_id, include_unmapped)
  return ReadinessResponse(can_publish=r.can_publish, blockers=r.blockers, warnings=r.warnings, counts=r.counts)

@router.post("/rate-imports/{import_id}/publish", response_model=PublishResponse)
async def publish_rate_import(import_id: UUID, payload: PublishRequest, current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)),
  session: AsyncSession = Depends(get_db)):
  return await RateImportService(session).publish(_org(current_user), current_user.id, import_id, payload)

@router.get("/rate-books/{book_id}/export")
async def export_rate_book(book_id: UUID, format: Literal["csv", "xlsx"] = Query(default="csv"),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db)):
  tools = RateToolsService(session)
  if format == "xlsx":
    name, body = await tools.export_xlsx(_org(current_user), book_id)
    media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
  else:
    name, body = await tools.export_csv(_org(current_user), book_id)
    media = "text/csv; charset=utf-8"
  return Response(content=body, media_type=media, headers={"Content-Disposition": f'attachment; filename="{name}"'})

@router.get("/rate-books/{book_id}/compare/{other_id}", response_model=CompareResponse)
async def compare_rate_books(book_id: UUID, other_id: UUID, match_on: Literal["code", "csr_ref"] = Query(default="code"),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db)):
  return await RateToolsService(session).compare(_org(current_user), book_id, other_id, match_on)

@router.post("/rate-books/{book_id}/escalations/from-compare", response_model=EscalationFromCompareResponse)
async def escalations_from_compare(book_id: UUID, payload: EscalationFromCompareRequest, current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)),
  session: AsyncSession = Depends(get_db)):
  return await RateToolsService(session).escalations_from_compare(_org(current_user), current_user.id, book_id, payload)

@router.get("/rate-books/{book_id}/history", response_model=HistoryResponse)
async def rate_history(book_id: UUID, work_item_code: str = Query(min_length=1, max_length=50), unit: str | None = Query(default=None, max_length=20),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db)):
  return await RateToolsService(session).history(_org(current_user), book_id, work_item_code, unit)

@router.post("/rate-books/{book_id}/refresh", response_model=RefreshResponse)
async def refresh_rate_book(book_id: UUID, payload: RefreshRequest, current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)),
  session: AsyncSession = Depends(get_db)):
  return await RateToolsService(session).refresh(_org(current_user), current_user.id, book_id, payload)

@router.get("/boq-versions/{boq_version_id}/rate-gaps", response_model=RateGapsResponse)
async def boq_rate_gaps(boq_version_id: UUID, as_of: date | None = Query(default=None), rate_book_ids: list[UUID] | None = Query(default=None),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db)):
  return await RateToolsService(session).rate_gaps(_org(current_user), boq_version_id, as_of=as_of, rate_book_ids=rate_book_ids)
