from __future__ import annotations
from app.modules.identity.models import User
from uuid import UUID
from app.modules.identity.enums import PermissionKey
from app.modules.drawings_boq.takeoff.extract.extract_schemas import (ExtractResponse, ExtractRequest, AcceptRequest, AcceptResponse, CandidateListResponse, DecideRequest, DecideResponse, 
  DrawingCandidatesResponse, DrawingExtractResponse, RegisterSyncResponse
)
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.modules.drawings_boq.takeoff.extract.extract_service import ExtractService
from app.modules.drawings_boq.takeoff.register_service import RegisterService
from app.modules.drawings_boq.takeoff.extract.floor_sources_schemas import ChooseFloorSourcesRequest, ChooseFloorSourcesResponse, FloorSourcesResponse
from app.modules.drawings_boq.takeoff.extract.floor_union_service import FloorUnionService
from app.modules.drawings_boq.takeoff.extract.layout_groups_schemas import ChooseLayoutsRequest, ChooseLayoutsResponse, LayoutGroupsResponse
from app.modules.drawings_boq.takeoff.extract.layout_groups_service import LayoutGroupService
from app.modules.drawings_boq.takeoff.extract.mark_entities_schemas import ChooseMarksRequest, ChooseMarksResponse, MarkEntitiesResponse
from app.modules.drawings_boq.takeoff.extract.mark_entities_service import MarkEntityService
from app.modules.drawings_boq.takeoff.extract.review_schemas import ConflictsResponse, LinksResponse, ResolveConflictsRequest, ResolveConflictsResponse, SteelRollupResponse
from app.modules.drawings_boq.takeoff.extract.review_service import ReviewService
from app.modules.drawings_boq.takeoff.approve_schemas import ApproveReadyRequest, ApproveReadyResponse
from app.modules.drawings_boq.takeoff.approve_service import ApproveService
from app.modules.drawings_boq.takeoff.extract.crosschecks_schemas import CrossChecksResponse, ReadyToAcceptResponse
from app.modules.drawings_boq.takeoff.extract.crosschecks_service import CrossCheckService
from app.modules.drawings_boq.takeoff.proof.schemas import FactsCheckRequest, FactsCheckResponse, TraceResponse
from app.modules.drawings_boq.takeoff.proof.service import ProofService
from app.modules.drawings_boq.takeoff.extract.typed_memory_schemas import TypedMemoryResponse
from app.modules.drawings_boq.takeoff.extract.typed_memory_service import TypedMemoryService

router = APIRouter()

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

_READ = PermissionKey.DRAWING_READ
_EDIT = PermissionKey.BOQ_UPDATE

