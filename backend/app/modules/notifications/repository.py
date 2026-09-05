from __future__ import annotations
from uuid import UUID
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.identity.models import Permission, Role, User, OrganizationMembership
from app.modules.notifications.models import Notification

class NotificationRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create(self, notification: Notification) -> Notification:
    self.session.add(notification)
    await self.session.flush()
    return notification

  async def bulk_create(
    self, notifications: list[Notification]
  ) -> list[Notification]:
    self.session.add_all(notifications)
    await self.session.flush()
    return notifications

  async def get_by_id_and_user(
    self, notification_id: UUID, user_id: UUID
  ) -> Notification | None:
    result = await self.session.execute(
      select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == user_id,
      )
    )
    return result.scalar_one_or_none()

  async def list_by_user(
    self,
    user_id: UUID,
    *,
    organization_id: UUID | None = None,
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 50,
    ) -> list[Notification]:
      query = select(Notification).where(Notification.user_id == user_id)
      if organization_id is not None:
        query = query.where(Notification.organization_id == organization_id)
      if unread_only:
        query = query.where(Notification.is_read.is_(False))
      query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
      result = await self.session.execute(query)
      return list(result.scalars().all())

  async def count_unread(
    self, user_id: UUID, *, organization_id: UUID | None = None
  ) -> int:
    query = select(func.count()).select_from(Notification).where(
      Notification.user_id == user_id,
      Notification.is_read.is_(False),
    )
    if organization_id is not None:
      query = query.where(Notification.organization_id == organization_id)
    result = await self.session.execute(query)
    return result.scalar_one()

  async def mark_all_read(
    self, user_id: UUID, read_at, *, organization_id: UUID | None = None
  ) -> None:
    query = update(Notification).where(
      Notification.user_id == user_id,
      Notification.is_read.is_(False),
    )
    if organization_id is not None:
      query = query.where(Notification.organization_id == organization_id)
    await self.session.execute(query.values(is_read=True, read_at=read_at))
    await self.session.flush()

  async def get_user_ids_with_permission(
    self, organization_id: UUID, permission_key: str
  ) -> list[UUID]:
    result = await self.session.execute(
      select(OrganizationMembership.user_id)
      .join(Role, OrganizationMembership.role_id == Role.id)
      .join(Role.permissions)
      .join(User, User.id == OrganizationMembership.user_id)
      .where(
        OrganizationMembership.organization_id == organization_id,
        OrganizationMembership.is_active.is_(True),
        Permission.key == permission_key,
        User.is_active.is_(True),
      )
    )
    return list(result.scalars().unique().all())