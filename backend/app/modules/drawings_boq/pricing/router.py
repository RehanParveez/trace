from __future__ import annotations
from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from app.modules.identity.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.pricing.rate_service import RateBookService
from app.modules.drawings_boq.pricing.schemas import (AnalysisBreakdownResponse, AnalysisCreateRequest, AnalysisResponse, AnalysisUpdateRequest, DiffResponse, EscalationCreateRequest, EscalationResponse,
  ImportResultResponse, OverrideCreateRequest, OverrideResponse, OverrideRevokeRequest, PriceVersionRequest, PriceVersionResponse, PricingSummaryResponse, RateBookCreateRequest,
  RateBookResponse, RateBookUpdateRequest, RateExplainResponse, RateItemBulkRequest, RateItemInput, RateItemResponse, RateItemUpdateRequest,
)
from typing import Literal
from datetime import date
from uuid import UUID
from app.dependencies.permissions import require_permission
from app.modules.identity.enums import PermissionKey
from app.core.database import get_db
from app.core.exceptions import TraceException
from app.modules.drawings_boq.pricing.diff_service import BOQDiffService
from app.modules.drawings_boq.pricing.pricing_service import PricingService

router = APIRouter(tags=["Pricing & comparison"])

MAX_CSV_BYTES = 5 * 1024 * 1024

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

def _books(session: AsyncSession) -> RateBookService:
  return RateBookService(session)

def _cursor(response: Response, next_cursor) -> None:
  if next_cursor:
    response.headers["X-Next-Cursor"] = str(next_cursor)

