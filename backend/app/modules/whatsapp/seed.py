from __future__ import annotations
import asyncio
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import AsyncSessionLocal
from app.modules.identity.models import Permission, Role
from app.modules.whatsapp.permissions import WHATSAPP_PERMISSIONS
 
DEFAULT_ROLE_NAME = "Company Admin"
 
async def seed_whatsapp() -> None:
  async with AsyncSessionLocal() as session:
    permissions: dict[str, Permission] = {}
 
    for permission_key, description in WHATSAPP_PERMISSIONS.items():
      result = await session.execute(
        select(Permission).where(
          Permission.key == permission_key.value
        )
      )
      permission = result.scalar_one_or_none()
 
      if permission is None:
        permission = Permission(
          id=uuid4(),
          key=permission_key.value,
          description=description,
        )
        session.add(permission)
        await session.flush()
 
      permissions[permission_key.value] = permission
 
    role_result = await session.execute(
      select(Role)
      .where(Role.name == DEFAULT_ROLE_NAME)
      .options(selectinload(Role.permissions))
    )
    roles = role_result.scalars().all()
 
    if not roles:
      print(
        f"No '{DEFAULT_ROLE_NAME}' roles found; "
        "run identity seed first."
      )
      return
 
    total_new = 0
    for role in roles:
      current_permission_keys = {
        permission.key for permission in role.permissions
      }
      new_permissions = [
        permission
        for key, permission in permissions.items()
        if key not in current_permission_keys
      ]
      if new_permissions:
        role.permissions.extend(new_permissions)
        total_new += len(new_permissions)
 
    await session.commit()
 
    print("WhatsApp seed completed.")
    print(f"Roles updated: {len(roles)}")
    print(f"Permissions ensured: {len(permissions)}")
    print(f"New permission grants: {total_new}")
 
if __name__ == "__main__":
  asyncio.run(seed_whatsapp())