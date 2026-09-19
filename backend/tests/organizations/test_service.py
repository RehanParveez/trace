from __future__ import annotations
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import hashlib
import secrets
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import TraceException
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import Organization, OrganizationInvitation, Role, User
from app.modules.organizations.schemas import (AISettingsUpdateRequest, InvitationAcceptRequest, InvitationCreateRequest, MemberRoleUpdateRequest, MemberStatusUpdateRequest,
  OrganizationUpdateRequest, RoleCreateRequest, RoleUpdateRequest,
)
from app.modules.organizations.service import OrganizationService
from sqlalchemy.orm.attributes import set_committed_value

async def _create_invitation(
  service: OrganizationService,
  org: Organization,
  inviter: User,
  role: Role,
  email: str = "invitee@gmail.com",
) -> OrganizationInvitation:
  payload = InvitationCreateRequest(email=email, role_id=role.id)
  return await service.create_invitation(org.id, inviter.id, payload)

@pytest.mark.asyncio
async def test_update_organization_rejects_duplicate_slug(
  organization_service: OrganizationService,
  make_organization,
  admin_context,
):
  await make_organization(slug="taken-slug")
  payload = OrganizationUpdateRequest(slug="taken-slug")
  with pytest.raises(TraceException) as exc:
    await organization_service.update_organization(
      admin_context.organization.id, payload, actor_user_id=admin_context.user.id
    )
  assert exc.value.code == "ORGANIZATION_SLUG_ALREADY_EXISTS"
  assert exc.value.status_code == 409

@pytest.mark.asyncio
async def test_update_organization_currency_locked_when_budgets_exist(
  organization_service: OrganizationService,
  admin_context,
  monkeypatch,
):
  async def fake_list_by_org(_org_id):
    return [object()]

  monkeypatch.setattr(
    organization_service.budgets, "list_by_org", fake_list_by_org
  )
  payload = OrganizationUpdateRequest(currency="USD")
  with pytest.raises(TraceException) as exc:
    await organization_service.update_organization(
      admin_context.organization.id, payload, actor_user_id=admin_context.user.id
    )
  assert exc.value.code == "ORGANIZATION_CURRENCY_LOCKED"
  assert exc.value.status_code == 409

@pytest.mark.asyncio
async def test_update_organization_allows_currency_change_without_budgets(
  organization_service: OrganizationService,
  admin_context,
  monkeypatch,
):
  async def fake_list_by_org(_org_id):
    return []

  monkeypatch.setattr(
    organization_service.budgets, "list_by_org", fake_list_by_org
  )
  payload = OrganizationUpdateRequest(currency="USD")
  org = await organization_service.update_organization(
    admin_context.organization.id, payload, actor_user_id=admin_context.user.id
  )
  assert org.currency == "USD"

@pytest.mark.asyncio
async def test_create_invitation_rejects_existing_member(
  organization_service: OrganizationService,
  admin_context,
  member_context,
):
  payload = InvitationCreateRequest(
    email=member_context.user.email,
    role_id=admin_context.role.id,
  )
  with pytest.raises(TraceException) as exc:
    await organization_service.create_invitation(
      admin_context.organization.id,
      admin_context.user.id,
      payload,
    )
  assert exc.value.code == "MEMBER_ALREADY_EXISTS"

@pytest.mark.asyncio
async def test_create_invitation_rejects_duplicate_pending(
  organization_service: OrganizationService,
  admin_context,
):
  await _create_invitation(
    organization_service,
    admin_context.organization,
    admin_context.user,
    admin_context.role,
    email="dup@gmail.com",
  )
  with pytest.raises(TraceException) as exc:
    await _create_invitation(
      organization_service,
      admin_context.organization,
      admin_context.user,
      admin_context.role,
      email="dup@gmail.com",
    )
  assert exc.value.code == "INVITATION_ALREADY_EXISTS"

