from __future__ import annotations
import asyncio
from app.core.database import AsyncSessionLocal
from app.shared.seed_utils import seed_module_permissions
from app.modules.withholding_tax.permissions import WITHHOLDING_TAX_PERMISSIONS

async def main() -> None:
  async with AsyncSessionLocal() as session:
    await seed_module_permissions(session, WITHHOLDING_TAX_PERMISSIONS)
    await session.commit() 
    
  print(
    "Withholding tax module seeded (permissions only). No rates were "
    "seeded — configure your organization's current FBR-notified rates "
    "under Withholding Tax settings before recording any deductions."
  )

if __name__ == "__main__":
  asyncio.run(main())