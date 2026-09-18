from __future__ import annotations
from uuid import uuid4
import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.exceptions import TraceException, trace_exception_handler
from app.core.security import hash_password
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import require_permission
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import Organization, OrganizationMembership, Permission, Role, User

async def _user_with_permissions(
  db_session: AsyncSession,
  *,
  permission_keys: list[str],
):
  org = Organization(
    id=uuid4(),
    name="Perm Org",
    slug=f"perm-{uuid4().hex[:6]}",
    is_active=True,
  )
  perms = []
  for key in permission_keys:
    p = Permission(id=uuid4(), key=key, description=key)
    perms.append(p)
    db_session.add(p)
  role = Role(
    id=uuid4(),
    organization_id=org.id,
    name="Custom",
    is_system=False,
  )
  role.permissions = perms
  user = User(
    id=uuid4(),
    organization_id=org.id,
    role_id=role.id,
    email=f"perm-{uuid4().hex[:6]}@gmail.com",
    password_hash=hash_password("@gmail12312#1!"),
    first_name="Perm",
    last_name="User",
    is_active=True,
    is_verified=True,
  )
  membership = OrganizationMembership(
    id=uuid4(),
    user_id=user.id,
    organization_id=org.id,
    role_id=role.id,
    is_active=True,
  )
  db_session.add_all([org, role, user, membership])
  await db_session.flush()
  user.active_membership = membership
  return user, membership

@pytest.mark.integration
@pytest.mark.permissions
@pytest.mark.asyncio
class TestRequirePermission:
  async def test_allows_when_permission_present(self, db_session):
    user, membership = await _user_with_permissions(
      db_session,
      permission_keys=[PermissionKey.IDENTITY_MANAGE.value],
    )
    app = FastAPI()
    app.add_exception_handler(TraceException, trace_exception_handler)

    async def _override_db():
      yield db_session

    async def _fake_current_user():
      user.active_membership = membership
      _ = membership.role.permissions
      return user

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _fake_current_user

    @app.get("/protected")
    async def protected(
      current: User = Depends(
        require_permission(PermissionKey.IDENTITY_MANAGE.value)
      ),
    ):
      return {"ok": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
      resp = await client.get("/protected")

    assert resp.status_code == 200

  async def test_denies_when_permission_missing(self, db_session):
    user, membership = await _user_with_permissions(
      db_session,
      permission_keys=[PermissionKey.IDENTITY_READ.value],
    )
    app = FastAPI()
    app.add_exception_handler(TraceException, trace_exception_handler)

    async def _override_db():
      yield db_session

    async def _fake_current_user():
      user.active_membership = membership
      _ = membership.role.permissions
      return user

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _fake_current_user

    @app.get("/protected")
    async def protected(
      current: User = Depends(
        require_permission(PermissionKey.IDENTITY_MANAGE.value)
      ),
    ):
      return {"ok": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
      resp = await client.get("/protected")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "PERMISSION_DENIED"