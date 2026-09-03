from app.core.database import AsyncSessionLocal
from app.modules.identity.models import Organization
from uuid import UUID
from app.modules.subscriptions.service import SubscriptionService
import asyncio
import sys

async def main(org_id: str) -> None:
  async with AsyncSessionLocal() as session:
    org = await session.get(Organization, UUID(org_id))
    if org is None:
      print(f"No organization found with id {org_id}")
      return
    service = SubscriptionService(session)
    subscription = await service.create_initial_subscription(org, plan_slug="free")
    print(f"Subscription ready: {subscription.id} (status={subscription.status})")

if __name__ == "__main__":
  asyncio.run(main(sys.argv[1]))