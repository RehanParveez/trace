from __future__ import annotations
import asyncio
from app.core.database import AsyncSessionLocal
from app.shared.seed_utils import seed_module_permissions
from app.modules.labour.permissions import LABOUR_PERMISSIONS

async def main() -> None:
  async with AsyncSessionLocal() as session:
    await seed_module_permissions(session, LABOUR_PERMISSIONS)
    await session.commit()
  print("Labour module seeded (permissions only — no fake workers, sources or attendance).")

if __name__ == "__main__":
  asyncio.run(main())