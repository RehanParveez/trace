from __future__ import annotations
from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Depends, File, Header, Query, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.permissions import require_permission
from app.modules.drawings_boq.schemas import ( BOQCustomItemCreateRequest, BOQItemResponse, BOQItemUpdateRequest, BOQSummaryResponse, BOQVersionCreateRequest, BOQVersionResponse, BOQVersionUpdateRequest, 
  DrawingElementResponse, DrawingResponse, LabourRateCreateRequest, LabourRateResponse, LabourRateUpdateRequest, MaterialLibraryCreateRequest, MaterialLibraryResponse, MaterialLibraryUpdateRequest,
   PDFExtractionResultResponse, ProjectBOQCountResponse, BuildingLevelResponse, ModelAuditResponse, CalculationRunResponse, CalculationRunCreateRequest, RunStageResponse, QuantitySolidResponse, LedgerRowResponse,
   DeductionResponse, AdjustmentCreateRequest, AdjustmentResponse, BOQBuildResponse, ItemTraceResponse, ReasonRequest, ReviewIssueResponse, ReviewIssueUpdateRequest, SnapshotItemResponse, SnapshotResponse, 
   TransitionRequest
)
from app.modules.drawings_boq.service import DrawingBOQService
from app.modules.drawings_boq.calc_service import CalculationService
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from fastapi.responses import Response
from app.modules.drawings_boq.boq_service import BOQEngineService

router = APIRouter(
  prefix="/drawings-boq",
  tags=["Drawings & BOQ"],
)

def _service(session: AsyncSession) -> DrawingBOQService:
  return DrawingBOQService(session)

