from __future__ import annotations
import calendar
from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import TraceException
from app.modules.identity.models import Organization
from app.modules.subscriptions.models import BillingInterval, Subscription, SubscriptionStatus, UsageCounter, UsagePeriod
from app.modules.subscriptions.repository import SubscriptionRepository
from app.modules.subscriptions.schemas import ChangePlanRequest, UsageMetricResponse, UsageResponse
from app.modules.notifications.service import NotificationService
from app.modules.notifications.schemas import NotificationType
from app.modules.audit.models import AuditAction, AuditEntityType
from app.modules.audit.service import AuditLogService
import logging

logger = logging.getLogger("trace.subscriptions")

class SubscriptionService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repository = SubscriptionRepository(session)
    self.notifications = NotificationService(session)
    self.audit = AuditLogService(session)

  async def list_plans(self):
    return await self.repository.list_public_plans()

  async def get_subscription(
    self,
    organization_id: UUID,
  ) -> Subscription:
    print(f"DB lookup subscription for org: {organization_id}")
    subscription = await self.repository.get_subscription(
      organization_id
    )

    if subscription is None:
      raise TraceException(
        "Subscription not found.",
        status_code=404,
        code="SUBSCRIPTION_NOT_FOUND",
      )

    return subscription

  async def get_subscription_summary(
    self,
    organization_id: UUID,
  ):
    print(f"Loading subscription for org: {organization_id}")
    subscription = await self.get_subscription(
      organization_id
    )

    return subscription

  async def create_initial_subscription(
    self,
    organization: Organization,
    plan_slug: str = "free",
  ) -> Subscription:
    existing = await self.repository.get_subscription(
      organization.id
    )

    if existing is not None:
      return existing

    plan = await self.repository.get_plan_by_slug(
      plan_slug
    )

    if plan is None:
      raise TraceException(
        "Default subscription plan not found.",
        status_code=500,
        code="DEFAULT_PLAN_NOT_FOUND",
      )

    now = datetime.now(timezone.utc)
    billing_interval = BillingInterval.MONTHLY

    period_end = self._advance_period(now, billing_interval)

    subscription = Subscription(
      id=uuid4(),
      organization_id=organization.id,
      plan_id=plan.id,
      status=SubscriptionStatus.ACTIVE,
      billing_interval=billing_interval,
      started_at=now,
      current_period_start=now,
      current_period_end=period_end,
      provider="manual",
    )

    try:
      subscription = await self.repository.create_subscription(
        subscription
      )
      await self.session.commit()
    except IntegrityError:
      await self.session.rollback()
      existing = await self.repository.get_subscription(organization.id)
      if existing is not None:
        return existing
      raise TraceException(
        "Unable to create initial subscription.",
        status_code=409,
        code="SUBSCRIPTION_CREATE_CONFLICT",
      )

    return subscription
  
  async def change_plan(
    self,
    organization_id: UUID,
    payload: ChangePlanRequest,
    actor_user_id: UUID,
  ) -> Subscription:
    subscription = await self.repository.get_subscription_for_update(
      organization_id
    )

    if subscription is None:
      raise TraceException(
        "Subscription not found.",
        status_code=404,
        code="SUBSCRIPTION_NOT_FOUND",
      )

    plan = await self.repository.get_plan(payload.plan_id)

    if plan is None or not plan.is_active:
      raise TraceException(
        "Plan not found or inactive.",
        status_code=404,
        code="PLAN_NOT_AVAILABLE",
      )

    if subscription.status in {
      SubscriptionStatus.CANCELLED,
      SubscriptionStatus.EXPIRED,
    }:
      raise TraceException(
        "Cancelled or expired subscriptions cannot be changed.",
        status_code=409,
        code="SUBSCRIPTION_NOT_CHANGEABLE",
      )

    old_plan_id = subscription.plan_id
    interval_changed = subscription.billing_interval != payload.billing_interval
    subscription.plan_id = plan.id
    subscription.billing_interval = payload.billing_interval

    if interval_changed:
      subscription.current_period_end = self._advance_period(
        subscription.current_period_start, payload.billing_interval,
      )

    await self.repository.update_subscription(
      subscription
    )
    await self.session.commit()
    await self.audit.log(
      organization_id,
      actor_user_id,
      AuditEntityType.SUBSCRIPTION,
      subscription.id,
      AuditAction.UPDATE,
      f"Changed subscription plan to {plan.name}",
      changes={
        "plan_id": {
          "old": str(old_plan_id),
          "new": str(plan.id),
        }
      },
    )

    logger.info(
      "subscription.plan_changed",
      extra={
        "organization_id": str(organization_id),
        "new_plan_id": str(plan.id),
        "billing_interval": payload.billing_interval.value,
      },
    )
    return subscription

  async def cancel_subscription(
    self,
    organization_id: UUID,
    cancel_at_period_end: bool,
  ) -> Subscription:
    subscription = await self.repository.get_subscription_for_update(
      organization_id
    )

    if subscription is None:
      raise TraceException(
        "Subscription not found.",
        status_code=404,
        code="SUBSCRIPTION_NOT_FOUND",
      )

    if subscription.status in {
      SubscriptionStatus.CANCELLED,
      SubscriptionStatus.EXPIRED,
    }:
      raise TraceException(
        "Subscription is already inactive.",
        status_code=409,
        code="SUBSCRIPTION_ALREADY_INACTIVE",
      )

    if cancel_at_period_end:
      subscription.cancel_at_period_end = True
    else:
      subscription.cancel_at_period_end = False
      subscription.cancelled_at = datetime.now(timezone.utc)
      subscription.status = SubscriptionStatus.CANCELLED

    await self.session.flush()
    await self.session.commit()

    logger.info(
      "subscription.cancelled",
      extra={"organization_id": str(organization_id), "immediate": not cancel_at_period_end},
    )

    return subscription

  async def roll_subscription_if_expired(
    self,
    organization_id: UUID,
    now: datetime | None = None,
  ) -> Subscription | None:
    now = now or datetime.now(timezone.utc)
    subscription = await self.repository.get_subscription_for_update(organization_id)

    if subscription is None:
      return None
    if subscription.status in {SubscriptionStatus.CANCELLED, SubscriptionStatus.EXPIRED}:
      return None
    if subscription.current_period_end > now:
      return None

    if subscription.cancel_at_period_end:
      subscription.status = SubscriptionStatus.CANCELLED
      subscription.cancelled_at = now
    else:
      subscription.current_period_start = subscription.current_period_end
      subscription.current_period_end = self._advance_period(
        subscription.current_period_start, subscription.billing_interval,
      )
      if subscription.status == SubscriptionStatus.TRIALING:
        subscription.status = SubscriptionStatus.ACTIVE

    await self.repository.update_subscription(subscription)
    await self.session.commit()

    logger.info(
      "subscription.period_rolled",
      extra={"organization_id": str(organization_id), "new_status": subscription.status.value},
    )

    return subscription

  async def apply_provider_event(
    self,
    organization_id: UUID,
    *,
    status: SubscriptionStatus,
    provider_subscription_id: str | None = None,
    provider_customer_id: str | None = None,
  ) -> Subscription:
    subscription = await self.repository.get_subscription_for_update(organization_id)

    if subscription is None:
      raise TraceException("Subscription not found.", status_code=404, code="SUBSCRIPTION_NOT_FOUND")

    subscription.status = status
    if provider_subscription_id is not None:
      subscription.provider_subscription_id = provider_subscription_id
    if provider_customer_id is not None:
      subscription.provider_customer_id = provider_customer_id

    await self.repository.update_subscription(subscription)
    await self.session.commit()

    logger.info(
      "subscription.provider_event_applied",
      extra={"organization_id": str(organization_id), "status": status.value},
    )

    return subscription

  async def get_usage(
    self,
    organization_id: UUID,
  ) -> UsageResponse:
    subscription = await self.get_subscription(
      organization_id
    )

    counters = await self.repository.list_usage_counters(
      organization_id,
      subscription.current_period_start,
      subscription.current_period_end,
    )

    quotas = subscription.plan.quotas or {}

    metrics: list[UsageMetricResponse] = []

    for metric, limit in quotas.items():
      counter = next(
        (
          item
          for item in counters
          if item.metric == metric
        ),
        None,
      )

      used = counter.quantity if counter else 0

      if limit is None:
        remaining = None
        percentage = None
      else:
        remaining = max(int(limit) - used, 0)

        percentage = (
          100.0
          if int(limit) <= 0 and used > 0
          else (
            (used / int(limit)) * 100
            if int(limit) > 0
            else 0.0
          )
        )

      metrics.append(
        UsageMetricResponse(
          metric=metric,
          used=used,
          limit=int(limit) if limit is not None else None,
          remaining=remaining,
          percentage=percentage,
        )
      )

    return UsageResponse(
      period_start=subscription.current_period_start,
      period_end=subscription.current_period_end,
      metrics=metrics,
    )

  async def check_quota(
    self,
    organization_id: UUID,
    metric: str,
    quantity: int = 1,
  ) -> None:
    if quantity <= 0:
      raise ValueError(
        "Quantity must be greater than zero."
      )

    subscription = await self.get_subscription(
      organization_id
    )

    if subscription.status not in {
      SubscriptionStatus.TRIALING,
      SubscriptionStatus.ACTIVE,
    }:
      raise TraceException(
        "Subscription does not allow this operation.",
        status_code=402,
        code="SUBSCRIPTION_INACTIVE",
      )

    quotas = subscription.plan.quotas or {}

    if metric not in quotas:
      return

    limit = quotas[metric]

    if limit is None:
      return

    counter = await self.repository.get_usage_counter(
      organization_id,
      metric,
      subscription.current_period_start,
      subscription.current_period_end,
    )

    current_quantity = (
      counter.quantity
      if counter is not None
      else 0
    )

    if current_quantity + quantity > int(limit):
      raise TraceException(
        f"Usage limit exceeded for '{metric}'.",
        status_code=402,
        code="USAGE_LIMIT_EXCEEDED",
      )

  async def increment_usage(
    self,
    organization_id: UUID,
    metric: str,
    quantity: int = 1,
  ) -> UsageCounter:
    if quantity <= 0:
      raise ValueError(
        "Quantity must be greater than zero."
      )

    subscription = await self.get_subscription(
      organization_id
    )

    if subscription.status not in {
      SubscriptionStatus.TRIALING,
      SubscriptionStatus.ACTIVE,
    }:
      raise TraceException(
        "Subscription does not allow usage.",
        status_code=402,
        code="SUBSCRIPTION_INACTIVE",
      )

    quotas = subscription.plan.quotas or {}
    limit = quotas.get(metric)

    counter = await self.repository.get_usage_counter(
      organization_id,
      metric,
      subscription.current_period_start,
      subscription.current_period_end,
    )

    if counter is None:
      counter = UsageCounter(
        id=uuid4(),
        organization_id=organization_id,
        metric=metric,
        period=UsagePeriod.MONTH,
        period_start=subscription.current_period_start,
        period_end=subscription.current_period_end,
        quantity=0,
      )

      counter = await self.repository.create_usage_counter(
        counter
      )

    if limit is not None:
      if counter.quantity + quantity > int(limit):
        await self.session.rollback()

        raise TraceException(
          f"Usage limit exceeded for '{metric}'.",
          status_code=402,
          code="USAGE_LIMIT_EXCEEDED",
        )

    previous_quantity = counter.quantity
    counter.quantity += quantity
    await self.session.flush()

    if limit is not None:
      previous_ratio = previous_quantity / int(limit)
      new_ratio = counter.quantity / int(limit)
      if previous_ratio < 0.8 <= new_ratio:
       await self.notifications.notify_by_permission(
        organization_id,
        "organization:manage",
        NotificationType.SUBSCRIPTION_USAGE_WARNING,
        f"{metric.replace('_', ' ').title()} usage is near your plan limit",
        body=f"{counter.quantity} of {limit} used this billing period.",
        link_path="/app/subscription",
        commit=False,
      )
    await self.session.commit()
    return counter

  @staticmethod
  def _advance_period(value: datetime, interval: BillingInterval) -> datetime:
    if interval == BillingInterval.YEARLY:
      return SubscriptionService._add_years(value, 1)
    return SubscriptionService._add_months(value, 1)

  @staticmethod
  def _add_months(value: datetime, months: int) -> datetime:
    total = value.month - 1 + months
    year = value.year + total // 12
    month = total % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)

  @staticmethod
  def _add_years(value: datetime, years: int) -> datetime:
    year = value.year + years
    day = value.day
    if value.month == 2 and value.day == 29 and not calendar.isleap(year):
      day = 28
    return value.replace(year=year, day=day)