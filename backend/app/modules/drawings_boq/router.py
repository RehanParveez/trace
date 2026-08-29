from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, File, Header, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.permissions import require_permission
from app.modules.drawings_boq.schemas import BOQItemResponse, BOQItemUpdateRequest, BOQVersionResponse, DrawingElementResponse, DrawingResponse, MaterialLibraryCreateRequest, MaterialLibraryResponse
from app.modules.drawings_boq.service import DrawingBOQService
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User

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
    current_user.organization_id,
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
    current_user.organization_id,
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
    current_user.organization_id,
    drawing_id,
  )

@router.get(
  "/drawings/{drawing_id}/elements",
  response_model=list[DrawingElementResponse],
)
async def list_drawing_elements(
  drawing_id: UUID,
  current_user: User = Depends(
    require_permission(PermissionKey.DRAWING_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.list_elements(
    current_user.organization_id,
    drawing_id,
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
    current_user.organization_id,
    project_id,
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
    current_user.organization_id,
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
    current_user.organization_id,
    item_id,
    payload,
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
    current_user.organization_id,
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
    current_user.organization_id,
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
    current_user.organization_id,
  )