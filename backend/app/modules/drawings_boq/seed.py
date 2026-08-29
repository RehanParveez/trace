from __future__ import annotations
import asyncio
from uuid import uuid4
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.database import AsyncSessionLocal
from app.modules.drawings_boq.models import MaterialLibrary
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import Organization, Permission, Role

MATERIAL_ENTRIES = [
  {
    "raw_text": "concrete grade 25",
    "normalized_name": "Concrete Grade 25 (M25)",
    "category": "Concrete",
    "default_unit": "m3",
  },
  {
    "raw_text": "concrete grade 30",
    "normalized_name": "Concrete Grade 30 (M30)",
    "category": "Concrete",
    "default_unit": "m3",
  },
  {
    "raw_text": "concrete gr45",
    "normalized_name": "Concrete Grade 45 (M45)",
    "category": "Concrete",
    "default_unit": "m3",
  },
  {
    "raw_text": "steel rebar grade 60",
    "normalized_name": "Steel Reinforcement Bar Grade 60",
    "category": "Steel",
    "default_unit": "kg",
  },
  {
    "raw_text": "burnt clay brick",
    "normalized_name": "Burnt Clay Brick (Standard)",
    "category": "Masonry",
    "default_unit": "unit",
  },
  {
    "raw_text": "cement opc",
    "normalized_name": "Ordinary Portland Cement",
    "category": "Cement",
    "default_unit": "kg",
  },
]

PERMISSIONS = [
  PermissionKey.DRAWING_READ,
  PermissionKey.DRAWING_CREATE,
  PermissionKey.DRAWING_DELETE,
  PermissionKey.BOQ_UPDATE,
  PermissionKey.BOQ_APPROVE,
  PermissionKey.MATERIAL_LIBRARY_MANAGE,
]

async def seed_permissions(
  session: AsyncSession,
) -> dict[PermissionKey, Permission]:
  permissions: dict[PermissionKey, Permission] = {}
  for key in PERMISSIONS:
    result = await session.execute(
      select(Permission).where(Permission.key == str(key))
    )
    permission = result.scalar_one_or_none()
    if permission is None:
      permission = Permission(
        id=uuid4(),
        key=str(key),
        description=key.value,
      )
      session.add(permission)
      await session.flush()
    permissions[key] = permission
  return permissions

async def grant_permissions_to_admin_roles(
  session: AsyncSession,
  permissions: dict[PermissionKey, Permission],
) -> None:
  result = await session.execute(
    select(Role)
    .where(func.lower(Role.name) == "admin")
    .options(selectinload(Role.permissions))
  )
  admin_roles = list(result.scalars().unique())

  for role in admin_roles:
    current_ids = {permission.id for permission in role.permissions}
    for permission in permissions.values():
      if permission.id not in current_ids:
        role.permissions.append(permission)

  await session.flush()

async def seed_material_library(
  session: AsyncSession,
) -> None:
  organization_result = await session.execute(
    select(Organization)
    .order_by(Organization.created_at.asc())
    .limit(1)
  )
  organization = organization_result.scalar_one_or_none()
  if organization is None:
    print(
      "Skipping material library seed: "
      "no organization exists."
    )
    return

  for data in MATERIAL_ENTRIES:
    existing = await session.execute(
      select(MaterialLibrary).where(
        MaterialLibrary.organization_id == organization.id,
        MaterialLibrary.raw_text == data["raw_text"],
      )
    )
    if existing.scalar_one_or_none() is None:
      session.add(
        MaterialLibrary(
          id=uuid4(),
          organization_id=organization.id,
          raw_text=data["raw_text"],
          normalized_name=data["normalized_name"],
          category=data["category"],
          default_unit=data["default_unit"],
        )
      )

async def main():
  async with AsyncSessionLocal() as session:
    permissions = await seed_permissions(session)
    await grant_permissions_to_admin_roles(session, permissions)
    await seed_material_library(session)
    await session.commit()
  print(
    "Drawings & BOQ module seeding completed successfully."
  )

if __name__ == "__main__":
  asyncio.run(main())