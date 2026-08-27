from __future__ import annotations
import asyncio
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import Permission
from app.modules.subscriptions.models import Plan

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
      "ai_requests": 0,
    },
  },
  {
    "name": "Starter",
    "slug": "starter",
    "description": "For small construction teams.",
    "price_monthly": 0,
    "price_yearly": 0,
    "currency": "PKR",
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
  },
  {
    "name": "Professional",
    "slug": "professional",
    "description": "For growing construction companies.",
    "price_monthly": 0,
    "price_yearly": 0,
    "currency": "PKR",
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
  },
]

PERMISSIONS = [
  PermissionKey.SUBSCRIPTION_READ,
  PermissionKey.SUBSCRIPTION_MANAGE,
  PermissionKey.SUBSCRIPTION_BILLING_MANAGE,
]

async def seed_subscription_permissions(
  session: AsyncSession,
) -> None:
  for key in PERMISSIONS:
    result = await session.execute(
      select(Permission).where(
        Permission.key == str(key)
      )
    )
    permission = result.scalar_one_or_none()

    if permission is None:
      permission = Permission(
        id=uuid4(),
        key=str(key),
        description=key.value,
      )
      session.add(permission)

  await session.flush()

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
        is_active=True,
        is_public=True,
        features=data["features"],
        quotas=data["quotas"],
      )

      session.add(plan)
    else:
      plan.name = data["name"]
      plan.description = data["description"]
      plan.price_monthly = data["price_monthly"]
      plan.price_yearly = data["price_yearly"]
      plan.currency = data["currency"]
      plan.features = data["features"]
      plan.quotas = data["quotas"]
      plan.is_active = True
      plan.is_public = True

  await session.commit()

async def main():
  async with AsyncSessionLocal() as session:
    await seed_subscription_permissions(session)
    await seed_plans(session)

  print("Subscription module seeding completed successfully.")

if __name__ == "__main__":
  asyncio.run(main())