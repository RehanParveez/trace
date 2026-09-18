from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import Permission, Role
from sqlalchemy import select
from uuid import uuid4
from sqlalchemy.orm import selectinload

async def seed_module_permissions(
  session: AsyncSession,
  permission_definitions: dict[PermissionKey, str],
) -> dict[PermissionKey, Permission]:
  permissions: dict[PermissionKey, Permission] = {}

  for key, description in permission_definitions.items():
    result = await session.execute(
      select(Permission).where(Permission.key == key.value)
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

    permissions[key] = permission

  role_result = await session.execute(
    select(Role)
    .where(Role.is_system.is_(True))
    .options(selectinload(Role.permissions))
    )
  roles = list(role_result.scalars().unique())
  if not roles:
    return permissions

  for role in roles:
    current_ids = {p.id for p in role.permissions}
    role.permissions.extend(
      p for p in permissions.values() if p.id not in current_ids
    )

  await session.flush()
  return permissions