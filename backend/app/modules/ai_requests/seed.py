from __future__ import annotations
import asyncio
from app.core.database import AsyncSessionLocal
from app.modules.ai_requests.permissions import AI_REQUEST_PERMISSIONS
from app.shared.seed_utils import seed_module_permissions

async def main():
  async with AsyncSessionLocal() as session:
    await seed_module_permissions(session, AI_REQUEST_PERMISSIONS)
    await session.commit()
  print("AI requests module seeding completed successfully.")

if __name__ == "__main__":
  asyncio.run(main())