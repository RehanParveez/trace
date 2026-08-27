from __future__ import annotations
import asyncio
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import Organization, OrganizationInvitation, OrganizationMembership, Permission, PlatformAdmin, Role, User

ORGANIZATION_NAME = "Acme Corp"
ORGANIZATION_SLUG = "acme-corp"

ADMIN_ROLE_NAME = "Admin"
MEMBER_ROLE_NAME = "Member"
VIEWER_ROLE_NAME = "Viewer"

PLATFORM_ADMIN_EMAIL = "admin@gmail.com"
PLATFORM_ADMIN_PASSWORD_HASH = (
  "$argon2id$v=19$m=65536,t=3,p=4$..."
)
PLATFORM_ADMIN_FIRST_NAME = "Platform"
PLATFORM_ADMIN_LAST_NAME = "Admin"

USER_1_EMAIL = "riaz@gmail.com"
USER_1_PASSWORD_HASH = "$argon2id$v=19$m=65536,t=3,p=4$..."
USER_1_FIRST_NAME = "Malik"
USER_1_LAST_NAME = "Riaz"

USER_2_EMAIL = "saif@gmail.com"
USER_2_PASSWORD_HASH = "$argon2id$v=19$m=65536,t=3,p=4$..."
USER_2_FIRST_NAME = "Saif"
USER_2_LAST_NAME = "ur-Rehman"

async def seed_permissions(session: AsyncSession) -> dict[PermissionKey, Permission]:
  permission_keys = [
    PermissionKey.ORGANIZATION_READ,
    PermissionKey.ORGANIZATION_MANAGE,
    PermissionKey.ORGANIZATION_MEMBERS_MANAGE,
  ]

  permissions: dict[PermissionKey, Permission] = {}

  for key in permission_keys:
    result = await session.execute(
      select(Permission).where(Permission.key == str(key))
    )
    perm = result.scalar_one_or_none()
    if perm is None:
      perm = Permission(
        id=uuid4(),
        key=str(key),
        description=key.value,
      )
      session.add(perm)
      await session.flush()
    permissions[key] = perm

  await session.commit()
  return permissions

async def seed_organization(
  session: AsyncSession,
) -> Organization:

  result = await session.execute(
    select(Organization).where(Organization.slug == ORGANIZATION_SLUG)
  )
  org = result.scalar_one_or_none()
  if org is None:
    org = Organization(
      id=uuid4(),
      name=ORGANIZATION_NAME,
      slug=ORGANIZATION_SLUG,
      is_active=True,
      ai_enabled=False,
    )
    session.add(org)
    await session.flush()
    await session.commit()
  return org

async def seed_roles(
  session: AsyncSession,
  organization: Organization,
  permissions: dict[PermissionKey, Permission],
) -> dict[str, Role]:

  roles: dict[str, Role] = {}

  async def get_or_create_role(
    name: str,
    is_system: bool,
    permission_keys: list[PermissionKey],
    description: str | None = None,
  ) -> Role:
    result = await session.execute(
      select(Role).where(
        Role.organization_id == organization.id,
        func.lower(Role.name) == func.lower(name),
      )
    )
    role = result.scalar_one_or_none()
    if role is None:
      role = Role(
        id=uuid4(),
        organization_id=organization.id,
        name=name,
        description=description,
        is_system=is_system,
      )
      role.permissions = [permissions[k] for k in permission_keys]
      session.add(role)
      await session.flush()
    else:
      current_perm_ids = {p.id for p in role.permissions}
      desired_perms = [permissions[k] for k in permission_keys]
      for p in desired_perms:
        if p.id not in current_perm_ids:
          role.permissions.append(p)
      await session.flush()
    return role

  admin_role = await get_or_create_role(
    ADMIN_ROLE_NAME,
    is_system=True,
    permission_keys=[
      PermissionKey.ORGANIZATION_READ,
      PermissionKey.ORGANIZATION_MANAGE,
      PermissionKey.ORGANIZATION_MEMBERS_MANAGE,
    ],
    description="Full organization administrator.",
  )
  member_role = await get_or_create_role(
    MEMBER_ROLE_NAME,
    is_system=False,
    permission_keys=[
      PermissionKey.ORGANIZATION_READ,
      PermissionKey.ORGANIZATION_MEMBERS_MANAGE,
    ],
    description="Standard member with member management.",
  )
  viewer_role = await get_or_create_role(
    VIEWER_ROLE_NAME,
    is_system=False,
    permission_keys=[
      PermissionKey.ORGANIZATION_READ,
    ],
    description="Read-only access to organization.",
  )
  roles[ADMIN_ROLE_NAME] = admin_role
  roles[MEMBER_ROLE_NAME] = member_role
  roles[VIEWER_ROLE_NAME] = viewer_role

  await session.commit()
  return roles

