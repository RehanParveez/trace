from __future__ import annotations
import asyncio
from app.core.database import AsyncSessionLocal
from app.shared.seed_utils import seed_module_permissions
from app.modules.bank_guarantees.permissions import BANK_GUARANTEE_PERMISSIONS

async def main() -> None:
  async with AsyncSessionLocal() as session:
    await seed_module_permissions(session, BANK_GUARANTEE_PERMISSIONS)
    await session.commit()
  print("Bank guarantees module seeded (permissions only).")

if __name__ == "__main__":
  asyncio.run(main())