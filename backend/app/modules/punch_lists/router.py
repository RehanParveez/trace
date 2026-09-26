from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.punch_lists.service import PunchListService
from app.modules.punch_lists.schemas import ( PunchListResponse, PunchListCreateRequest, ProjectPunchListSummaryResponse, PunchListDetailResponse, PunchListItemCreateRequest, PunchListItemPhotoCreateRequest, PunchListItemPhotoResponse,
  PunchListItemResponse, PunchListItemUpdateRequest
)
from uuid import UUID
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.modules.identity.models import User
from app.modules.identity.enums import PermissionKey

router = APIRouter(prefix="/punch-lists", tags=["Punch Lists"])

def _service(session: AsyncSession) -> PunchListService:
  return PunchListService(session)

@router.post("", response_model=PunchListResponse, status_code=201)
async def create_punch_list(
  payload: PunchListCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.PUNCH_LIST_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).create_punch_list(current_user.active_membership.organization_id, payload, current_user.id)

@router.get("", response_model=list[PunchListDetailResponse])
async def list_punch_lists(
  project_id: UUID = Query(...),
  current_user: User = Depends(require_permission(PermissionKey.PUNCH_LIST_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).list_punch_lists(current_user.active_membership.organization_id, project_id)

@router.get("/{punch_list_id}", response_model=PunchListDetailResponse)
async def get_punch_list(
  punch_list_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.PUNCH_LIST_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).get_punch_list(current_user.active_membership.organization_id, punch_list_id)

@router.get("/projects/{project_id}/summary", response_model=ProjectPunchListSummaryResponse)
async def get_project_summary(
  project_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.PUNCH_LIST_READ)),
  session: AsyncSession = Depends(get_db),
):
  data = await _service(session).get_project_summary(current_user.active_membership.organization_id, project_id)
  return ProjectPunchListSummaryResponse(**data)

@router.post("/{punch_list_id}/close", response_model=PunchListResponse)
async def close_punch_list(
  punch_list_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.PUNCH_LIST_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).close_punch_list(current_user.active_membership.organization_id, punch_list_id, current_user.id)

@router.post("/{punch_list_id}/items", response_model=PunchListItemResponse, status_code=201)
async def add_item(
  punch_list_id: UUID,
  payload: PunchListItemCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.PUNCH_LIST_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).add_item(current_user.active_membership.organization_id, punch_list_id, payload, current_user.id)

@router.patch("/items/{item_id}", response_model=PunchListItemResponse)
async def update_item(
  item_id: UUID,
  payload: PunchListItemUpdateRequest,
  current_user: User = Depends(require_permission(PermissionKey.PUNCH_LIST_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).update_item(current_user.active_membership.organization_id, item_id, payload, current_user.id)

@router.post("/items/{item_id}/photos", response_model=PunchListItemPhotoResponse, status_code=201)
async def add_photo(
  item_id: UUID,
  payload: PunchListItemPhotoCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.PUNCH_LIST_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).add_photo(current_user.active_membership.organization_id, item_id, payload)

@router.delete("/photos/{link_id}")
async def remove_photo(
  link_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.PUNCH_LIST_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  await _service(session).remove_photo(current_user.active_membership.organization_id, link_id)
  return {"message": "Photo removed."}