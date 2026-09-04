from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.modules.identity.models import User
from app.modules.notifications.schemas import NotificationResponse, UnreadCountResponse, MessageResponse
from app.modules.notifications.service import NotificationService

router = APIRouter(
  prefix="/notifications",
  tags=["Notifications"],
)

def _service(session: AsyncSession) -> NotificationService:
  return NotificationService(session)

@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
  unread_only: bool = Query(default=False),
  skip: int = Query(default=0, ge=0),
  limit: int = Query(default=50, ge=1, le=100),
  current_user: User = Depends(get_current_user),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.list_notifications(
    current_user.active_membership.organization_id,
    current_user.id,
    unread_only=unread_only,
    skip=skip,
    limit=limit,
  )

@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
  current_user: User = Depends(get_current_user),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  count = await service.get_unread_count(
    current_user.active_membership.organization_id, current_user.id
  )
  return UnreadCountResponse(unread_count=count)

@router.post(
  "/{notification_id}/read",
  response_model=NotificationResponse,
)
async def mark_notification_read(
  notification_id: UUID,
  current_user: User = Depends(get_current_user),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.mark_read(
    current_user.active_membership.organization_id,
    current_user.id,
    notification_id,
  )

@router.post("/read-all", response_model=MessageResponse)
async def mark_all_notifications_read(
  current_user: User = Depends(get_current_user),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  await service.mark_all_read(
    current_user.active_membership.organization_id, current_user.id
  )
  return {"message": "All notifications marked as read."}