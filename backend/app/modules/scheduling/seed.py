from __future__ import annotations
import asyncio
from app.core.database import AsyncSessionLocal
from app.shared.seed_utils import seed_module_permissions
from app.modules.scheduling.permissions import SCHEDULING_PERMISSIONS

async def main() -> None:
  async with AsyncSessionLocal() as session:
    await seed_module_permissions(session, SCHEDULING_PERMISSIONS)
    await session.commit()
  print("Scheduling module seeded (permissions only).")

if __name__ == "__main__":
  asyncio.run(main())