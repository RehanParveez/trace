from __future__ import annotations
import pytest
from app.modules.notifications.service import NotificationService
from app.modules.identity.enums import PermissionKey
from app.modules.notifications.models import  NotificationType, Notification
from uuid import uuid4
from sqlalchemy import select
from datetime import datetime, timezone
from app.core.exceptions import TraceException
from sqlalchemy.orm import selectinload
from app.modules.identity.models import Role

@pytest.mark.asyncio
async def test_notify_by_permission_targets_only_users_with_permission(
  notification_service: NotificationService,
  db_session,
  notifications_admin_context,
  make_role,
  make_user,
  make_membership,
  seed_notification_permissions,
):
  ctx = notifications_admin_context
  org = ctx.organization

  perm = seed_notification_permissions[PermissionKey.NOTIFICATION_READ.value]

  role_with = await make_role(organization=org, name="Reader", is_system=False)
  result = await db_session.execute(
    select(Role)
    .where(Role.id == role_with.id)
    .options(selectinload(Role.permissions))
  )
  role_with = result.scalar_one()
  role_with.permissions = [perm]
  await db_session.flush()

  user_a = await make_user(
    organization=org,
    role=role_with,
    email=f"a-{uuid4().hex[:6]}@ex.com",
  )
  await make_membership(user=user_a, organization=org, role=role_with, is_active=True)

  role_without = await make_role(organization=org, name="NoNotif", is_system=False)
  result = await db_session.execute(
    select(Role)
    .where(Role.id == role_without.id)
    .options(selectinload(Role.permissions))
  )
  role_without = result.scalar_one()
  role_without.permissions = []
  await db_session.flush()

  user_b = await make_user(
    organization=org,
    role=role_without,
    email=f"b-{uuid4().hex[:6]}@ex.com",
  )
  await make_membership(user=user_b, organization=org, role=role_without, is_active=True)

  created = await notification_service.notify_by_permission(
    organization_id=org.id,
    permission_key=PermissionKey.NOTIFICATION_READ.value,
    type=NotificationType.SUBSCRIPTION_USAGE_WARNING,
    title="Quota warning",
    body="You are near the limit",
    commit=True,
  )

  assert len(created) >= 1
  user_ids = {n.user_id for n in created}
  assert user_a.id in user_ids
  assert user_b.id not in user_ids
  assert ctx.user.id in user_ids

  result = await db_session.execute(
    select(Notification).where(
      Notification.organization_id == org.id,
      Notification.type == NotificationType.SUBSCRIPTION_USAGE_WARNING,
    )
  )
  persisted = list(result.scalars().all())
  assert {n.user_id for n in persisted} == user_ids
  assert all(n.is_read is False for n in persisted)

@pytest.mark.asyncio
async def test_notify_by_permission_excludes_user(
  notification_service: NotificationService,
  db_session,
  notifications_admin_context,
):
  ctx = notifications_admin_context

  created = await notification_service.notify_by_permission(
    organization_id=ctx.organization.id,
    permission_key=str(PermissionKey.NOTIFICATION_READ),
    type=NotificationType.MEMBER_JOINED,
    title="Someone joined",
    exclude_user_id=ctx.user.id,
    commit=True,
  )

  assert all(n.user_id != ctx.user.id for n in created)

  result = await db_session.execute(
    select(Notification).where(
      Notification.organization_id == ctx.organization.id,
      Notification.type == NotificationType.MEMBER_JOINED,
    )
  )
  assert all(n.user_id != ctx.user.id for n in result.scalars().all())
  
@pytest.mark.asyncio
async def test_notify_by_permission_returns_empty_when_no_matching_users(
  notification_service: NotificationService,
  db_session,
  make_organization,
  make_role,
  make_user,
  make_membership,
):
  org = await make_organization()
  role = await make_role(organization=org, name="Empty", is_system=False)
  user = await make_user(organization=org, role=role)
  await make_membership(user=user, organization=org, role=role)

  created = await notification_service.notify_by_permission(
    organization_id=org.id,
    permission_key="nonexistent.permission.key",
    type=NotificationType.MEMBER_JOINED,
    title="Should not create",
    commit=True,
  )
  assert created == []

  result = await db_session.execute(
    select(Notification).where(Notification.organization_id == org.id)
  )
  assert list(result.scalars().all()) == []

@pytest.mark.asyncio
async def test_mark_read_sets_flag_and_timestamp(
  notification_service: NotificationService,
  notifications_admin_context,
  make_notification,
  db_session,
):
  ctx = notifications_admin_context
  n = await make_notification(
    organization=ctx.organization,
    user=ctx.user,
    is_read=False,
  )
  await db_session.commit()

  updated = await notification_service.mark_read(
    ctx.user.id,
    n.id,
    ctx.organization.id,
  )
  assert updated.is_read is True
  assert updated.read_at is not None
  assert updated.read_at.tzinfo is not None

  result = await db_session.execute(
    select(Notification).where(Notification.id == n.id)
  )
  persisted = result.scalar_one()
  assert persisted.is_read is True
  assert persisted.read_at is not None

@pytest.mark.asyncio
async def test_mark_read_is_idempotent(
  notification_service: NotificationService,
  notifications_admin_context,
  make_notification,
  db_session,
):
  ctx = notifications_admin_context
  already_read_at = datetime.now(timezone.utc)
  n = await make_notification(
    organization=ctx.organization,
    user=ctx.user,
    is_read=True,
    read_at=already_read_at,
  )
  await db_session.commit()

  updated = await notification_service.mark_read(
    ctx.user.id,
    n.id,
    ctx.organization.id,
  )
  assert updated.is_read is True
  assert updated.read_at == already_read_at

@pytest.mark.asyncio
async def test_mark_read_raises_when_not_found_or_wrong_user(
  notification_service: NotificationService,
  notifications_admin_context,
  make_notification,
  make_user,
  make_role,
  make_membership,
  db_session,
):
  ctx = notifications_admin_context
  n = await make_notification(organization=ctx.organization, user=ctx.user)
  await db_session.commit()

  with pytest.raises(TraceException) as exc:
    await notification_service.mark_read(ctx.user.id, uuid4(), ctx.organization.id)
  assert exc.value.status_code == 404
  assert exc.value.code == "NOTIFICATION_NOT_FOUND"

  other_role = await make_role(organization=ctx.organization, name="Other")
  other_user = await make_user(organization=ctx.organization, role=other_role)
  await make_membership(user=other_user, organization=ctx.organization, role=other_role)

  with pytest.raises(TraceException) as exc:
    await notification_service.mark_read(other_user.id, n.id, ctx.organization.id)
  assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_mark_all_read(
  notification_service: NotificationService,
  notifications_admin_context,
  make_notification,
  db_session,
):
  ctx = notifications_admin_context
  org, user = ctx.organization, ctx.user

  n1 = await make_notification(organization=org, user=user, is_read=False)
  n2 = await make_notification(organization=org, user=user, is_read=False)
  n3 = await make_notification(
    organization=org,
    user=user,
    is_read=True,
    read_at=datetime.now(timezone.utc),
  )
  await db_session.commit()

  await notification_service.mark_all_read(user.id, org.id)

  result = await db_session.execute(
    select(Notification).where(
      Notification.user_id == user.id,
      Notification.organization_id == org.id,
    )
  )
  all_notifs = list(result.scalars().all())
  assert len(all_notifs) == 3
  assert all(n.is_read is True and n.read_at is not None for n in all_notifs)