from __future__ import annotations
from app.core.database import AsyncSessionLocal
import asyncio
from app.shared.seed_utils import seed_module_permissions
from app.modules.change_orders.permissions import CHANGE_ORDER_PERMISSIONS

async def main() -> None:
  async with AsyncSessionLocal() as session:
    await seed_module_permissions(session, CHANGE_ORDER_PERMISSIONS)
    await session.commit()
  print("Change orders module seeded (permissions only).")

if __name__ == "__main__":
  asyncio.run(main())