@router.post("/takeoff/sheets/{sheet_id}/extract", response_model=ExtractResponse)
async def extract_sheet(
  sheet_id: UUID, payload: ExtractRequest | None = None,
  current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await FloorUnionService(session).extract_sheet(_org(current_user), sheet_id, current_user.id, payload or ExtractRequest())

@router.get("/takeoff/sheets/{sheet_id}/candidates", response_model=CandidateListResponse)
async def sheet_candidates(
  sheet_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  return await ExtractService(session).candidates(_org(current_user), sheet_id)

@router.post("/drawings/{drawing_id}/takeoff/extract", response_model=DrawingExtractResponse)
async def extract_drawing(
  drawing_id: UUID, payload: ExtractRequest | None = None,
   current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await FloorUnionService(session).extract_drawing(_org(current_user), drawing_id, current_user.id, payload or ExtractRequest())

@router.get("/drawings/{drawing_id}/takeoff/candidates", response_model=DrawingCandidatesResponse)
async def drawing_candidates(
  drawing_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  return await ExtractService(session).drawing_candidates(_org(current_user), drawing_id)

@router.post("/takeoff/candidates/accept", response_model=AcceptResponse)
async def accept_candidates(
  payload: AcceptRequest, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await ExtractService(session).accept(_org(current_user), current_user.id, payload)

@router.post("/takeoff/candidates/reject", response_model=DecideResponse)
async def reject_candidates(
  payload: DecideRequest, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await ExtractService(session).reject(_org(current_user), current_user.id, payload.ids)

@router.post("/takeoff/candidates/restore", response_model=DecideResponse)
async def restore_candidates(
  payload: DecideRequest, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
    return await ExtractService(session).restore(_org(current_user), current_user.id, payload.ids)

@router.post("/drawings/{drawing_id}/takeoff/register", response_model=RegisterSyncResponse)
async def sync_register(
  drawing_id: UUID, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await RegisterService(session).sync_and_commit(_org(current_user), drawing_id)

@router.get("/drawings/{drawing_id}/takeoff/floor-sources", response_model=FloorSourcesResponse)
async def floor_sources(
  drawing_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
   return await FloorUnionService(session).floor_sources(_org(current_user), drawing_id)

@router.post("/drawings/{drawing_id}/takeoff/floor-sources/choose", response_model=ChooseFloorSourcesResponse)
async def choose_floor_sources(
  drawing_id: UUID, payload: ChooseFloorSourcesRequest, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await FloorUnionService(session).choose(_org(current_user), current_user.id, drawing_id, payload)

@router.get("/drawings/{drawing_id}/takeoff/layout-groups", response_model=LayoutGroupsResponse)
async def layout_groups(
  drawing_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  return await LayoutGroupService(session).layout_groups(_org(current_user), drawing_id)

@router.post("/drawings/{drawing_id}/takeoff/layout-groups/choose", response_model=ChooseLayoutsResponse)
async def choose_layout_groups(
  drawing_id: UUID, payload: ChooseLayoutsRequest, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await LayoutGroupService(session).choose_layouts(_org(current_user), current_user.id, drawing_id, payload)

@router.get("/drawings/{drawing_id}/takeoff/mark-entities", response_model=MarkEntitiesResponse)
async def mark_entities(
  drawing_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  return await MarkEntityService(session).mark_entities(_org(current_user), drawing_id)

@router.post("/drawings/{drawing_id}/takeoff/mark-entities/choose", response_model=ChooseMarksResponse)
async def choose_mark_entities(
  drawing_id: UUID, payload: ChooseMarksRequest, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await MarkEntityService(session).choose_marks(_org(current_user), current_user.id, drawing_id, payload)

@router.post("/drawings/{drawing_id}/takeoff/floor-sources/combine", response_model=ChooseFloorSourcesResponse)
async def combine_floor_sources(
  drawing_id: UUID, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  """Lay the two sheets of each floor over each other, count what both show once, and keep what only one shows."""
  svc = FloorUnionService(session)
  out = await svc.combine(_org(current_user), current_user.id, drawing_id)
  return {"chosen": out["combined"], "set_aside": sum(c["set_aside"] for c in out["combined"]), "restored": sum(c["restored"] for c in out["combined"]),
    "blocked": out["skipped"], "floors": out["floors"]}

@router.get("/drawings/{drawing_id}/takeoff/conflicts", response_model=ConflictsResponse)
async def value_conflicts(
  drawing_id: UUID, slab_policy: str | None = None, beam_policy: str | None = None, count_policy: str | None = None,
  current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  """Values the drawing prints differently (a slab thickness on the architectural and the structural sheet, a beam section listed more than once, a mark counted
  differently by the two sheets of a floor), each with the quantity it gives and the one in force."""
  policy = {k: v for k, v in (("SLAB_THICKNESS", slab_policy), ("BEAM_SECTION", beam_policy), ("SOURCE_COUNT", count_policy)) if v}
  return await ReviewService(session).conflicts(_org(current_user), drawing_id, policy)

@router.post("/drawings/{drawing_id}/takeoff/conflicts/resolve", response_model=ResolveConflictsResponse)
async def resolve_value_conflicts(
  drawing_id: UUID, payload: ResolveConflictsRequest, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await ReviewService(session).resolve(_org(current_user), current_user.id, drawing_id, payload)

@router.get("/drawings/{drawing_id}/takeoff/links", response_model=LinksResponse)
async def member_links(
  drawing_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  """For each beam, plinth beam, footing, neck column and tank: whether the detail the drawing prints for it was found and put on it."""
  return await ReviewService(session).links(_org(current_user), drawing_id)

@router.get("/drawings/{drawing_id}/takeoff/steel-rollup", response_model=SteelRollupResponse)
async def steel_rollup(
  drawing_id: UUID, cover_mm: float | None = None, hook_dia: float | None = None, lap_dia: float | None = None, anchor_dia: float | None = None, wastage_pct: float | None = None,
  current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  """The reinforcement weight of the items as they stand, from the bars printed or typed with them, before a calculation run."""
  given = {k: v for k, v in (("cover_mm", cover_mm), ("hook_dia", hook_dia), ("lap_dia", lap_dia), ("anchor_dia", anchor_dia), ("wastage_pct", wastage_pct)) if v is not None}
  return await ReviewService(session).steel_rollup(_org(current_user), drawing_id, given or None)

@router.post("/drawings/{drawing_id}/takeoff/approve", response_model=ApproveReadyResponse)
async def approve_ready(
  drawing_id: UUID, payload: ApproveReadyRequest | None = None, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await ApproveService(session).approve(_org(current_user), current_user.id, drawing_id, payload or ApproveReadyRequest())

@router.get("/drawings/{drawing_id}/takeoff/checks", response_model=CrossChecksResponse)
async def cross_checks(
  drawing_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  return await CrossCheckService(session).checks(_org(current_user), drawing_id)

@router.get("/drawings/{drawing_id}/takeoff/ready", response_model=ReadyToAcceptResponse)
async def ready_to_accept(
  drawing_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  return await CrossCheckService(session).ready_to_accept(_org(current_user), drawing_id)

@router.get("/drawings/{drawing_id}/takeoff/typed-memory", response_model=TypedMemoryResponse)
async def typed_memory(
  drawing_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  return await TypedMemoryService(session).memory(_org(current_user), drawing_id)

@router.post("/drawings/{drawing_id}/takeoff/facts-check", response_model=FactsCheckResponse)
async def facts_check(
  drawing_id: UUID, payload: FactsCheckRequest, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  return await ProofService(session).facts_check(_org(current_user), drawing_id, payload)

@router.get("/drawings/{drawing_id}/takeoff/trace", response_model=TraceResponse)
async def reader_trace(
  drawing_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  return await ProofService(session).trace(_org(current_user), drawing_id)
