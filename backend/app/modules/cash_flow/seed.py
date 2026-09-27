from __future__ import annotations
import asyncio
from app.core.database import AsyncSessionLocal
from app.shared.seed_utils import seed_module_permissions
from app.modules.cash_flow.permissions import CASH_FLOW_PERMISSIONS

async def main() -> None:
  async with AsyncSessionLocal() as session:
    await seed_module_permissions(session, CASH_FLOW_PERMISSIONS)
    await session.commit()
  print("Cash flow module seeded (permissions only). Default payment-terms assumptions apply until adjusted per organization.")

if __name__ == "__main__":
  asyncio.run(main())