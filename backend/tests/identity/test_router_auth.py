from __future__ import annotations
from uuid import uuid4
import pytest
from app.core.security import create_access_token, hash_password
from app.modules.identity.models import Organization, OrganizationMembership, Role, User

async def _seed_verified_user(
  db_session,
  *,
  email="aayan@gmail.com",
  password="Aayan12312#!1",
):
  org = Organization(
    id=uuid4(),
    name="Router Org",
    slug=f"router-{uuid4().hex[:6]}",
    is_active=True,
  )
  role = Role(
    id=uuid4(),
    organization_id=org.id,
    name="Company Admin",
    is_system=True,
  )
  user = User(
    id=uuid4(),
    organization_id=org.id,
    role_id=role.id,
    email=email.strip().lower(),
    password_hash=hash_password(password),
    first_name="Router",
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
  return org, role, user, membership

@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestRouterAuth:
  async def test_login_success(self, client, db_session):
    await _seed_verified_user(db_session)
    resp = await client.post(
      "/api/v1/auth/login",
      json={"email": "aayan@gmail.com", "password": "Aayan12312#!1"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tokens"]["access_token"]
    assert body["tokens"]["refresh_token"]
    assert body["user"]["email"] == "aayan@gmail.com"

  async def test_login_invalid_credentials(self, client, db_session):
    await _seed_verified_user(db_session)
    resp = await client.post(
      "/api/v1/auth/login",
      json={"email": "aayan@gmail.com", "password": "WrongPassword1!"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"

  async def test_me_requires_auth(self, client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"

  async def test_me_with_valid_token(self, client, db_session):
    org, _, user, _ = await _seed_verified_user(db_session)
    token = create_access_token(
      subject=str(user.id),
      organization_id=str(org.id),
    )
    resp = await client.get(
      "/api/v1/auth/me",
      headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["user"]["id"] == str(user.id)