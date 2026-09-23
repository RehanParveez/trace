from __future__ import annotations
import asyncio
from app.core.database import AsyncSessionLocal
from app.shared.seed_utils import seed_module_permissions
from app.modules.retention.permissions import RETENTION_PERMISSIONS

async def main() -> None:
  async with AsyncSessionLocal() as session:
    await seed_module_permissions(session, RETENTION_PERMISSIONS)
    await session.commit()
  print("Retention module seeded (permissions only).")

if __name__ == "__main__":
  asyncio.run(main())