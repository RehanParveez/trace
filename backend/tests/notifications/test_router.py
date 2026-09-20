from __future__ import annotations
import pytest
from app.dependencies.auth import get_current_user
from app.modules.notifications.models import NotificationType, Notification
from httpx import AsyncClient
from app.main import app
from sqlalchemy import select
from uuid import uuid4

PREFIX = "/api/v1/notifications"

@pytest.fixture
def auth_override(notifications_admin_context):
  user = notifications_admin_context.user

  async def _override():
    return user

  app.dependency_overrides[get_current_user] = _override
  yield user
  app.dependency_overrides.pop(get_current_user, None)

@pytest.mark.asyncio
async def test_list_notifications_endpoint(
  client: AsyncClient,
  auth_override,
  notifications_admin_context,
  make_notification,
  db_session,
):
  ctx = notifications_admin_context
  await make_notification(
    organization=ctx.organization,
    user=ctx.user,
    title="One",
    type=NotificationType.MEMBER_JOINED,
  )
  await make_notification(
    organization=ctx.organization,
    user=ctx.user,
    title="Two",
    type=NotificationType.MEMBER_JOINED,
    is_read=True,
  )
  await db_session.commit()

  resp = await client.get(PREFIX)
  assert resp.status_code == 200
  data = resp.json()
  assert len(data) == 2
  assert {item["title"] for item in data} == {"One", "Two"}
  assert all("id" in item and "type" in item and "is_read" in item for item in data)

  resp = await client.get(PREFIX, params={"unread_only": True})
  assert resp.status_code == 200
  assert len(resp.json()) == 1
  assert resp.json()[0]["title"] == "One"

@pytest.mark.asyncio
async def test_list_notifications_pagination(
  client: AsyncClient,
  auth_override,
  notifications_admin_context,
  make_notification,
  db_session,
):
  ctx = notifications_admin_context
  for i in range(5):
    await make_notification(
      organization=ctx.organization,
      user=ctx.user,
      title=f"N{i}",
      type=NotificationType.MEMBER_JOINED,
    )
  await db_session.commit()

  resp = await client.get(PREFIX, params={"skip": 1, "limit": 2})
  assert resp.status_code == 200
  assert len(resp.json()) == 2

@pytest.mark.asyncio
async def test_unread_count_endpoint(
  client: AsyncClient,
  auth_override,
  notifications_admin_context,
  make_notification,
  db_session,
):
  ctx = notifications_admin_context
  await make_notification(organization=ctx.organization, user=ctx.user, is_read=False)
  await make_notification(organization=ctx.organization, user=ctx.user, is_read=False)
  await make_notification(organization=ctx.organization, user=ctx.user, is_read=True)
  await db_session.commit()

  resp = await client.get(f"{PREFIX}/unread-count")
  assert resp.status_code == 200
  assert resp.json() == {"unread_count": 2}

@pytest.mark.asyncio
async def test_mark_notification_read_endpoint(
  client: AsyncClient,
  auth_override,
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

  resp = await client.post(f"{PREFIX}/{n.id}/read")
  assert resp.status_code == 200
  body = resp.json()
  assert body["id"] == str(n.id)
  assert body["is_read"] is True
  assert body["read_at"] is not None

  result = await db_session.execute(
    select(Notification).where(Notification.id == n.id)
  )
  persisted = result.scalar_one()
  assert persisted.is_read is True
  assert persisted.read_at is not None

@pytest.mark.asyncio
async def test_mark_notification_read_not_found(
  client: AsyncClient,
  auth_override,
):
  resp = await client.post(f"{PREFIX}/{uuid4()}/read")
  assert resp.status_code == 404
  data = resp.json()
  assert data.get("code") == "NOTIFICATION_NOT_FOUND" or "not found" in str(data).lower()

@pytest.mark.asyncio
async def test_mark_all_read_endpoint(
  client: AsyncClient,
  auth_override,
  notifications_admin_context,
  make_notification,
  db_session,
):
  ctx = notifications_admin_context
  await make_notification(organization=ctx.organization, user=ctx.user, is_read=False)
  await make_notification(organization=ctx.organization, user=ctx.user, is_read=False)
  await db_session.commit()

  resp = await client.post(f"{PREFIX}/read-all")
  assert resp.status_code == 200
  assert resp.json()["message"] == "All notifications marked as read."

  count_resp = await client.get(f"{PREFIX}/unread-count")
  assert count_resp.status_code == 200
  assert count_resp.json()["unread_count"] == 0

  result = await db_session.execute(
    select(Notification).where(
      Notification.user_id == ctx.user.id,
      Notification.organization_id == ctx.organization.id,
    )
  )
  assert all(n.is_read is True for n in result.scalars().all())

@pytest.mark.asyncio
async def test_endpoints_require_auth(client: AsyncClient):
  for method, path in [
    ("get", PREFIX),
    ("get", f"{PREFIX}/unread-count"),
    ("post", f"{PREFIX}/{uuid4()}/read"),
    ("post", f"{PREFIX}/read-all"),
  ]:
    resp = await getattr(client, method)(path)
    assert resp.status_code in (401, 403), f"{method.upper()} {path} should be protected"