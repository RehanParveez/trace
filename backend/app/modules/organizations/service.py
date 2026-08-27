from __future__ import annotations
import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import TraceException
from app.modules.identity.models import Organization, OrganizationInvitation, OrganizationMembership, Role, User
from app.modules.organizations.repository import OrganizationRepository
from app.modules.organizations.schemas import ( AISettingsUpdateRequest, InvitationAcceptRequest, InvitationAcceptanceResponse, InvitationCreateRequest, MemberRoleUpdateRequest, MemberStatusUpdateRequest,
  OrganizationUpdateRequest, RoleCreateRequest, RoleUpdateRequest,
)

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

class OrganizationService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repository = OrganizationRepository(session)

  async def get_organization(self, organization_id: UUID) -> Organization:
    organization = await self.repository.get_organization(organization_id)
    if organization is None:
      raise TraceException(
        "Organization not found.",
        status_code=404,
        code="ORGANIZATION_NOT_FOUND",
      )
    return organization

  async def update_organization(
    self,
    organization_id: UUID,
    payload: OrganizationUpdateRequest,
  ) -> Organization:
    organization = await self.repository.get_organization_for_update(
      organization_id
    )
    if organization is None:
      raise TraceException(
        "Organization not found.",
        status_code=404,
        code="ORGANIZATION_NOT_FOUND",
      )

    if payload.name is not None:
      organization.name = payload.name
    if payload.slug is not None:
      slug = self._normalize_slug(payload.slug)
      existing = await self.repository.get_by_slug(slug)
      if existing is not None and existing.id != organization.id:
        raise TraceException(
          "Organization slug is already in use.",
          status_code=409,
          code="ORGANIZATION_SLUG_ALREADY_EXISTS",
        )
      organization.slug = slug
    if payload.ai_enabled is not None:
      organization.ai_enabled = payload.ai_enabled

    try:
      await self.repository.update_organization(organization)
      await self.session.commit()
    except IntegrityError as exc:
      await self.session.rollback()
      raise TraceException(
        "Unable to update organization.",
        status_code=409,
        code="ORGANIZATION_UPDATE_CONFLICT",
      ) from exc

    return organization

  async def get_ai_settings(self, organization_id: UUID) -> bool:
    organization = await self.get_organization(organization_id)
    return organization.ai_enabled

  async def update_ai_settings(
    self,
    organization_id: UUID,
    payload: AISettingsUpdateRequest,
  ) -> bool:
    organization = await self.repository.get_organization_for_update(
      organization_id
    )
    if organization is None:
      raise TraceException(
        "Organization not found.",
        status_code=404,
        code="ORGANIZATION_NOT_FOUND",
      )
    organization.ai_enabled = payload.ai_enabled
    await self.session.commit()
    return organization.ai_enabled

  async def create_invitation(
    self,
    organization_id: UUID,
    invited_by_user_id: UUID,
    payload: InvitationCreateRequest,
  ) -> OrganizationInvitation:
    email = payload.email.strip().lower()
    role = await self.repository.get_role(organization_id, payload.role_id)
    if role is None:
      raise TraceException(
        "Role not found in this organization.",
        status_code=404,
        code="ROLE_NOT_FOUND",
      )

    existing_member = await self.repository.get_member_by_email_in_org(
      organization_id, email
    )
    if existing_member is not None:
      raise TraceException(
        "A user with this email is already a member of the organization.",
        status_code=409,
        code="MEMBER_ALREADY_EXISTS",
      )

    existing_invitation = (
      await self.repository.get_pending_invitation_for_email(
        organization_id, email
      )
    )
    if existing_invitation is not None:
      raise TraceException(
        "A pending invitation already exists for this email.",
        status_code=409,
        code="INVITATION_ALREADY_EXISTS",
      )

    raw_token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    invitation = OrganizationInvitation(
      id=uuid4(),
      organization_id=organization_id,
      role_id=role.id,
      invited_by_user_id=invited_by_user_id,
      email=email,
      token_hash=token_hash,
      expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )

    try:
      invitation = await self.repository.create_invitation(invitation)
      await self.session.commit()
    except IntegrityError as exc:
      await self.session.rollback()
      raise TraceException(
        "Unable to create invitation.",
        status_code=409,
        code="INVITATION_CREATE_CONFLICT",
      ) from exc

    return invitation

  async def list_invitations(
    self,
    organization_id: UUID,
    *,
    skip: int = 0,
    limit: int = 100,
  ) -> tuple[list[OrganizationInvitation], int]:
    return await self.repository.list_invitations(
      organization_id, skip=skip, limit=limit
    )

  async def revoke_invitation(
    self,
    organization_id: UUID,
    invitation_id: UUID,
  ) -> None:
    invitation = await self.repository.get_invitation(
      organization_id, invitation_id
    )
    if invitation is None:
      raise TraceException(
        "Invitation not found.",
        status_code=404,
        code="INVITATION_NOT_FOUND",
      )
    if invitation.accepted_at is not None:
      raise TraceException(
        "Accepted invitations cannot be revoked.",
        status_code=409,
        code="INVITATION_ALREADY_ACCEPTED",
      )
    if invitation.revoked_at is not None:
      raise TraceException(
        "Invitation has already been revoked.",
        status_code=409,
        code="INVITATION_ALREADY_REVOKED",
      )
    invitation.revoked_at = datetime.now(timezone.utc)
    await self.session.flush()
    await self.session.commit()

  async def accept_invitation(
    self,
    payload: InvitationAcceptRequest,
    current_user: User,
  ) -> InvitationAcceptanceResponse:
    raw_token = payload.token.strip()
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    invitation = await self.repository.get_invitation_by_token_hash(token_hash)
    if invitation is None:
      raise TraceException(
        "Invalid or expired invitation.",
        status_code=400,
        code="INVALID_INVITATION_TOKEN",
      )

    if invitation.revoked_at is not None:
      raise TraceException(
        "This invitation has been revoked.",
        status_code=409,
        code="INVITATION_REVOKED",
      )

    if invitation.accepted_at is not None:
      raise TraceException(
        "This invitation has already been accepted.",
        status_code=409,
        code="INVITATION_ALREADY_ACCEPTED",
      )

    now = datetime.now(timezone.utc)
    if invitation.expires_at <= now:
      raise TraceException(
        "This invitation has expired.",
        status_code=400,
        code="INVITATION_EXPIRED",
      )

    invitation_email = invitation.email.strip().lower()
    current_user_email = str(current_user.email).strip().lower()

    if invitation_email != current_user_email:
      raise TraceException(
        "This invitation was issued for a different email address.",
        status_code=403,
        code="INVITATION_EMAIL_MISMATCH",
      )

    if not current_user.is_active:
      raise TraceException(
        "User account is inactive.",
        status_code=403,
        code="USER_INACTIVE",
      )

    if not invitation.organization.is_active:
      raise TraceException(
        "Organization is inactive.",
        status_code=403,
        code="ORGANIZATION_INACTIVE",
      )

    role = await self.repository.get_role(
      invitation.organization_id, invitation.role_id
    )
    if role is None:
      raise TraceException(
        "The role assigned to this invitation no longer exists.",
        status_code=409,
        code="INVITATION_ROLE_UNAVAILABLE",
      )

    existing_membership = await self.repository.get_membership(
      current_user.id, invitation.organization_id
    )
    if existing_membership is not None:
      raise TraceException(
        "User is already a member of this organization.",
        status_code=409,
        code="MEMBER_ALREADY_EXISTS",
      )

    membership = OrganizationMembership(
      user_id=current_user.id,
      organization_id=invitation.organization_id,
      role_id=role.id,
      is_active=True,
    )
    self.session.add(membership)

    invitation.accepted_by_user_id = current_user.id
    invitation.accepted_at = now

    has_any = await self.repository.has_any_membership(current_user.id)
    if not has_any:
      current_user.organization_id = invitation.organization_id
      current_user.role_id = role.id

    try:
      await self.session.flush()
      await self.session.commit()
    except IntegrityError as exc:
      await self.session.rollback()
      raise TraceException(
        "Unable to accept invitation.",
        status_code=409,
        code="INVITATION_ACCEPT_CONFLICT",
      ) from exc

    return InvitationAcceptanceResponse(
      message="Invitation accepted successfully.",
      organization_id=invitation.organization_id,
      organization_name=invitation.organization.name,
      role_id=role.id,
      role_name=role.name,
    )

  async def list_members(
    self,
    organization_id: UUID,
    *,
    skip: int = 0,
    limit: int = 100,
  ) -> tuple[list[User], int]:
    return await self.repository.list_members(
      organization_id, skip=skip, limit=limit
    )

  async def get_member(
    self,
    organization_id: UUID,
    user_id: UUID,
  ) -> User:
    member = await self.repository.get_member(organization_id, user_id)
    if member is None:
      raise TraceException(
        "Organization member not found.",
        status_code=404,
        code="MEMBER_NOT_FOUND",
      )
    return member

  async def update_member_role(
    self,
    organization_id: UUID,
    user_id: UUID,
    payload: MemberRoleUpdateRequest,
  ) -> User:
    member = await self.get_member(organization_id, user_id)

    role = await self.repository.get_role(organization_id, payload.role_id)
    if role is None:
      raise TraceException(
        "Role not found in this organization.",
        status_code=404,
        code="ROLE_NOT_FOUND",
      )

    membership = await self.repository.get_membership(user_id, organization_id)
    if membership is None:
      raise TraceException(
        "Membership not found.",
        status_code=404,
        code="MEMBERSHIP_NOT_FOUND",
      )

    membership.role_id = role.id
    await self.session.flush()
    await self.session.commit()

    if member.organization_id == organization_id:
      member.role_id = role.id
      await self.session.flush()

    return member

  async def update_member_status(
    self,
    organization_id: UUID,
    user_id: UUID,
    payload: MemberStatusUpdateRequest,
    current_user_id: UUID,
  ) -> User:
    member = await self.get_member(organization_id, user_id)

    membership = await self.repository.get_membership(user_id, organization_id)
    if membership is None:
      raise TraceException(
        "Membership not found.",
        status_code=404,
        code="MEMBERSHIP_NOT_FOUND",
      )

    if member.id == current_user_id and not payload.is_active:
      raise TraceException(
        "You cannot deactivate your own account.",
        status_code=400,
        code="CANNOT_DEACTIVATE_SELF",
      )

    membership.is_active = payload.is_active
    await self.session.flush()
    await self.session.commit()

    return member

  async def list_roles(self, organization_id: UUID) -> list[Role]:
    return await self.repository.list_roles(organization_id)

  async def get_role(self, organization_id: UUID, role_id: UUID) -> Role:
    role = await self.repository.get_role(organization_id, role_id)
    if role is None:
      raise TraceException(
        "Role not found.", status_code=404, code="ROLE_NOT_FOUND"
      )
    return role

  async def create_role(
    self,
    organization_id: UUID,
    payload: RoleCreateRequest,
  ) -> Role:
    existing = await self.repository.get_role_by_name(
      organization_id, payload.name
    )
    if existing is not None:
      raise TraceException(
        "A role with this name already exists.",
        status_code=409,
        code="ROLE_ALREADY_EXISTS",
      )

    permissions = await self.repository.get_permissions_by_ids(
      payload.permission_ids
    )
    if len(permissions) != len(set(payload.permission_ids)):
      raise TraceException(
        "One or more permissions are invalid.",
        status_code=400,
        code="INVALID_PERMISSIONS",
      )

    role = Role(
      id=uuid4(),
      organization_id=organization_id,
      name=payload.name.strip(),
      description=payload.description.strip() if payload.description else None,
      is_system=False,
    )
    role.permissions = permissions

    try:
      return_role = await self.repository.create_role(role)
      await self.session.commit()
      return return_role
    except IntegrityError as exc:
      await self.session.rollback()
      raise TraceException(
        "Unable to create role.",
        status_code=409,
        code="ROLE_CREATE_CONFLICT",
      ) from exc

  async def update_role(
    self,
    organization_id: UUID,
    role_id: UUID,
    payload: RoleUpdateRequest,
  ) -> Role:
    role = await self.get_role(organization_id, role_id)
    if role.is_system:
      raise TraceException(
        "System roles cannot be modified.",
        status_code=403,
        code="SYSTEM_ROLE_PROTECTED",
      )

    if payload.name is not None:
      existing = await self.repository.get_role_by_name(
        organization_id, payload.name
      )
      if existing is not None and existing.id != role.id:
        raise TraceException(
          "A role with this name already exists.",
          status_code=409,
          code="ROLE_ALREADY_EXISTS",
        )
      role.name = payload.name.strip()

    if payload.description is not None:
      role.description = payload.description.strip() or None

    if payload.permission_ids is not None:
      permissions = await self.repository.get_permissions_by_ids(
        payload.permission_ids
      )
      if len(permissions) != len(set(payload.permission_ids)):
        raise TraceException(
          "One or more permissions are invalid.",
          status_code=400,
          code="INVALID_PERMISSIONS",
        )
      role.permissions = permissions

    await self.session.flush()
    await self.session.commit()
    return role

  async def delete_role(
    self,
    organization_id: UUID,
    role_id: UUID,
  ) -> None:
    role = await self.get_role(organization_id, role_id)
    if role.is_system:
      raise TraceException(
        "System roles cannot be deleted.",
        status_code=403,
        code="SYSTEM_ROLE_PROTECTED",
      )

    assigned_users = await self.repository.count_users_with_role(
      organization_id, role.id
    )
    if assigned_users > 0:
      raise TraceException(
        "Role cannot be deleted while members are assigned to it.",
        status_code=409,
        code="ROLE_IN_USE",
      )
    await self.repository.delete_role(role)
    await self.session.commit()

  async def list_permissions(self):
    return await self.repository.list_permissions()

  @staticmethod
  def _normalize_slug(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    if not value:
      raise TraceException(
        "Organization slug is invalid.",
        status_code=422,
        code="INVALID_ORGANIZATION_SLUG",
      )
    if len(value) > 100:
      raise TraceException(
        "Organization slug is too long.",
        status_code=422,
        code="INVALID_ORGANIZATION_SLUG",
      )
    return value