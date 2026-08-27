from __future__ import annotations
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.modules.identity.models import Organization, OrganizationInvitation, OrganizationMembership, Permission, Role, User

class OrganizationRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create_invitation(
    self,
    invitation: OrganizationInvitation,
  ) -> OrganizationInvitation:
    self.session.add(invitation)
    await self.session.flush()
    return invitation

  async def get_invitation(
    self,
    organization_id: UUID,
    invitation_id: UUID,
  ) -> OrganizationInvitation | None:
    result = await self.session.execute(
      select(OrganizationInvitation)
      .where(
        OrganizationInvitation.id == invitation_id,
        OrganizationInvitation.organization_id == organization_id,
      )
      .options(
        selectinload(OrganizationInvitation.role),
        selectinload(OrganizationInvitation.invited_by),
      )
    )
    return result.scalar_one_or_none()

  async def get_invitation_by_token_hash(
    self,
    token_hash: str,
  ) -> OrganizationInvitation | None:
    result = await self.session.execute(
      select(OrganizationInvitation)
      .where(OrganizationInvitation.token_hash == token_hash)
      .options(
        selectinload(OrganizationInvitation.organization),
        selectinload(OrganizationInvitation.role),
      )
    )
    return result.scalar_one_or_none()

  async def get_pending_invitation_for_email(
    self,
    organization_id: UUID,
    email: str,
  ) -> OrganizationInvitation | None:
    result = await self.session.execute(
      select(OrganizationInvitation)
      .where(
        OrganizationInvitation.organization_id == organization_id,
        OrganizationInvitation.email == email,
        OrganizationInvitation.accepted_at.is_(None),
        OrganizationInvitation.revoked_at.is_(None),
        OrganizationInvitation.expires_at > func.now(),
      )
      .order_by(OrganizationInvitation.created_at.desc())
      .limit(1)
    )
    return result.scalar_one_or_none()

  async def list_invitations(
    self,
    organization_id: UUID,
    *,
    skip: int = 0,
    limit: int = 100,
  ) -> tuple[list[OrganizationInvitation], int]:
    count_result = await self.session.execute(
      select(func.count())
      .select_from(OrganizationInvitation)
      .where(OrganizationInvitation.organization_id == organization_id)
    )
    total = count_result.scalar_one()

    result = await self.session.execute(
      select(OrganizationInvitation)
      .where(OrganizationInvitation.organization_id == organization_id)
      .options(
        selectinload(OrganizationInvitation.role),
        selectinload(OrganizationInvitation.invited_by),
      )
      .order_by(OrganizationInvitation.created_at.desc())
      .offset(skip)
      .limit(limit)
    )

    invitations = list(result.scalars().unique())
    return invitations, total

  async def revoke_invitation(
    self,
    invitation: OrganizationInvitation,
  ) -> None:
    await self.session.flush()

  async def get_organization(
    self,
    organization_id: UUID,
  ) -> Organization | None:
    result = await self.session.execute(
      select(Organization).where(Organization.id == organization_id)
    )
    return result.scalar_one_or_none()

  async def get_organization_for_update(
    self,
    organization_id: UUID,
  ) -> Organization | None:
    result = await self.session.execute(
      select(Organization)
      .where(Organization.id == organization_id)
      .with_for_update()
    )
    return result.scalar_one_or_none()

  async def get_by_slug(
    self,
    slug: str,
  ) -> Organization | None:
    result = await self.session.execute(
      select(Organization).where(Organization.slug == slug)
    )
    return result.scalar_one_or_none()

  async def update_organization(
    self,
    organization: Organization,
  ) -> Organization:
    self.session.add(organization)
    await self.session.flush()
    return organization

  async def get_membership(
    self,
    user_id: UUID,
    organization_id: UUID,
  ) -> OrganizationMembership | None:
    result = await self.session.execute(
      select(OrganizationMembership)
      .where(
        OrganizationMembership.user_id == user_id,
        OrganizationMembership.organization_id == organization_id,
      )
      .options(
        selectinload(OrganizationMembership.role).selectinload(
          Role.permissions
        ),
        selectinload(OrganizationMembership.organization),
      )
    )
    return result.scalar_one_or_none()

  async def list_memberships_for_user(
    self,
    user_id: UUID,
  ) -> list[OrganizationMembership]:
    result = await self.session.execute(
      select(OrganizationMembership)
      .where(OrganizationMembership.user_id == user_id)
      .options(
        selectinload(OrganizationMembership.role).selectinload(
          Role.permissions
        ),
        selectinload(OrganizationMembership.organization),
      )
    )
    return list(result.scalars().unique())

  async def has_any_membership(
    self,
    user_id: UUID,
  ) -> bool:
    result = await self.session.execute(
      select(func.count())
      .select_from(OrganizationMembership)
      .where(OrganizationMembership.user_id == user_id)
    )
    return result.scalar_one() > 0

  async def get_member_by_email_in_org(
    self,
    organization_id: UUID,
    email: str,
  ) -> User | None:
    user_result = await self.session.execute(
      select(User).where(func.lower(User.email) == func.lower(email))
    )
    user = user_result.scalar_one_or_none()
    if user is None:
      return None

    membership = await self.get_membership(user.id, organization_id)
    return user if membership is not None else None

  async def get_member(
    self,
    organization_id: UUID,
    user_id: UUID,
  ) -> User | None:
    membership = await self.get_membership(user_id, organization_id)
    if membership is None:
      return None

    result = await self.session.execute(
      select(User)
      .where(User.id == user_id)
      .options(
        selectinload(User.role).selectinload(Role.permissions),
      )
    )
    return result.scalar_one_or_none()

  async def list_members(
    self,
    organization_id: UUID,
    *,
    skip: int = 0,
    limit: int = 100,
  ) -> tuple[list[User], int]:
    count_result = await self.session.execute(
      select(func.count())
      .select_from(OrganizationMembership)
      .where(OrganizationMembership.organization_id == organization_id)
    )
    total = count_result.scalar_one()

    result = await self.session.execute(
      select(User)
      .join(
        OrganizationMembership,
        OrganizationMembership.user_id == User.id,
      )
      .where(OrganizationMembership.organization_id == organization_id)
      .options(
        selectinload(User.role).selectinload(Role.permissions),
      )
      .order_by(User.created_at.asc())
      .offset(skip)
      .limit(limit)
    )
    return list(result.scalars().unique()), total

  async def get_role(
    self,
    organization_id: UUID,
    role_id: UUID,
  ) -> Role | None:
    result = await self.session.execute(
      select(Role)
      .where(
        Role.id == role_id,
        Role.organization_id == organization_id,
      )
      .options(selectinload(Role.permissions))
    )
    return result.scalar_one_or_none()

  async def get_role_by_name(
    self,
    organization_id: UUID,
    name: str,
  ) -> Role | None:
    result = await self.session.execute(
      select(Role)
      .where(
        Role.organization_id == organization_id,
        func.lower(Role.name) == func.lower(name),
      )
    )
    return result.scalar_one_or_none()

  async def list_roles(
    self,
    organization_id: UUID,
  ) -> list[Role]:
    result = await self.session.execute(
      select(Role)
      .where(Role.organization_id == organization_id)
      .options(selectinload(Role.permissions))
      .order_by(Role.is_system.desc(), Role.name.asc())
    )
    return list(result.scalars().unique())

  async def create_role(
    self,
    role: Role,
  ) -> Role:
    self.session.add(role)
    await self.session.flush()
    await self.session.refresh(role, attribute_names=["permissions"])
    return role

  async def delete_role(
    self,
    role: Role,
  ) -> None:
    await self.session.delete(role)
    await self.session.flush()

  async def get_permissions_by_ids(
    self,
    permission_ids: list[UUID],
  ) -> list[Permission]:
    if not permission_ids:
      return []

    result = await self.session.execute(
      select(Permission).where(Permission.id.in_(permission_ids))
    )
    return list(result.scalars().all())

  async def list_permissions(self) -> list[Permission]:
    result = await self.session.execute(
      select(Permission).order_by(Permission.key.asc())
    )
    return list(result.scalars().all())

  async def count_users_with_role(
    self,
    organization_id: UUID,
    role_id: UUID,
  ) -> int:
    result = await self.session.execute(
      select(func.count())
      .select_from(OrganizationMembership)
      .where(
        OrganizationMembership.organization_id == organization_id,
        OrganizationMembership.role_id == role_id,
      )
    )
    return result.scalar_one()