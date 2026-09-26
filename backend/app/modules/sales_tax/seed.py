from __future__ import annotations
from app.core.database import AsyncSessionLocal
import asyncio
from app.shared.seed_utils import seed_module_permissions
from app.modules.sales_tax.permissions import SALES_TAX_PERMISSIONS

async def main() -> None:
  async with AsyncSessionLocal() as session:
    await seed_module_permissions(session, SALES_TAX_PERMISSIONS)
    await session.commit()
  print(
    "Sales tax module seeded (permissions only). No rates were seeded — "
    "configure your organization's current provincial rate(s) under Sales Tax "
    "settings before generating any bills with sales tax applied."
  )

if __name__ == "__main__":
  asyncio.run(main())