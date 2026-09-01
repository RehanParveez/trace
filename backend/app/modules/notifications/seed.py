from __future__ import annotations
import asyncio
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.modules.identity.models import Permission
from app.modules.notifications.permissions import NOTIFICATION_PERMISSIONS

async def seed_notification_permissions(session: AsyncSession) -> None:
  for key, description in NOTIFICATION_PERMISSIONS.items():
    result = await session.execute(
      select(Permission).where(Permission.key == str(key))
    )
    if result.scalar_one_or_none() is None:
      session.add(
        Permission(
          id=uuid4(),
          key=str(key),
          description=description,
        )
      )
  await session.commit()

async def main():
  async with AsyncSessionLocal() as session:
    await seed_notification_permissions(session)
  print("Notifications module seeding completed successfully.")

if __name__ == "__main__":
  asyncio.run(main())