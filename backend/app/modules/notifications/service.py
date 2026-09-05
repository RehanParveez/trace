from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import TraceException
from app.modules.notifications.models import Notification, NotificationType
from app.modules.notifications.repository import NotificationRepository

class NotificationService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repository = NotificationRepository(session)

  async def notify_user(
    self,
    organization_id: UUID,
    user_id: UUID,
    type: NotificationType,
    title: str,
    body: str | None = None,
    link_path: str | None = None,
    *,
    commit: bool = True,
  ) -> Notification:
    notification = Notification(
      id=uuid4(),
      organization_id=organization_id,
      user_id=user_id,
      type=type,
      title=title,
      body=body,
      link_path=link_path,
    )
    notification = await self.repository.create(notification)
    if commit:
      await self.session.commit()
    return notification

  async def notify_by_permission(
    self,
    organization_id: UUID,
    permission_key: str,
    type: NotificationType,
    title: str,
    body: str | None = None,
    link_path: str | None = None,
    *,
    exclude_user_id: UUID | None = None,
    commit: bool = True,
  ) -> list[Notification]:
    user_ids = await self.repository.get_user_ids_with_permission(
      organization_id, permission_key
    )
    if exclude_user_id is not None:
      user_ids = [uid for uid in user_ids if uid != exclude_user_id]
    if not user_ids:
      return []

    notifications = [
      Notification(
        id=uuid4(),
        organization_id=organization_id,
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        link_path=link_path,
      )
      for user_id in user_ids
    ]
    created = await self.repository.bulk_create(notifications)
    if commit:
      await self.session.commit()
    return created

  async def list_notifications(
    self,
    user_id: UUID,
    *,
    organization_id: UUID | None = None,
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 50,
  ) -> list[Notification]:
    return await self.repository.list_by_user(
      user_id, organization_id=organization_id, unread_only=unread_only, skip=skip, limit=limit,
    )

  async def get_unread_count(
    self, user_id: UUID, *, organization_id: UUID | None = None
  ) -> int:
    return await self.repository.count_unread(user_id, organization_id=organization_id)

  async def mark_read(
    self, user_id: UUID, notification_id: UUID,
  ) -> Notification:
    notification = await self.repository.get_by_id_and_user(notification_id, user_id)
    if notification is None:
      raise TraceException("Notification not found.", status_code=404, code="NOTIFICATION_NOT_FOUND")
    if not notification.is_read:
      notification.is_read = True
      notification.read_at = datetime.now(timezone.utc)
      await self.session.commit()
    return notification

  async def mark_all_read(
    self, user_id: UUID, *, organization_id: UUID | None = None
  ) -> None:
    await self.repository.mark_all_read(user_id, datetime.now(timezone.utc), organization_id=organization_id)
    await self.session.commit()