@pytest.mark.asyncio
async def test_create_invitation_rejects_unknown_role(
  organization_service: OrganizationService,
  admin_context,
):
  payload = InvitationCreateRequest(
    email="new@gmail.com",
    role_id=uuid4(),
  )
  with pytest.raises(TraceException) as exc:
    await organization_service.create_invitation(
      admin_context.organization.id,
      admin_context.user.id,
      payload,
    )
  assert exc.value.code == "ROLE_NOT_FOUND"

@pytest.mark.asyncio
async def test_revoke_invitation_blocks_already_accepted(
  organization_service: OrganizationService,
  admin_context,
  db_session: AsyncSession,
):
  inv = await _create_invitation(
    organization_service,
    admin_context.organization,
    admin_context.user,
    admin_context.role,
  )
  inv.accepted_at = datetime.now(timezone.utc)
  await db_session.flush()

  with pytest.raises(TraceException) as exc:
    await organization_service.revoke_invitation(
      admin_context.organization.id, inv.id, actor_user_id=admin_context.user.id
    )
  assert exc.value.code == "INVITATION_ALREADY_ACCEPTED"

@pytest.mark.asyncio
async def test_revoke_invitation_blocks_already_revoked(
  organization_service: OrganizationService,
  admin_context,
  db_session: AsyncSession,
):
  inv = await _create_invitation(
    organization_service,
    admin_context.organization,
    admin_context.user,
    admin_context.role,
  )
  inv.revoked_at = datetime.now(timezone.utc)
  await db_session.flush()

  with pytest.raises(TraceException) as exc:
    await organization_service.revoke_invitation(
      admin_context.organization.id, inv.id, actor_user_id=admin_context.user.id
    )
  assert exc.value.code == "INVITATION_ALREADY_REVOKED"

@pytest.mark.asyncio
async def test_accept_invitation_email_mismatch(
  organization_service: OrganizationService,
  admin_context,
  make_user,
  db_session: AsyncSession,
):
  inv = await _create_invitation(
    organization_service,
    admin_context.organization,
    admin_context.user,
    admin_context.role,
    email="target@gmail.com",
  )
  raw = secrets.token_urlsafe(48)
  inv.token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
  await db_session.flush()

  other = await make_user(
    organization=admin_context.organization,
    role=admin_context.role,
    email="other@gmail.com",
  )
  payload = InvitationAcceptRequest(token=raw)
  with pytest.raises(TraceException) as exc:
    await organization_service.accept_invitation(payload, other)
  assert exc.value.code == "INVITATION_EMAIL_MISMATCH"

@pytest.mark.asyncio
async def test_accept_invitation_expired(
  organization_service: OrganizationService,
  admin_context,
  make_user,
  db_session: AsyncSession,
):
  inv = await _create_invitation(
    organization_service,
    admin_context.organization,
    admin_context.user,
    admin_context.role,
    email="expired@gmail.com",
  )
  inv.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
  raw = secrets.token_urlsafe(48)
  inv.token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
  await db_session.flush()

  user = await make_user(
    organization=admin_context.organization,
    role=admin_context.role,
    email="expired@gmail.com",
  )
  payload = InvitationAcceptRequest(token=raw)
  with pytest.raises(TraceException) as exc:
    await organization_service.accept_invitation(payload, user)
  assert exc.value.code == "INVITATION_EXPIRED"

@pytest.mark.asyncio
async def test_update_member_role_blocks_last_admin_self_demotion(
  organization_service: OrganizationService,
  admin_context,
  make_role,
  seed_org_permissions,
  db_session: AsyncSession,
):
  read_only = seed_org_permissions[str(PermissionKey.ORGANIZATION_READ)]
  demote_role = await make_role(
    organization=admin_context.organization,
    name="NoManage",
    is_system=False,
  )
  set_committed_value(demote_role, "permissions", [read_only])
  await db_session.flush()

  payload = MemberRoleUpdateRequest(role_id=demote_role.id)
  with pytest.raises(TraceException) as exc:
    await organization_service.update_member_role(
      admin_context.organization.id,
      admin_context.user.id,
      payload,
      admin_context.user.id,
    )
  assert exc.value.code == "LAST_ADMIN_PROTECTED"