async def seed_users_and_memberships(
  session: AsyncSession,
  organization: Organization,
  roles: dict[str, Role],
) -> list[User]:

  users: list[User] = []

  result = await session.execute(
    select(User).where(func.lower(User.email) == func.lower(PLATFORM_ADMIN_EMAIL))
  )
  user_admin = result.scalar_one_or_none()
  if user_admin is None:
    user_admin = User(
      id=uuid4(),
      email=PLATFORM_ADMIN_EMAIL,
      password_hash=PLATFORM_ADMIN_PASSWORD_HASH,
      first_name=PLATFORM_ADMIN_FIRST_NAME,
      last_name=PLATFORM_ADMIN_LAST_NAME,
      is_active=True,
      is_verified=True,
      organization_id=organization.id,
      role_id=roles[ADMIN_ROLE_NAME].id,
    )
    session.add(user_admin)
    await session.flush()

    membership_admin = OrganizationMembership(
      id=uuid4(),
      user_id=user_admin.id,
      organization_id=organization.id,
      role_id=roles[ADMIN_ROLE_NAME].id,
      is_active=True,
    )
    session.add(membership_admin)
    users.append(user_admin)

  result = await session.execute(
    select(User).where(func.lower(User.email) == func.lower(USER_1_EMAIL))
  )
  user1 = result.scalar_one_or_none()
  if user1 is None:
    user1 = User(
      id=uuid4(),
      email=USER_1_EMAIL,
      password_hash=USER_1_PASSWORD_HASH,
      first_name=USER_1_FIRST_NAME,
      last_name=USER_1_LAST_NAME,
      is_active=True,
      is_verified=True,
      organization_id=organization.id,
      role_id=roles[ADMIN_ROLE_NAME].id,
    )
    session.add(user1)
    await session.flush()

    membership1 = OrganizationMembership(
      id=uuid4(),
      user_id=user1.id,
      organization_id=organization.id,
      role_id=roles[ADMIN_ROLE_NAME].id,
      is_active=True,
    )
    session.add(membership1)
    users.append(user1)

  result = await session.execute(
    select(User).where(func.lower(User.email) == func.lower(USER_2_EMAIL))
  )
  user2 = result.scalar_one_or_none()
  if user2 is None:
    user2 = User(
      id=uuid4(),
      email=USER_2_EMAIL,
      password_hash=USER_2_PASSWORD_HASH,
      first_name=USER_2_FIRST_NAME,
      last_name=USER_2_LAST_NAME,
      is_active=True,
      is_verified=True,
      organization_id=organization.id,
      role_id=roles[MEMBER_ROLE_NAME].id,
    )
    session.add(user2)
    await session.flush()

    membership2 = OrganizationMembership(
      id=uuid4(),
      user_id=user2.id,
      organization_id=organization.id,
      role_id=roles[MEMBER_ROLE_NAME].id,
      is_active=True,
    )
    session.add(membership2)
    users.append(user2)

  await session.commit()
  return users

async def seed_platform_admin(
  session: AsyncSession,
  admin_user: User,
) -> None:

  result = await session.execute(
    select(PlatformAdmin).where(PlatformAdmin.user_id == admin_user.id)
  )
  pa = result.scalar_one_or_none()
  if pa is None:
    pa = PlatformAdmin(
      user_id=admin_user.id,
      created_at=datetime.now(timezone.utc),
    )
    session.add(pa)
    await session.commit()

async def seed_sample_invitation(
  session: AsyncSession,
  organization: Organization,
  roles: dict[str, Role],
  invited_by_user: User,
) -> OrganizationInvitation:

  email = "newmember@gmail.com"
  raw_token = secrets.token_urlsafe(48)
  token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

  invitation = OrganizationInvitation(
    id=uuid4(),
    organization_id=organization.id,
    role_id=roles[VIEWER_ROLE_NAME].id,
    invited_by_user_id=invited_by_user.id,
    email=email,
    token_hash=token_hash,
    expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    accepted_at=None,
    revoked_at=None,
  )

  session.add(invitation)
  await session.commit()
  return invitation

async def main():
  async with AsyncSessionLocal() as session:
    permissions = await seed_permissions(session)
    organization = await seed_organization(session)
    roles = await seed_roles(session, organization, permissions)
    users = await seed_users_and_memberships(session, organization, roles)

    await seed_platform_admin(session, users[0])
    await seed_sample_invitation(session, organization, roles, users[0])
    print("Seeding completed successfully.")

if __name__ == "__main__":
  asyncio.run(main())