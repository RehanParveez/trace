from __future__ import annotations
import asyncio
from app.core.database import AsyncSessionLocal
from app.modules.verification.permissions import VERIFICATION_PERMISSIONS
from app.shared.seed_utils import seed_module_permissions

async def seed_verification() -> None:
  async with AsyncSessionLocal() as session:
    await seed_module_permissions(session, VERIFICATION_PERMISSIONS)
    await session.commit()
  print("Verification seed completed.")

if __name__ == "__main__":
  asyncio.run(seed_verification())