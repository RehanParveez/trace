from __future__ import annotations
from datetime import datetime
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.modules.subscriptions.models import Plan, Subscription, SubscriptionStatus, UsageCounter

class SubscriptionRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def get_plan(
    self,
    plan_id: UUID,
  ) -> Plan | None:
    result = await self.session.execute(
      select(Plan).where(Plan.id == plan_id)
    )
    return result.scalar_one_or_none()

  async def get_plan_by_slug(
    self,
    slug: str,
  ) -> Plan | None:
    result = await self.session.execute(
      select(Plan).where(Plan.slug == slug)
    )
    return result.scalar_one_or_none()

  async def list_public_plans(self) -> list[Plan]:
    result = await self.session.execute(
      select(Plan)
      .where(
        Plan.is_active.is_(True),
        Plan.is_public.is_(True),
      )
      .order_by(
        Plan.price_monthly.asc(),
        Plan.name.asc(),
      )
    )
    return list(result.scalars().all())

  async def get_subscription(
    self,
    organization_id: UUID,
  ) -> Subscription | None:
    result = await self.session.execute(
      select(Subscription)
      .where(
        Subscription.organization_id == organization_id,
      )
      .options(
        selectinload(Subscription.plan),
      )
    )
    return result.scalar_one_or_none()

  async def get_subscription_for_update(
    self,
    organization_id: UUID,
  ) -> Subscription | None:
    result = await self.session.execute(
      select(Subscription)
      .where(
        Subscription.organization_id == organization_id,
      )
      .options(
        selectinload(Subscription.plan),
      )
      .with_for_update()
    )
    return result.scalar_one_or_none()

  async def create_subscription(
    self,
    subscription: Subscription,
  ) -> Subscription:
    self.session.add(subscription)
    await self.session.flush()
    return subscription

  async def update_subscription(
    self,
    subscription: Subscription,
  ) -> Subscription:
    self.session.add(subscription)
    await self.session.flush()
    return subscription

  async def get_usage_counter(
    self,
    organization_id: UUID,
    metric: str,
    period_start: datetime,
    period_end: datetime,
  ) -> UsageCounter | None:
    result = await self.session.execute(
      select(UsageCounter)
      .where(
        UsageCounter.organization_id == organization_id,
        UsageCounter.metric == metric,
        UsageCounter.period_start == period_start,
        UsageCounter.period_end == period_end,
      )
      .with_for_update()
    )
    return result.scalar_one_or_none()

  async def create_usage_counter(
    self,
    counter: UsageCounter,
  ) -> UsageCounter:
    self.session.add(counter)
    await self.session.flush()
    return counter

  async def list_usage_counters(
    self,
    organization_id: UUID,
    period_start: datetime,
    period_end: datetime,
  ) -> list[UsageCounter]:
    result = await self.session.execute(
      select(UsageCounter)
      .where(
        UsageCounter.organization_id == organization_id,
        UsageCounter.period_start == period_start,
        UsageCounter.period_end == period_end,
      )
      .order_by(UsageCounter.metric.asc())
    )
    return list(result.scalars().all())

  async def get_active_subscription_count(
    self,
    organization_id: UUID,
  ) -> int:
    result = await self.session.execute(
      select(func.count())
      .select_from(Subscription)
      .where(
        Subscription.organization_id == organization_id,
          Subscription.status.in_(
          [
            SubscriptionStatus.TRIALING,
            SubscriptionStatus.ACTIVE,
          ]
        ),
      )
    )
    return result.scalar_one()

  async def list_all_subscriptions(
    self,
    *,
    status: SubscriptionStatus | None = None,
    plan_id: UUID | None = None,
    limit: int = 20,
    offset: int = 0,
  ) -> tuple[list[Subscription], int]:
    query = select(Subscription).options(selectinload(Subscription.plan))
    count_query = select(func.count()).select_from(Subscription)

    if status is not None:
      query = query.where(Subscription.status == status)
      count_query = count_query.where(Subscription.status == status)
    if plan_id is not None:
      query = query.where(Subscription.plan_id == plan_id)
      count_query = count_query.where(Subscription.plan_id == plan_id)

    query = query.order_by(Subscription.created_at.desc()).limit(limit).offset(offset)
    items_result = await self.session.execute(query)
    total_result = await self.session.execute(count_query)

    return list(items_result.scalars().all()), total_result.scalar_one()