@pytest.mark.asyncio
async def test_update_member_status_blocks_self_deactivation(
  organization_service: OrganizationService,
  admin_context,
):
  payload = MemberStatusUpdateRequest(is_active=False)
  with pytest.raises(TraceException) as exc:
    await organization_service.update_member_status(
      admin_context.organization.id,
      admin_context.user.id,
      payload,
      admin_context.user.id,
    )
  assert exc.value.code == "CANNOT_DEACTIVATE_SELF"

@pytest.mark.asyncio
async def test_update_member_status_blocks_last_admin_deactivation(
  organization_service: OrganizationService,
  admin_context,
  member_context,
):
  payload = MemberStatusUpdateRequest(is_active=False)
  with pytest.raises(TraceException) as exc:
    await organization_service.update_member_status(
      admin_context.organization.id,
      admin_context.user.id,
      payload,
      member_context.user.id,
    )
  assert exc.value.code == "LAST_ADMIN_PROTECTED"

@pytest.mark.asyncio
async def test_create_role_rejects_duplicate_name(
  organization_service: OrganizationService,
  admin_context,
):
  payload = RoleCreateRequest(
    name=admin_context.role.name,
    permission_ids=[],
  )
  with pytest.raises(TraceException) as exc:
    await organization_service.create_role(
      admin_context.organization.id, payload, actor_user_id=admin_context.user.id
    )
  assert exc.value.code == "ROLE_ALREADY_EXISTS"

@pytest.mark.asyncio
async def test_update_role_protects_system_role(
  organization_service: OrganizationService,
  admin_context,
):
  payload = RoleUpdateRequest(name="Hacked")
  with pytest.raises(TraceException) as exc:
    await organization_service.update_role(
      admin_context.organization.id,
      admin_context.role.id,
      payload,
      actor_user_id=admin_context.user.id,
    )
  assert exc.value.code == "SYSTEM_ROLE_PROTECTED"

@pytest.mark.asyncio
async def test_delete_role_protects_system_role(
  organization_service: OrganizationService,
  admin_context,
):
  with pytest.raises(TraceException) as exc:
    await organization_service.delete_role(
      admin_context.organization.id,
      admin_context.role.id,
      actor_user_id=admin_context.user.id,
    )
  assert exc.value.code == "SYSTEM_ROLE_PROTECTED"

@pytest.mark.asyncio
async def test_delete_role_blocks_when_members_assigned(
  organization_service: OrganizationService,
  admin_context,
  make_role,
  make_user,
  make_membership,
  seed_org_permissions,
  db_session: AsyncSession,
):
  read_perm = seed_org_permissions[str(PermissionKey.ORGANIZATION_READ)]
  role = await make_role(
    organization=admin_context.organization,
    name="InUse",
    is_system=False,
  )
  set_committed_value(role, "permissions", [read_perm])
  await db_session.flush()

  user = await make_user(
    organization=admin_context.organization,
    role=role,
  )
  await make_membership(
    user=user,
    organization=admin_context.organization,
    role=role,
  )

  with pytest.raises(TraceException) as exc:
    await organization_service.delete_role(
      admin_context.organization.id,
      role.id,
      actor_user_id=admin_context.user.id,
    )
  assert exc.value.code == "ROLE_IN_USE"

@pytest.mark.asyncio
async def test_update_ai_settings_roundtrip(
  organization_service: OrganizationService,
  admin_context,
):
  enabled = await organization_service.update_ai_settings(
    admin_context.organization.id,
    AISettingsUpdateRequest(ai_enabled=True),
    actor_user_id=admin_context.user.id,
  )
  assert enabled is True
  got = await organization_service.get_ai_settings(admin_context.organization.id)
  assert got is True