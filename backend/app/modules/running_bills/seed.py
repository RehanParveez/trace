from __future__ import annotations
import asyncio
from app.core.database import AsyncSessionLocal
from app.shared.seed_utils import seed_module_permissions
from app.modules.running_bills.permissions import RUNNING_BILL_PERMISSIONS

async def main() -> None:
  async with AsyncSessionLocal() as session:
    await seed_module_permissions(session, RUNNING_BILL_PERMISSIONS)
    await session.commit()  
  print("Running bills module seeded (permissions only — real bills need real approved progress claims).")

if __name__ == "__main__":
  asyncio.run(main())