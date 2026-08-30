from __future__ import annotations
import json
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.permissions import require_permission
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from app.modules.whatsapp.schemas import (ChannelConnectRequest, ChannelResponse, PhotoTagCreateRequest, PhotoTagResponse, SitePhotoAssignProjectRequest,
 SitePhotoResponse, SitePhotoUpdateRequest,
)
from app.modules.whatsapp.service import WhatsAppService

router = APIRouter(
  prefix="/whatsapp",
  tags=["WhatsApp & Site Photos"],
)

def _service(session: AsyncSession) -> WhatsAppService:
  return WhatsAppService(session)

@router.get("/webhook")
async def verify_webhook(
  hub_mode: str | None = Query(default=None, alias="hub.mode"),
  hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
  hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
):
  if WhatsAppService.verify_subscription_challenge(hub_mode, hub_verify_token):
    return Response(content=hub_challenge or "", media_type="text/plain")
  return Response(status_code=403)

@router.post("/webhook")
async def receive_webhook(
  request: Request,
  session: AsyncSession = Depends(get_db),
):
  raw_body = await request.body()
  signature = request.headers.get("X-Hub-Signature-256")
  if not WhatsAppService.verify_signature(raw_body, signature):
    return Response(status_code=403)
  payload = json.loads(raw_body)
  service = _service(session)
  await service.handle_webhook_payload(payload)

  return {"status": "received"}

@router.post(
  "/channel",
  response_model=ChannelResponse,
  status_code=status.HTTP_201_CREATED,
)
async def connect_channel(
  payload: ChannelConnectRequest,
  current_user: User = Depends(
    require_permission(PermissionKey.WHATSAPP_CHANNEL_MANAGE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.connect_channel(
    current_user.organization_id, payload
  )

@router.get("/channel", response_model=ChannelResponse)
async def get_channel(
  current_user: User = Depends(
    require_permission(PermissionKey.WHATSAPP_CHANNEL_MANAGE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.get_channel(current_user.organization_id)

@router.delete("/channel", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_channel(
  current_user: User = Depends(
    require_permission(PermissionKey.WHATSAPP_CHANNEL_MANAGE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  await service.disconnect_channel(current_user.organization_id)

@router.get("/photos", response_model=list[SitePhotoResponse])
async def list_photos(
  project_id: UUID | None = Query(default=None),
  tag: str | None = Query(default=None),
  skip: int = Query(default=0, ge=0),
  limit: int = Query(default=100, ge=1, le=100),
  current_user: User = Depends(
    require_permission(PermissionKey.SITE_PHOTO_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.list_photos(
    current_user.organization_id,
    project_id=project_id,
    tag=tag,
    skip=skip,
    limit=limit,
  )

@router.get("/photos/{photo_id}", response_model=SitePhotoResponse)
async def get_photo(
  photo_id: UUID,
  current_user: User = Depends(
    require_permission(PermissionKey.SITE_PHOTO_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.get_photo(
    current_user.organization_id, photo_id
  )

@router.patch("/photos/{photo_id}", response_model=SitePhotoResponse)
async def update_photo(
  photo_id: UUID,
  payload: SitePhotoUpdateRequest,
  current_user: User = Depends(
    require_permission(PermissionKey.SITE_PHOTO_MANAGE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.update_photo(
    current_user.organization_id, photo_id, payload
  )

@router.post(
  "/photos/{photo_id}/assign-project",
  response_model=SitePhotoResponse,
)
async def assign_project(
  photo_id: UUID,
  payload: SitePhotoAssignProjectRequest,
  current_user: User = Depends(
    require_permission(PermissionKey.SITE_PHOTO_MANAGE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.assign_project(
    current_user.organization_id, photo_id, payload
  )

@router.post(
  "/photos/{photo_id}/tags",
  response_model=PhotoTagResponse,
  status_code=status.HTTP_201_CREATED,
)
async def add_tag(
  photo_id: UUID,
  payload: PhotoTagCreateRequest,
  current_user: User = Depends(
    require_permission(PermissionKey.SITE_PHOTO_MANAGE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.add_tag(
    current_user.organization_id, photo_id, payload
  )

@router.delete(
  "/photos/{photo_id}/tags/{tag_id}",
  status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_tag(
  photo_id: UUID,
  tag_id: UUID,
  current_user: User = Depends(
    require_permission(PermissionKey.SITE_PHOTO_MANAGE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  await service.remove_tag(
    current_user.organization_id, photo_id, tag_id
  )