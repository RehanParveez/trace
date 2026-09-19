from __future__ import annotations
from uuid import uuid4
import pytest
from httpx import AsyncClient
from app.core.security import create_access_token

def _auth_header(user_id, org_id) -> dict[str, str]:
  token = create_access_token(
    subject=str(user_id),
    organization_id=str(org_id),
  )
  return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_get_organization_requires_read_permission(
  client: AsyncClient,
  member_context,
):
  headers = _auth_header(member_context.user.id, member_context.organization.id)
  resp = await client.get("/api/v1/organizations/me", headers=headers)
  assert resp.status_code == 200
  body = resp.json()
  assert body["id"] == str(member_context.organization.id)

@pytest.mark.asyncio
async def test_update_organization_requires_manage_permission(
  client: AsyncClient,
  member_context,
):
  headers = _auth_header(member_context.user.id, member_context.organization.id)
  resp = await client.patch(
    "/api/v1/organizations/me",
    json={"name": "Hacked Name"},
    headers=headers,
  )
  assert resp.status_code == 403
  assert resp.json()["error"]["code"] == "PERMISSION_DENIED"

@pytest.mark.asyncio
async def test_update_organization_succeeds_for_admin(
  client: AsyncClient,
  admin_context,
):
  headers = _auth_header(admin_context.user.id, admin_context.organization.id)
  resp = await client.patch(
    "/api/v1/organizations/me",
    json={"name": "Updated Acme"},
    headers=headers,
  )
  assert resp.status_code == 200
  assert resp.json()["name"] == "Updated Acme"

@pytest.mark.asyncio
async def test_list_members_requires_read(
  client: AsyncClient,
  admin_context,
):
  headers = _auth_header(admin_context.user.id, admin_context.organization.id)
  resp = await client.get("/api/v1/organizations/me/members", headers=headers)
  assert resp.status_code == 200
  assert "X-Total-Count" in resp.headers

@pytest.mark.asyncio
async def test_create_invitation_requires_members_manage(
  client: AsyncClient,
  member_context,
  admin_context,
):
  headers = _auth_header(member_context.user.id, member_context.organization.id)
  resp = await client.post(
    "/api/v1/organizations/me/invitations",
    json={"email": "new@gmail.com", "role_id": str(admin_context.role.id)},
    headers=headers,
  )
  assert resp.status_code == 403
  assert resp.json()["error"]["code"] == "PERMISSION_DENIED"

@pytest.mark.asyncio
async def test_create_role_requires_manage(
  client: AsyncClient,
  member_context,
):
  headers = _auth_header(member_context.user.id, member_context.organization.id)
  resp = await client.post(
    "/api/v1/organizations/me/roles",
    json={"name": "NewRole", "permission_ids": []},
    headers=headers,
  )
  assert resp.status_code == 403
  assert resp.json()["error"]["code"] == "PERMISSION_DENIED"

@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(client: AsyncClient):
  resp = await client.get("/api/v1/organizations/me")
  assert resp.status_code == 401
  assert resp.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"

@pytest.mark.asyncio
async def test_role_lifecycle_happy_path(
  client: AsyncClient,
  admin_context,
  seed_org_permissions,
):
  headers = _auth_header(admin_context.user.id, admin_context.organization.id)
  perm_id = str(list(seed_org_permissions.values())[0].id)

  create_resp = await client.post(
    "/api/v1/organizations/me/roles",
    json={
      "name": f"Custom-{uuid4().hex[:6]}",
      "description": "test role",
      "permission_ids": [perm_id],
    },
    headers=headers,
  )
  assert create_resp.status_code == 201
  role_id = create_resp.json()["id"]

  list_resp = await client.get("/api/v1/organizations/me/roles", headers=headers)
  assert list_resp.status_code == 200
  ids = {r["id"] for r in list_resp.json()}
  assert role_id in ids

  del_resp = await client.delete(
    f"/api/v1/organizations/me/roles/{role_id}",
    headers=headers,
  )
  assert del_resp.status_code == 204