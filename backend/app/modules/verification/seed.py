from __future__ import annotations
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import Permission, Role
from app.modules.verification.permissions import VERIFICATION_PERMISSIONS

async def seed_verification_permissions(
  session: AsyncSession,
) -> None:
  for permission_key, description in VERIFICATION_PERMISSIONS.items():
    result = await session.execute(
      select(Permission).where(
        Permission.key == permission_key,
      )
    )
    permission = result.scalar_one_or_none()
    if permission is None:
      permission = Permission(
        key=permission_key,
        description=description,
      )
      session.add(permission)

  await session.flush()

async def seed_verification() -> None:
  async with AsyncSessionLocal() as session:
    await seed_verification_permissions(session)

    result = await session.execute(
      select(Role).where(Role.is_system.is_(True))
    )
    roles = result.scalars().all()

    permissions_result = await session.execute(
      select(Permission).where(
        Permission.key.in_(list(VERIFICATION_PERMISSIONS.keys()))
      )
    )
    permissions = {
      permission.key: permission
      for permission in permissions_result.scalars().all()
    }

    allowed = {
      PermissionKey.PROGRESS_CLAIM_READ,
      PermissionKey.PROGRESS_CLAIM_CREATE,
      PermissionKey.PROGRESS_CLAIM_UPDATE,
      PermissionKey.PROGRESS_CLAIM_SUBMIT,
      PermissionKey.PROGRESS_CLAIM_REVIEW,
      PermissionKey.PHOTO_BOQ_LINK_READ,
      PermissionKey.PHOTO_BOQ_LINK_MANAGE,
    }

    for role in roles:
      for key in allowed:
        permission = permissions.get(key)
        if permission is not None and permission not in role.permissions:
          role.permissions.append(permission)

    await session.commit()

    print("Verification seed completed.")

if __name__ == "__main__":
  asyncio.run(seed_verification())