@router.get("/rate-books", response_model=list[RateBookResponse])
async def list_rate_books(
  response: Response,
  status: Literal["DRAFT", "ACTIVE", "SUPERSEDED", "ARCHIVED"] | None = Query(default=None),
  owner: Literal["all", "system", "org"] = Query(default="all"),
  limit: int = Query(default=100, ge=1, le=500),
  after: UUID | None = Query(default=None),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  rows, nxt = await _books(session).list_books(_org(current_user), status=status, owner=owner, after=after, limit=limit)
  _cursor(response, nxt)
  return rows

@router.post("/rate-books", response_model=RateBookResponse, status_code=201)
async def create_rate_book(
  payload: RateBookCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _books(session).create_book(_org(current_user), current_user.id, payload)

@router.get("/rate-books/{book_id}", response_model=RateBookResponse)
async def get_rate_book(
  book_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _books(session).get_book(_org(current_user), book_id)

@router.patch("/rate-books/{book_id}", response_model=RateBookResponse)
async def update_rate_book(
  book_id: UUID,
  payload: RateBookUpdateRequest,
  current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _books(session).update_book(_org(current_user), current_user.id, book_id, payload)

@router.delete("/rate-books/{book_id}", status_code=204)
async def delete_rate_book(
  book_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  await _books(session).delete_book(_org(current_user), current_user.id, book_id)
  return Response(status_code=204)

@router.post("/rate-books/{book_id}/publish", response_model=RateBookResponse)
async def publish_rate_book(
  book_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _books(session).publish_book(_org(current_user), current_user.id, book_id)

@router.post("/rate-books/{book_id}/new-version", response_model=RateBookResponse, status_code=201)
async def new_rate_book_version(
  book_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _books(session).new_version(_org(current_user), current_user.id, book_id)

@router.post("/rate-books/{book_id}/archive", response_model=RateBookResponse)
async def archive_rate_book(
  book_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _books(session).archive_book(_org(current_user), current_user.id, book_id)

@router.get("/rate-books/{book_id}/items", response_model=list[RateItemResponse])
async def list_rate_items(
  book_id: UUID,
  response: Response,
  q: str | None = Query(default=None, max_length=100),
  trade: str | None = Query(default=None, max_length=80),
  include_inactive: bool = Query(default=False),
  limit: int = Query(default=200, ge=1, le=1000),
  after: UUID | None = Query(default=None),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  rows, nxt = await _books(session).list_items(_org(current_user), book_id, q=q, trade=trade,
    only_active=not include_inactive, after=after, limit=limit)
  _cursor(response, nxt)
  return rows

@router.post("/rate-books/{book_id}/items", response_model=RateItemResponse, status_code=201)
async def add_rate_item(
  book_id: UUID,
  payload: RateItemInput,
  current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _books(session).add_item(_org(current_user), current_user.id, book_id, payload)

@router.post("/rate-books/{book_id}/items/bulk", response_model=ImportResultResponse)
async def bulk_upsert_rate_items(
  book_id: UUID,
  payload: RateItemBulkRequest,
  current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _books(session).bulk_upsert(_org(current_user), current_user.id, book_id, payload.items)

@router.post("/rate-books/{book_id}/import", response_model=ImportResultResponse)
async def import_rate_items_csv(
  book_id: UUID,
  file: UploadFile = File(...),
  current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  content = await file.read(MAX_CSV_BYTES + 1)
  if len(content) > MAX_CSV_BYTES:
    raise TraceException("The CSV is larger than 5 MB.", status_code=413, code="RATE_IMPORT_TOO_LARGE")
  return await _books(session).import_csv(_org(current_user), current_user.id, book_id, content)

@router.patch("/rate-items/{item_id}", response_model=RateItemResponse)
async def update_rate_item(
  item_id: UUID,
  payload: RateItemUpdateRequest,
  current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _books(session).update_item(_org(current_user), current_user.id, item_id, payload)

@router.delete("/rate-items/{item_id}", status_code=204)
async def delete_rate_item(
  item_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  await _books(session).delete_item(_org(current_user), current_user.id, item_id)
  return Response(status_code=204)

@router.get("/rate-books/{book_id}/escalations", response_model=list[EscalationResponse])
async def list_escalations(
  book_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _books(session).list_escalations(_org(current_user), book_id)

@router.post("/rate-books/{book_id}/escalations", response_model=EscalationResponse, status_code=201)
async def add_escalation(
  book_id: UUID,
  payload: EscalationCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _books(session).add_escalation(_org(current_user), current_user.id, book_id, payload)

@router.delete("/rate-escalations/{escalation_id}", status_code=204)
async def delete_escalation(
  escalation_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  await _books(session).delete_escalation(_org(current_user), current_user.id, escalation_id)
  return Response(status_code=204)

@router.get("/rate-books/{book_id}/analyses", response_model=list[AnalysisResponse])
async def list_analyses(
  book_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _books(session).list_analyses(_org(current_user), book_id)

@router.post("/rate-books/{book_id}/analyses", response_model=AnalysisResponse, status_code=201)
async def create_analysis(
  book_id: UUID,
  payload: AnalysisCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _books(session).create_analysis(_org(current_user), current_user.id, book_id, payload)

@router.get("/rate-analyses/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(
  analysis_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _books(session).get_analysis(_org(current_user), analysis_id)

@router.patch("/rate-analyses/{analysis_id}", response_model=AnalysisResponse)
async def update_analysis(
  analysis_id: UUID,
  payload: AnalysisUpdateRequest,
  current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _books(session).update_analysis(_org(current_user), current_user.id, analysis_id, payload)

@router.delete("/rate-analyses/{analysis_id}", status_code=204)
async def delete_analysis(
  analysis_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  await _books(session).delete_analysis(_org(current_user), current_user.id, analysis_id)
  return Response(status_code=204)

@router.get("/rate-analyses/{analysis_id}/breakdown", response_model=AnalysisBreakdownResponse)
async def analysis_breakdown(
  analysis_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  svc = _books(session)
  return await svc.breakdown(_org(current_user), await svc.get_analysis(_org(current_user), analysis_id))

@router.post("/rate-analyses/{analysis_id}/compute", response_model=AnalysisResponse)
async def compute_analysis(
  analysis_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _books(session).compute_analysis(_org(current_user), current_user.id, analysis_id)

@router.post("/rate-analyses/{analysis_id}/apply", response_model=RateItemResponse)
async def apply_analysis(
  analysis_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.RATEBOOK_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _books(session).apply_analysis(_org(current_user), current_user.id, analysis_id)

@router.get("/projects/{project_id}/rate-overrides", response_model=list[OverrideResponse])
async def list_rate_overrides(
  project_id: UUID,
  response: Response,
  include_revoked: bool = Query(default=False),
  limit: int = Query(default=200, ge=1, le=1000),
  after: UUID | None = Query(default=None),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  rows, nxt = await _books(session).list_overrides(_org(current_user), project_id, include_revoked=include_revoked,
    after=after, limit=limit)
  _cursor(response, nxt)
  return rows

@router.post("/projects/{project_id}/rate-overrides", response_model=OverrideResponse, status_code=201)
async def create_rate_override(
  project_id: UUID,
  payload: OverrideCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.BOQ_ADJUST)),
  session: AsyncSession = Depends(get_db),
):
  return await _books(session).create_override(_org(current_user), current_user.id, project_id, payload)

@router.post("/rate-overrides/{override_id}/revoke", response_model=OverrideResponse)
async def revoke_rate_override(
  override_id: UUID,
  payload: OverrideRevokeRequest,
  current_user: User = Depends(require_permission(PermissionKey.BOQ_ADJUST)),
  session: AsyncSession = Depends(get_db),
):
  return await _books(session).revoke_override(_org(current_user), current_user.id, override_id, payload.reason)

@router.post("/boq-versions/{boq_version_id}/price", response_model=PriceVersionResponse)
async def price_boq_version(
  boq_version_id: UUID,
  payload: PriceVersionRequest | None = None,
  current_user: User = Depends(require_permission(PermissionKey.BOQ_UPDATE)),
  session: AsyncSession = Depends(get_db),
):
  return await PricingService(session).price_version(_org(current_user), boq_version_id, current_user.id,
    payload or PriceVersionRequest())

@router.get("/boq-versions/{boq_version_id}/pricing", response_model=PricingSummaryResponse)
async def boq_pricing_summary(
  boq_version_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await PricingService(session).summary(_org(current_user), boq_version_id)

@router.get("/boq-items/{item_id}/rate-resolution", response_model=RateExplainResponse)
async def explain_item_rate(
  item_id: UUID,
  as_of: date | None = Query(default=None),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await PricingService(session).explain_item(_org(current_user), item_id, as_of)

@router.get("/boq-versions/{version_a}/diff/{version_b}", response_model=DiffResponse)
async def diff_boq_versions(
  version_a: UUID,
  version_b: UUID,
  include_unchanged: bool = Query(default=False),
  include_elements: bool = Query(default=True),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await BOQDiffService(session).diff_versions(_org(current_user), version_a, version_b,
    include_unchanged=include_unchanged, include_elements=include_elements)