from __future__ import annotations
import asyncio
from uuid import uuid4
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import Organization, Permission, PlatformAdmin, Role, User

DEFAULT_ORGANIZATION = {
  "name": "Trace Organization",
  "slug": "trace-org",
}

DEFAULT_USER = {
  "email": "admin@trace.local",
  "password": "admin12312!",
  "first_name": "Trace",
  "last_name": "Administrator",
}

async def seed_identity() -> None:
  async with AsyncSessionLocal() as session:
    organization_result = await session.execute(
      select(Organization).where(
        Organization.slug == DEFAULT_ORGANIZATION["slug"]
      )
    )
    organization = organization_result.scalar_one_or_none()

    if organization is None:
      organization = Organization(
        id=uuid4(),
        name=DEFAULT_ORGANIZATION["name"],
        slug=DEFAULT_ORGANIZATION["slug"],
        is_active=True,
      )

      session.add(organization)
      await session.flush()

    permission_definitions = {
      PermissionKey.IDENTITY_READ: (
        "View identity information."
      ),
      PermissionKey.IDENTITY_MANAGE: (
        "Manage identity information."
      ),
      PermissionKey.ORGANIZATION_READ: (
        "View organization information."
      ),
      PermissionKey.ORGANIZATION_MANAGE: (
        "Manage organization settings."
      ),
      PermissionKey.ORGANIZATION_MEMBERS_MANAGE: (
        "Manage organization members."
      ),
    }

    permissions: dict[str, Permission] = {}
    for key, description in permission_definitions.items():
      result = await session.execute(
        select(Permission).where(
          Permission.key == key.value
        )
      )
      permission = result.scalar_one_or_none()
      if permission is None:
        permission = Permission(
          id=uuid4(),
          key=key.value,
          description=description,
        )
        session.add(permission)
        await session.flush()
      permissions[key.value] = permission

    role_result = await session.execute(
      select(Role).where(
        Role.organization_id == organization.id,
        Role.name == "Company Admin",
      )
    )

    role = role_result.scalar_one_or_none()
    if role is None:
      role = Role(
        id=uuid4(),
        organization_id=organization.id,
        name = "Company Admin",
        description=(
          "Full administrative access to the organization."
        ),
        is_system=True,
      )
      role.permissions = list(
        permissions.values()
      )
      session.add(role)
      await session.flush()

    else:
      role.permissions = list(
        permissions.values()
      )
    user_result = await session.execute(
      select(User).where(
        User.email == DEFAULT_USER["email"]
      )
    )
    user = user_result.scalar_one_or_none()
    if user is None:
      user = User(
        id=uuid4(),
        organization_id=organization.id,
        role_id=role.id,
        email=DEFAULT_USER["email"],
        password_hash=hash_password(
          DEFAULT_USER["password"]
        ),
        first_name=DEFAULT_USER["first_name"],
        last_name=DEFAULT_USER["last_name"],
        is_active=True,
        is_verified=True,
      )
      session.add(user)
      await session.flush()

    else:
      user.organization_id = organization.id
      user.role_id = role.id
      user.is_active = True
      user.is_verified = True

    platform_admin_result = await session.execute(
      select(PlatformAdmin).where(
        PlatformAdmin.user_id == user.id
      )
    )
    platform_admin = (
      platform_admin_result.scalar_one_or_none()
    )

    if platform_admin is None:
      platform_admin = PlatformAdmin(
        user_id=user.id,
      )
      session.add(platform_admin)

    await session.commit()
    print("Identity seed completed.")
    print(f"Organization: {organization.slug}")
    print(f"Email: {DEFAULT_USER['email']}")
    print(f"Password: {DEFAULT_USER['password']}")

if __name__ == "__main__":
  asyncio.run(seed_identity())