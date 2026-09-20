from __future__ import annotations
import asyncio
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.modules.identity.models import Organization
from app.modules.subscriptions.models import Plan
from app.modules.subscriptions.service import SubscriptionService
from app.shared.seed_utils import seed_module_permissions
from app.modules.subscriptions.permissions import SUBSCRIPTION_PERMISSIONS
from decimal import Decimal

PLANS = [
  {
    "name": "Free",
    "slug": "free",
    "description": "Basic access for evaluation.",
    "price_monthly": 0,
    "price_yearly": 0,
    "currency": "PKR",
    "features": {
      "projects": True,
      "site_logs": True,
      "basic_boq": True,
      "ai": False,
    },
    "quotas": {
      "projects": 3,
      "storage_bytes": 1073741824,
      "site_photos": 100,
      "drawings": 3,
      "ai_requests": 10,
    },
  },
  
  {
    "name": "Starter",
    "slug": "starter",
    "description": "For small construction teams.",
    "price_monthly": Decimal("4999"),
    "price_yearly": Decimal("49999"),
    "currency": "PKR",
    "trial_days": 14,
    "sort_order": 10,
    "is_default": False,
    "features": {
      "projects": True,
      "site_logs": True,
      "basic_boq": True,
      "ai": True,
    },
    "quotas": {
      "projects": 10,
      "storage_bytes": 5368709120,
      "site_photos": 1000,
      "drawings": 20,
      "ai_requests": 100,
    },
    "limit_policy": {"ai_requests": "soft", "storage_bytes": "hard"},
  },
  
  {
    "name": "Professional",
    "slug": "professional",
    "description": "For growing construction companies.",
    "price_monthly": Decimal("14999"),
    "price_yearly":  Decimal("149999"),
    "currency": "PKR",
    "trial_days": 14,
    "sort_order": 20,
    "is_default": False,
    "features": {
      "projects": True,
      "site_logs": True,
      "basic_boq": True,
      "ai": True,
      "advanced_boq": True,
    },
    "quotas": {
      "projects": 50,
      "storage_bytes": 26843545600,
      "site_photos": 10000,
      "drawings": 100,
      "ai_requests": 1000,
    },
    "limit_policy": {"ai_requests": "soft", "storage_bytes": "hard"},
  },
]

async def seed_plans(
  session: AsyncSession,
) -> None:
  for data in PLANS:
    result = await session.execute(
      select(Plan).where(
        Plan.slug == data["slug"]
      )
    )

    plan = result.scalar_one_or_none()

    if plan is None:
      plan = Plan(
        id=uuid4(),
        name=data["name"],
        slug=data["slug"],
        description=data["description"],
        price_monthly=data["price_monthly"],
        price_yearly=data["price_yearly"],
        currency=data["currency"],
        trial_days=data.get("trial_days", 0),
        sort_order=data.get("sort_order", 0),
        is_default=data.get("is_default", False),
        is_active=True,
        is_public=True,
        features=data["features"],
        quotas=data["quotas"],
        limit_policy=data.get("limit_policy", {}),
      )

      session.add(plan)
      
    else:
      plan.name = data["name"]
      plan.description = data["description"]
      plan.price_monthly = data["price_monthly"]
      plan.price_yearly = data["price_yearly"]
      plan.trial_days = data.get("trial_days", plan.trial_days)
      plan.sort_order = data.get("sort_order", plan.sort_order)
      plan.is_default = data.get("is_default", plan.is_default)
      plan.features = data["features"]
      plan.quotas = data["quotas"]
      plan.limit_policy = data.get("limit_policy", plan.limit_policy or {})
      plan.is_active = True
      plan.is_public = True

  await session.commit()
  
async def seed_default_subscriptions(
  session: AsyncSession,
) -> None:
  service = SubscriptionService(session)
  result = await session.execute(select(Organization))
  organizations = result.scalars().all()

  for organization in organizations:
    await service.create_initial_subscription(organization)

async def main():
  async with AsyncSessionLocal() as session:
    await seed_module_permissions(session, SUBSCRIPTION_PERMISSIONS)
    await seed_plans(session)

  print("Subscription module seeding completed successfully.")

if __name__ == "__main__":
  asyncio.run(main())