@router.post(
  "/projects/{project_id}/drawings",
  response_model=DrawingResponse,
  status_code=201,
)
async def upload_drawing(
  project_id: UUID,
  file: UploadFile = File(...),
  idempotency_key: str | None = Header(
    default=None, alias="Idempotency-Key"
  ),
  current_user: User = Depends(
    require_permission(PermissionKey.DRAWING_CREATE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.upload_drawing(
    current_user.active_membership.organization_id,
    project_id,
    current_user.id,
    file,
    idempotency_key,
  )

@router.get(
  "/projects/{project_id}/drawings",
  response_model=list[DrawingResponse],
)
async def list_drawings(
  project_id: UUID,
  current_user: User = Depends(
    require_permission(PermissionKey.DRAWING_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.list_drawings(
    current_user.active_membership.organization_id,
    project_id,
  )

@router.get(
  "/drawings/{drawing_id}",
  response_model=DrawingResponse,
)
async def get_drawing(
  drawing_id: UUID,
  current_user: User = Depends(
    require_permission(PermissionKey.DRAWING_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.get_drawing(
    current_user.active_membership.organization_id,
    drawing_id,
  )
  
@router.post(
  "/drawings/{drawing_id}/suggest-items",
  response_model=PDFExtractionResultResponse,
)
async def suggest_boq_items_from_pdf(
  drawing_id: UUID,
  current_user: User = Depends(
    require_permission(PermissionKey.BOQ_ITEM_CREATE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.suggest_items_from_pdf(
    current_user.active_membership.organization_id,
    drawing_id,
    current_user.id,
  )

@router.get(
  "/drawings/{drawing_id}/elements",
  response_model=list[DrawingElementResponse],
)
async def list_drawing_elements(
  drawing_id: UUID,
  response: Response,
  limit: int = Query(default=2000, ge=1, le=5000),
  cursor: str | None = Query(default=None),
  structural_role: str | None = Query(default=None, max_length=30),
  discipline: str | None = Query(default=None, max_length=20),
  level_id: UUID | None = Query(default=None),
  normalization_status: Literal["PENDING", "VALID", "WARNING", "INVALID"] | None = Query(default=None),
  ifc_type: str | None = Query(default=None, max_length=100),
  current_user: User = Depends(
    require_permission(PermissionKey.DRAWING_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  elements, next_cursor = await service.list_elements_page(
    current_user.active_membership.organization_id,
    drawing_id,
    limit=limit,
    cursor=cursor,
    structural_role=structural_role,
    discipline=discipline,
    level_id=level_id,
    normalization_status=normalization_status,
    ifc_type=ifc_type,
  )
  if next_cursor:
    response.headers["X-Next-Cursor"] = next_cursor
  return elements

@router.get(
  "/drawings/{drawing_id}/levels",
  response_model=list[BuildingLevelResponse],
)
async def list_drawing_levels(
  drawing_id: UUID,
  current_user: User = Depends(
    require_permission(PermissionKey.DRAWING_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.list_levels(
    current_user.active_membership.organization_id,
    drawing_id,
  )

@router.get(
  "/drawings/{drawing_id}/audit",
  response_model=ModelAuditResponse,
)
async def get_drawing_audit(
  drawing_id: UUID,
  current_user: User = Depends(
    require_permission(PermissionKey.DRAWING_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.get_latest_audit(
    current_user.active_membership.organization_id,
    drawing_id,
  )

@router.get("/drawings/{drawing_id}/file")
async def get_drawing_file(
  drawing_id: UUID,
  current_user: User = Depends(
    require_permission(PermissionKey.DRAWING_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  contents, media_type, filename = await service.get_drawing_file(
    current_user.active_membership.organization_id,
    drawing_id,
  )
  return Response(
    content=contents,
    media_type=media_type,
    headers={"Content-Disposition": f'inline; filename="{filename}"'},
  )

@router.get(
  "/projects/{project_id}/boq-versions",
  response_model=list[BOQVersionResponse],
)
async def list_boq_versions(
  project_id: UUID,
  current_user: User = Depends(
    require_permission(PermissionKey.DRAWING_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.list_boq_versions(
    current_user.active_membership.organization_id,
    project_id,
  )

@router.post(
  "/projects/{project_id}/boq-versions",
  response_model=BOQVersionResponse,
  status_code=201,
)
async def create_boq_version(
  project_id: UUID,
  payload: BOQVersionCreateRequest,
  current_user: User = Depends(
    require_permission(PermissionKey.BOQ_ITEM_CREATE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.create_boq_version(
    current_user.active_membership.organization_id,
    project_id,
    payload,
  )

@router.get(
  "/boq-versions/{boq_version_id}/items",
  response_model=list[BOQItemResponse],
)
async def list_boq_items(
  boq_version_id: UUID,
  current_user: User = Depends(
    require_permission(PermissionKey.DRAWING_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.list_boq_items(
    current_user.active_membership.organization_id,
    boq_version_id,
  )

@router.patch(
  "/boq-items/{item_id}",
  response_model=BOQItemResponse,
)
async def update_boq_item(
  item_id: UUID,
  payload: BOQItemUpdateRequest,
  current_user: User = Depends(
    require_permission(PermissionKey.BOQ_UPDATE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.update_boq_item(
    current_user.active_membership.organization_id,
    item_id,
    current_user.id,
    payload,
  )

@router.delete(
  "/boq-items/{item_id}",
  status_code=204,
)
async def delete_boq_item(
  item_id: UUID,
  current_user: User = Depends(
    require_permission(PermissionKey.BOQ_UPDATE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  await service.delete_boq_item(
    current_user.active_membership.organization_id,
    item_id,
    current_user.id,
  )

@router.post(
  "/boq-items/{item_id}/approve",
  response_model=BOQItemResponse,
)
async def approve_boq_item(
  item_id: UUID,
  current_user: User = Depends(
    require_permission(PermissionKey.BOQ_APPROVE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.approve_boq_item(
    current_user.active_membership.organization_id,
    item_id,
    current_user.id,
  )

@router.post(
  "/material-library",
  response_model=MaterialLibraryResponse,
  status_code=201,
)
async def create_material_library_entry(
  payload: MaterialLibraryCreateRequest,
  current_user: User = Depends(
    require_permission(PermissionKey.MATERIAL_LIBRARY_MANAGE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.create_material_library_entry(
    current_user.active_membership.organization_id,
    payload,
  )

@router.get(
  "/material-library",
  response_model=list[MaterialLibraryResponse],
)
async def list_material_library(
  current_user: User = Depends(
    require_permission(PermissionKey.DRAWING_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.list_material_library(
    current_user.active_membership.organization_id,
  )
  
@router.patch(
  "/material-library/{entry_id}",
  response_model=MaterialLibraryResponse,
)
async def update_material_library_entry(
  entry_id: UUID,
  payload: MaterialLibraryUpdateRequest,
  current_user: User = Depends(
    require_permission(PermissionKey.MATERIAL_LIBRARY_MANAGE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.update_material_library_entry(
    current_user.active_membership.organization_id, entry_id, payload,
  )

@router.post(
  "/labour-rates",
  response_model=LabourRateResponse,
  status_code=201,
)
async def create_labour_rate(
  payload: LabourRateCreateRequest,
  current_user: User = Depends(
    require_permission(PermissionKey.LABOUR_RATE_MANAGE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.create_labour_rate(current_user.active_membership.organization_id, payload)

@router.get(
  "/labour-rates",
  response_model=list[LabourRateResponse],
)
async def list_labour_rates(
  current_user: User = Depends(
    require_permission(PermissionKey.DRAWING_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.list_labour_rates(current_user.active_membership.organization_id)

@router.patch(
  "/labour-rates/{rate_id}",
  response_model=LabourRateResponse,
)
async def update_labour_rate(
  rate_id: UUID,
  payload: LabourRateUpdateRequest,
  current_user: User = Depends(
    require_permission(PermissionKey.LABOUR_RATE_MANAGE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.update_labour_rate(
    current_user.active_membership.organization_id, rate_id, payload,
  )
  
@router.get(
  "/boq-item-counts",
  response_model=list[ProjectBOQCountResponse],
)
async def get_boq_item_counts(
  current_user: User = Depends(
    require_permission(PermissionKey.DRAWING_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.get_project_boq_counts(
    current_user.active_membership.organization_id,
  )

@router.post(
  "/boq-versions/{boq_version_id}/items",
  response_model=BOQItemResponse,
  status_code=201,
)
async def add_custom_boq_item(
  boq_version_id: UUID,
  payload: BOQCustomItemCreateRequest,
  current_user: User = Depends(
    require_permission(PermissionKey.BOQ_ITEM_CREATE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.add_custom_boq_item(
    current_user.active_membership.organization_id, boq_version_id, current_user.id, payload,
  )

@router.patch(
  "/boq-versions/{boq_version_id}",
  response_model=BOQVersionResponse,
)
async def update_boq_version(
  boq_version_id: UUID,
  payload: BOQVersionUpdateRequest,
  current_user: User = Depends(
    require_permission(PermissionKey.BOQ_UPDATE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.update_boq_version(
    current_user.active_membership.organization_id, boq_version_id, payload,
  )

@router.post(
  "/boq-versions/{boq_version_id}/labour/generate",
  response_model=list[BOQItemResponse],
)
async def generate_labour_items(
  boq_version_id: UUID,
  current_user: User = Depends(
    require_permission(PermissionKey.BOQ_UPDATE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.generate_labour_items(
    current_user.active_membership.organization_id, boq_version_id,
  )

@router.get(
  "/boq-versions/{boq_version_id}/summary",
  response_model=BOQSummaryResponse,
)
async def get_boq_summary(
  boq_version_id: UUID,
  current_user: User = Depends(
    require_permission(PermissionKey.DRAWING_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.get_boq_summary(
    current_user.active_membership.organization_id, boq_version_id,
  )

@router.get("/boq-versions/{boq_version_id}/export/pdf")
async def export_boq_pdf(
  boq_version_id: UUID,
  current_user: User = Depends(
    require_permission(PermissionKey.BOQ_EXPORT)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  pdf_bytes, filename = await service.export_boq_pdf(
    current_user.active_membership.organization_id, boq_version_id,
  )
  return Response(
    content=pdf_bytes,
    media_type="application/pdf",
    headers={"Content-Disposition": f'attachment; filename="{filename}"'},
  )

@router.get("/boq-versions/{boq_version_id}/export/xlsx")
async def export_boq_xlsx(
  boq_version_id: UUID,
  current_user: User = Depends(
    require_permission(PermissionKey.BOQ_EXPORT)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  xlsx_bytes, filename = await service.export_boq_xlsx(
    current_user.active_membership.organization_id, boq_version_id,
  )
  return Response(
    content=xlsx_bytes,
    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    headers={"Content-Disposition": f'attachment; filename="{filename}"'},
  )
  
@router.delete(
  "/drawings/{drawing_id}",
  status_code=204,
)
async def delete_drawing(
  drawing_id: UUID,
  current_user: User = Depends(
    require_permission(PermissionKey.DRAWING_DELETE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  await service.delete_drawing(
    current_user.active_membership.organization_id,
    drawing_id,
    current_user.id,
  )
  
@router.post("/drawings/{drawing_id}/revise", response_model=DrawingResponse, status_code=201)
async def revise_drawing(
  drawing_id: UUID,
  file: UploadFile = File(...),
  revision_label: str | None = Form(default=None),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_CREATE)),
  session: AsyncSession = Depends(get_db),
  idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
  service = _service(session)
  previous = await service.get_drawing(current_user.active_membership.organization_id, drawing_id)
  return await service.create_revision(
    current_user.active_membership.organization_id, previous.project_id, drawing_id,
    current_user.id, file, revision_label, idempotency_key,
  )

@router.get("/drawings/{drawing_id}/revisions", response_model=list[DrawingResponse])
async def list_drawing_revisions(
  drawing_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.list_revisions(current_user.active_membership.organization_id, drawing_id)

@router.get(
  "/boq-items/{boq_item_id}/source-elements",
  response_model=list[DrawingElementResponse],
)
async def list_boq_item_source_elements(
  boq_item_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.list_boq_item_source_elements(
    current_user.active_membership.organization_id, boq_item_id,
  )
  
@router.post(
  "/projects/{project_id}/calculation-runs",
  response_model=CalculationRunResponse,
  status_code=202,
)
async def start_calculation_run(
  project_id: UUID,
  response: Response,
  payload: CalculationRunCreateRequest | None = None,
  current_user: User = Depends(require_permission(PermissionKey.CALC_RUN)),
  session: AsyncSession = Depends(get_db),
):
  payload = payload or CalculationRunCreateRequest()
  run, reused = await CalculationService(session).request_run(
    current_user.active_membership.organization_id,
    project_id,
    current_user.id,
    payload.drawing_ids,
    payload.rule_set_code,
    payload.convention_code,
  )
  if reused:
    response.status_code = 200
  return run

@router.get("/calculation-runs/{run_id}", response_model=CalculationRunResponse)
async def get_calculation_run(
  run_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await CalculationService(session).get_run(current_user.active_membership.organization_id, run_id)

@router.get("/calculation-runs/{run_id}/stages", response_model=list[RunStageResponse])
async def list_calculation_run_stages(
  run_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await CalculationService(session).list_stages(current_user.active_membership.organization_id, run_id)

@router.get("/calculation-runs/{run_id}/solids", response_model=list[QuantitySolidResponse])
async def list_calculation_run_solids(
  run_id: UUID,
  response: Response,
  limit: int = Query(default=500, ge=1, le=2000),
  after: UUID | None = Query(default=None),
  role: str | None = Query(default=None, max_length=30),
  level_id: UUID | None = Query(default=None),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  rows, next_cursor = await CalculationService(session).list_solids(
    current_user.active_membership.organization_id, run_id,
    limit=limit, after=after, role=role, level_id=level_id,
  )
  if next_cursor:
    response.headers["X-Next-Cursor"] = str(next_cursor)
  return rows

@router.get("/calculation-runs/{run_id}/ledger", response_model=list[LedgerRowResponse])
async def list_calculation_run_ledger(
  run_id: UUID,
  response: Response,
  limit: int = Query(default=500, ge=1, le=2000),
  after: UUID | None = Query(default=None),
  work_item_code: str | None = Query(default=None, max_length=50),
  level_id: UUID | None = Query(default=None),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  rows, next_cursor = await CalculationService(session).list_ledger(
    current_user.active_membership.organization_id, run_id,
    limit=limit, after=after, work_item_code=work_item_code, level_id=level_id,
  )
  if next_cursor:
    response.headers["X-Next-Cursor"] = str(next_cursor)
  return rows

@router.get("/calculation-runs/{run_id}/deductions", response_model=list[DeductionResponse])
async def list_calculation_run_deductions(
  run_id: UUID,
  response: Response,
  limit: int = Query(default=500, ge=1, le=2000),
  after: UUID | None = Query(default=None),
  from_solid_id: UUID | None = Query(default=None),
  deduction_type: Literal["OVERLAP_ALLOCATION", "EXTENT_TRIMMING", "VOID_DEDUCTION",
    "MATERIAL_SUBSTITUTION", "MEASUREMENT_CONVENTION"] | None = Query(default=None),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  rows, next_cursor = await CalculationService(session).list_deductions(
    current_user.active_membership.organization_id, run_id,
    limit=limit, after=after, from_solid_id=from_solid_id, deduction_type=deduction_type,
  )
  if next_cursor:
    response.headers["X-Next-Cursor"] = str(next_cursor)
  return rows

def _engine(session: AsyncSession) -> BOQEngineService:
  return BOQEngineService(session)

@router.post("/calculation-runs/{run_id}/boq", response_model=BOQBuildResponse)
async def build_boq_from_run(
  run_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.CALC_RUN)),
  session: AsyncSession = Depends(get_db),
):
  return await _engine(session).build_from_run(current_user.active_membership.organization_id, run_id, current_user.id)

@router.post("/boq-versions/{boq_version_id}/submit-review", response_model=BOQVersionResponse)
async def submit_boq_for_review(
  boq_version_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.BOQ_UPDATE)),
  session: AsyncSession = Depends(get_db),
):
  return await _engine(session).submit_for_review(current_user.active_membership.organization_id, boq_version_id, current_user.id)

@router.post("/boq-versions/{boq_version_id}/reopen", response_model=BOQVersionResponse)
async def reopen_boq_version(
  boq_version_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.BOQ_APPROVE)),
  session: AsyncSession = Depends(get_db),
):
  return await _engine(session).reopen(current_user.active_membership.organization_id, boq_version_id, current_user.id)

@router.post("/boq-versions/{boq_version_id}/approve", response_model=BOQVersionResponse)
async def approve_boq_version(
  boq_version_id: UUID,
  payload: TransitionRequest | None = None,
  current_user: User = Depends(require_permission(PermissionKey.BOQ_APPROVE)),
  session: AsyncSession = Depends(get_db),
):
  return await _engine(session).approve_version(
    current_user.active_membership.organization_id, boq_version_id, current_user.id, payload.note if payload else None)

@router.post("/boq-versions/{boq_version_id}/issue", response_model=BOQVersionResponse)
async def issue_boq_version(
  boq_version_id: UUID,
  payload: TransitionRequest | None = None,
  current_user: User = Depends(require_permission(PermissionKey.BOQ_ISSUE)),
  session: AsyncSession = Depends(get_db),
):
  return await _engine(session).issue_version(
    current_user.active_membership.organization_id, boq_version_id, current_user.id, payload.note if payload else None)

@router.post("/boq-versions/{boq_version_id}/archive", response_model=BOQVersionResponse)
async def archive_boq_version(
  boq_version_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.BOQ_ISSUE)),
  session: AsyncSession = Depends(get_db),
):
  return await _engine(session).archive_version(current_user.active_membership.organization_id, boq_version_id, current_user.id)

@router.get("/boq-versions/{boq_version_id}/snapshots", response_model=list[SnapshotResponse])
async def list_boq_snapshots(
  boq_version_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _engine(session).list_snapshots(current_user.active_membership.organization_id, boq_version_id)

@router.get("/boq-snapshots/{snapshot_id}/items", response_model=list[SnapshotItemResponse])
async def list_boq_snapshot_items(
  snapshot_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _engine(session).snapshot_items(current_user.active_membership.organization_id, snapshot_id)

@router.get("/boq-versions/{boq_version_id}/ledger", response_model=list[LedgerRowResponse])
async def list_boq_version_ledger(
  boq_version_id: UUID,
  response: Response,
  limit: int = Query(default=500, ge=1, le=2000),
  after: UUID | None = Query(default=None),
  work_item_code: str | None = Query(default=None, max_length=50),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  rows, next_cursor = await _engine(session).ledger_for_version(
    current_user.active_membership.organization_id, boq_version_id,
    limit=limit, after=after, work_item_code=work_item_code)
  if next_cursor:
    response.headers["X-Next-Cursor"] = str(next_cursor)
  return rows

@router.get("/boq-items/{item_id}/trace", response_model=ItemTraceResponse)
async def get_boq_item_trace(
  item_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _engine(session).item_trace(current_user.active_membership.organization_id, item_id)

@router.get("/boq-items/{item_id}/adjustments", response_model=list[AdjustmentResponse])
async def list_boq_item_adjustments(
  item_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _engine(session).list_adjustments(current_user.active_membership.organization_id, item_id)

@router.post("/boq-items/{item_id}/adjustments", response_model=AdjustmentResponse, status_code=201)
async def create_boq_item_adjustment(
  item_id: UUID,
  payload: AdjustmentCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.BOQ_ADJUST)),
  session: AsyncSession = Depends(get_db),
):
  return await _engine(session).add_adjustment(
    current_user.active_membership.organization_id, item_id, current_user.id, payload.kind, payload.value, payload.reason)

@router.post("/boq-adjustments/{adjustment_id}/revoke", response_model=AdjustmentResponse)
async def revoke_boq_adjustment(
  adjustment_id: UUID,
  payload: ReasonRequest,
  current_user: User = Depends(require_permission(PermissionKey.BOQ_ADJUST)),
  session: AsyncSession = Depends(get_db),
):
  return await _engine(session).revoke_adjustment(
    current_user.active_membership.organization_id, adjustment_id, current_user.id, payload.reason)

@router.post("/boq-items/{item_id}/waive-review", response_model=BOQItemResponse)
async def waive_boq_item_review(
  item_id: UUID,
  payload: ReasonRequest,
  current_user: User = Depends(require_permission(PermissionKey.BOQ_UPDATE)),
  session: AsyncSession = Depends(get_db),
):
  return await _engine(session).waive_item_review(
    current_user.active_membership.organization_id, item_id, current_user.id, payload.reason)

@router.post("/boq-items/{item_id}/confirm-rate", response_model=BOQItemResponse)
async def confirm_boq_item_rate(
  item_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.BOQ_UPDATE)),
  session: AsyncSession = Depends(get_db),
):
  return await _engine(session).confirm_rate(current_user.active_membership.organization_id, item_id, current_user.id)

@router.get("/review-issues", response_model=list[ReviewIssueResponse])
async def list_review_issues(
  project_id: UUID = Query(...),
  boq_version_id: UUID | None = Query(default=None),
  status: Literal["OPEN", "RESOLVED", "WAIVED"] | None = Query(default=None),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _engine(session).list_issues(
    current_user.active_membership.organization_id, project_id, status, boq_version_id)

@router.patch("/review-issues/{issue_id}", response_model=ReviewIssueResponse)
async def update_review_issue(
  issue_id: UUID,
  payload: ReviewIssueUpdateRequest,
  current_user: User = Depends(require_permission(PermissionKey.REVIEW_RESOLVE)),
  session: AsyncSession = Depends(get_db),
):
  return await _engine(session).resolve_issue(
    current_user.active_membership.organization_id, issue_id, current_user.id, payload.status, payload.note)

@router.get("/boq-versions/{boq_version_id}/exports/{kind}")
async def export_boq_snapshot(
  boq_version_id: UUID,
  kind: Literal["CONTRACT_BOQ", "PROCUREMENT", "MEASUREMENT_BOOK", "AUDIT_REPORT", "REVISION_COMPARISON", "BBS"],
  fmt: Literal["pdf", "xlsx"] = Query(default="pdf"),
  snapshot_id: UUID | None = Query(default=None),
  current_user: User = Depends(require_permission(PermissionKey.BOQ_EXPORT)),
  session: AsyncSession = Depends(get_db),
):
  data, media, filename = await _engine(session).export_snapshot(
    current_user.active_membership.organization_id, boq_version_id, kind, fmt, current_user.id, snapshot_id)
  return Response(content=data, media_type=media, headers={"Content-Disposition": f'attachment; filename="{filename}"'})