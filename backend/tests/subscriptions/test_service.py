from __future__ import annotations
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
import pytest
from app.core.exceptions import TraceException
from app.modules.subscriptions.models import BillingInterval, SubscriptionStatus
from app.modules.subscriptions.schemas import ChangePlanRequest
from app.modules.subscriptions.service import SubscriptionService

@pytest.mark.unit
class TestPeriodArithmetic:
  def test_add_months_simple(self):
    start = datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)
    result = SubscriptionService._add_months(start, 1)
    assert result == datetime(2025, 2, 15, 12, 0, tzinfo=timezone.utc)

  def test_add_months_clamps_end_of_month(self):
    start = datetime(2025, 1, 31, tzinfo=timezone.utc)
    result = SubscriptionService._add_months(start, 1)
    assert result.year == 2025 and result.month == 2 and result.day == 28

  def test_add_months_crosses_year(self):
    start = datetime(2025, 12, 10, tzinfo=timezone.utc)
    result = SubscriptionService._add_months(start, 1)
    assert result == datetime(2026, 1, 10, tzinfo=timezone.utc)

  def test_add_years_leap_day_to_non_leap(self):
    start = datetime(2024, 2, 29, tzinfo=timezone.utc)
    result = SubscriptionService._add_years(start, 1)
    assert result == datetime(2025, 2, 28, tzinfo=timezone.utc)

  def test_advance_period_monthly(self):
    start = datetime(2025, 3, 5, tzinfo=timezone.utc)
    end = SubscriptionService._advance_period(start, BillingInterval.MONTHLY)
    assert end == datetime(2025, 4, 5, tzinfo=timezone.utc)

  def test_advance_period_yearly(self):
    start = datetime(2025, 3, 5, tzinfo=timezone.utc)
    end = SubscriptionService._advance_period(start, BillingInterval.YEARLY)
    assert end == datetime(2026, 3, 5, tzinfo=timezone.utc)

@pytest.mark.integration
class TestCreateInitialSubscription:
  async def test_creates_active_free_subscription(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    seeded_free_plan,
  ):
    org = await make_organization()
    sub = await subscription_service.create_initial_subscription(org)

    assert sub.organization_id == org.id
    assert sub.plan_id == seeded_free_plan.id
    assert sub.status == SubscriptionStatus.ACTIVE
    assert sub.billing_interval == BillingInterval.MONTHLY
    assert sub.current_period_end > sub.current_period_start
    assert sub.provider == "manual"
    assert sub.cancel_at_period_end is False
    assert sub.cancelled_at is None

  async def test_is_idempotent(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
    seeded_free_plan,
  ):
    org = await make_organization()
    existing = await make_subscription(organization=org, plan=seeded_free_plan)
    again = await subscription_service.create_initial_subscription(org)
    assert again.id == existing.id

  async def test_missing_default_plan_raises_500(
    self,
    subscription_service: SubscriptionService,
    make_organization,
  ):
    org = await make_organization()
    with pytest.raises(TraceException) as exc_info:
      await subscription_service.create_initial_subscription(org)
    assert exc_info.value.status_code == 500
    assert exc_info.value.code == "DEFAULT_PLAN_NOT_FOUND"

@pytest.mark.integration
class TestChangePlan:
  async def test_happy_path_keeps_period_when_interval_unchanged(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
    make_plan,
    make_user,
    make_role,
  ):
    org = await make_organization()
    role = await make_role(organization=org)
    user = await make_user(organization=org, role=role)
    old_plan = await make_plan(slug="old")
    new_plan = await make_plan(slug="new", price_monthly=Decimal("4999"))
    sub = await make_subscription(organization=org, plan=old_plan)
    original_end = sub.current_period_end

    payload = ChangePlanRequest(plan_id=new_plan.id, billing_interval=BillingInterval.MONTHLY)
    updated = await subscription_service.change_plan(org.id, payload, user.id)

    assert updated.plan_id == new_plan.id
    assert updated.billing_interval == BillingInterval.MONTHLY
    assert updated.current_period_end == original_end

  async def test_interval_change_recalculates_period_end(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
    make_plan,
    make_user,
    make_role,
  ):
    org = await make_organization()
    role = await make_role(organization=org)
    user = await make_user(organization=org, role=role)
    plan = await make_plan()
    start = datetime(2025, 1, 10, tzinfo=timezone.utc)
    await make_subscription(
      organization=org,
      plan=plan,
      billing_interval=BillingInterval.MONTHLY,
      period_start=start,
      period_end=start + timedelta(days=30),
    )

    payload = ChangePlanRequest(plan_id=plan.id, billing_interval=BillingInterval.YEARLY)
    updated = await subscription_service.change_plan(org.id, payload, user.id)

    assert updated.billing_interval == BillingInterval.YEARLY
    expected = SubscriptionService._advance_period(start, BillingInterval.YEARLY)
    assert updated.current_period_end == expected

  async def test_rejects_inactive_plan(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
    make_plan,
    make_user,
    make_role,
  ):
    org = await make_organization()
    role = await make_role(organization=org)
    user = await make_user(organization=org, role=role)
    await make_subscription(organization=org)
    inactive = await make_plan(is_active=False)

    with pytest.raises(TraceException) as exc_info:
      await subscription_service.change_plan(
        org.id, ChangePlanRequest(plan_id=inactive.id), user.id
      )
    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "PLAN_NOT_AVAILABLE"

  async def test_rejects_cancelled_subscription(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
    make_plan,
    make_user,
    make_role,
  ):
    org = await make_organization()
    role = await make_role(organization=org)
    user = await make_user(organization=org, role=role)
    await make_subscription(organization=org, status=SubscriptionStatus.CANCELLED)
    new_plan = await make_plan()

    with pytest.raises(TraceException) as exc_info:
      await subscription_service.change_plan(
        org.id, ChangePlanRequest(plan_id=new_plan.id), user.id
      )
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "SUBSCRIPTION_NOT_CHANGEABLE"

  async def test_rejects_expired_subscription(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
    make_plan,
    make_user,
    make_role,
  ):
    org = await make_organization()
    role = await make_role(organization=org)
    user = await make_user(organization=org, role=role)
    await make_subscription(organization=org, status=SubscriptionStatus.EXPIRED)
    new_plan = await make_plan()

    with pytest.raises(TraceException) as exc_info:
      await subscription_service.change_plan(
        org.id, ChangePlanRequest(plan_id=new_plan.id), user.id
      )
    assert exc_info.value.code == "SUBSCRIPTION_NOT_CHANGEABLE"

@pytest.mark.integration
class TestCancelAndReactivate:
  async def test_cancel_at_period_end_keeps_active_status(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
    make_user,
    make_role,
  ):
    org = await make_organization()
    role = await make_role(organization=org)
    user = await make_user(organization=org, role=role)
    await make_subscription(organization=org)

    updated = await subscription_service.cancel_subscription(
      org.id, cancel_at_period_end=True, actor_user_id=user.id
    )
    assert updated.cancel_at_period_end is True
    assert updated.status == SubscriptionStatus.ACTIVE
    assert updated.cancelled_at is None

  async def test_cancel_immediately_sets_cancelled(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
    make_user,
    make_role,
  ):
    org = await make_organization()
    role = await make_role(organization=org)
    user = await make_user(organization=org, role=role)
    await make_subscription(organization=org)

    updated = await subscription_service.cancel_subscription(
      org.id, cancel_at_period_end=False, actor_user_id=user.id
    )
    assert updated.status == SubscriptionStatus.CANCELLED
    assert updated.cancelled_at is not None
    assert updated.cancel_at_period_end is False

  async def test_cancel_already_inactive_raises(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
    make_user,
    make_role,
  ):
    org = await make_organization()
    role = await make_role(organization=org)
    user = await make_user(organization=org, role=role)
    await make_subscription(organization=org, status=SubscriptionStatus.CANCELLED)

    with pytest.raises(TraceException) as exc_info:
      await subscription_service.cancel_subscription(
        org.id, cancel_at_period_end=True, actor_user_id=user.id
      )
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "SUBSCRIPTION_ALREADY_INACTIVE"

  async def test_reactivate_clears_flag(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
    make_user,
    make_role,
  ):
    org = await make_organization()
    role = await make_role(organization=org)
    user = await make_user(organization=org, role=role)
    await make_subscription(organization=org, cancel_at_period_end=True)

    updated = await subscription_service.reactivate_subscription(org.id, user.id)
    assert updated.cancel_at_period_end is False
    assert updated.status == SubscriptionStatus.ACTIVE

  async def test_reactivate_when_not_scheduled_raises(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
    make_user,
    make_role,
  ):
    org = await make_organization()
    role = await make_role(organization=org)
    user = await make_user(organization=org, role=role)
    await make_subscription(organization=org, cancel_at_period_end=False)

    with pytest.raises(TraceException) as exc_info:
      await subscription_service.reactivate_subscription(org.id, user.id)
    assert exc_info.value.code == "SUBSCRIPTION_NOT_SCHEDULED_FOR_CANCELLATION"

  async def test_reactivate_cancelled_subscription_raises(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
    make_user,
    make_role,
  ):
    org = await make_organization()
    role = await make_role(organization=org)
    user = await make_user(organization=org, role=role)
    await make_subscription(
      organization=org,
      status=SubscriptionStatus.CANCELLED,
      cancel_at_period_end=True,
    )

    with pytest.raises(TraceException) as exc_info:
      await subscription_service.reactivate_subscription(org.id, user.id)
    assert exc_info.value.code == "SUBSCRIPTION_NOT_REACTIVATABLE"

@pytest.mark.integration
class TestRollSubscription:
  async def test_advances_period_when_not_cancelling(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
  ):
    org = await make_organization()
    now = datetime.now(timezone.utc)
    past_end = now - timedelta(hours=1)
    await make_subscription(
      organization=org,
      period_start=past_end - timedelta(days=30),
      period_end=past_end,
      cancel_at_period_end=False,
    )

    rolled = await subscription_service.roll_subscription_if_expired(org.id, now)
    assert rolled is not None
    assert rolled.current_period_start == past_end
    assert rolled.current_period_end > past_end
    assert rolled.status == SubscriptionStatus.ACTIVE

  async def test_cancels_when_cancel_at_period_end_is_true(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
  ):
    org = await make_organization()
    now = datetime.now(timezone.utc)
    past_end = now - timedelta(hours=1)
    await make_subscription(
      organization=org,
      period_end=past_end,
      cancel_at_period_end=True,
    )

    rolled = await subscription_service.roll_subscription_if_expired(org.id, now)
    assert rolled is not None
    assert rolled.status == SubscriptionStatus.CANCELLED
    assert rolled.cancelled_at == now

  async def test_returns_none_when_period_still_active(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
  ):
    org = await make_organization()
    future = datetime.now(timezone.utc) + timedelta(days=10)
    await make_subscription(organization=org, period_end=future)

    result = await subscription_service.roll_subscription_if_expired(org.id)
    assert result is None

  async def test_returns_none_when_already_cancelled(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
  ):
    org = await make_organization()
    await make_subscription(
      organization=org,
      status=SubscriptionStatus.CANCELLED,
      period_end=datetime.now(timezone.utc) - timedelta(days=1),
    )

    result = await subscription_service.roll_subscription_if_expired(org.id)
    assert result is None

  async def test_trialing_becomes_active(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
  ):
    org = await make_organization()
    now = datetime.now(timezone.utc)
    past_end = now - timedelta(minutes=5)
    await make_subscription(
      organization=org,
      status=SubscriptionStatus.TRIALING,
      period_end=past_end,
      cancel_at_period_end=False,
    )

    rolled = await subscription_service.roll_subscription_if_expired(org.id, now)
    assert rolled is not None
    assert rolled.status == SubscriptionStatus.ACTIVE

@pytest.mark.integration
class TestUsageAndQuota:
  async def test_get_usage_returns_zero_when_no_counters(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
    make_plan,
  ):
    org = await make_organization()
    plan = await make_plan(quotas={"projects": 10, "ai_requests": 100})
    sub = await make_subscription(organization=org, plan=plan)

    usage = await subscription_service.get_usage(org.id)
    assert usage.period_start == sub.current_period_start
    assert usage.period_end == sub.current_period_end
    by_metric = {m.metric: m for m in usage.metrics}
    assert by_metric["projects"].used == 0
    assert by_metric["projects"].limit == 10
    assert by_metric["projects"].remaining == 10
    assert by_metric["projects"].percentage == 0.0

  async def test_check_quota_allows_under_limit(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
    make_plan,
  ):
    org = await make_organization()
    plan = await make_plan(quotas={"projects": 5})
    await make_subscription(organization=org, plan=plan)
    await subscription_service.check_quota(org.id, "projects", quantity=1)

  async def test_check_quota_blocks_when_limit_reached(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
    make_plan,
    make_usage_counter,
  ):
    org = await make_organization()
    plan = await make_plan(quotas={"projects": 2})
    sub = await make_subscription(organization=org, plan=plan)
    await make_usage_counter(
      organization=org,
      metric="projects",
      period_start=sub.current_period_start,
      period_end=sub.current_period_end,
      quantity=2,
    )

    with pytest.raises(TraceException) as exc_info:
      await subscription_service.check_quota(org.id, "projects", quantity=1)
    assert exc_info.value.status_code == 402
    assert exc_info.value.code == "USAGE_LIMIT_EXCEEDED"

  async def test_check_quota_inactive_subscription_raises_402(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
  ):
    org = await make_organization()
    await make_subscription(organization=org, status=SubscriptionStatus.CANCELLED)

    with pytest.raises(TraceException) as exc_info:
      await subscription_service.check_quota(org.id, "projects")
    assert exc_info.value.status_code == 402
    assert exc_info.value.code == "SUBSCRIPTION_INACTIVE"

  async def test_increment_usage_creates_and_enforces(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
    make_plan,
  ):
    org = await make_organization()
    plan = await make_plan(quotas={"ai_requests": 3})
    await make_subscription(organization=org, plan=plan)

    c1 = await subscription_service.increment_usage(org.id, "ai_requests", 2)
    assert c1.quantity == 2

    c2 = await subscription_service.increment_usage(org.id, "ai_requests", 1)
    assert c2.quantity == 3

    with pytest.raises(TraceException) as exc_info:
      await subscription_service.increment_usage(org.id, "ai_requests", 1)
    assert exc_info.value.code == "USAGE_LIMIT_EXCEEDED"

  async def test_increment_usage_many_is_atomic(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
    make_plan,
  ):
    org = await make_organization()
    plan = await make_plan(quotas={"projects": 2, "ai_requests": 10})
    await make_subscription(organization=org, plan=plan)

    await subscription_service.increment_usage_many(
      org.id, {"projects": 1, "ai_requests": 1}
    )

    with pytest.raises(TraceException) as exc_info:
      await subscription_service.increment_usage_many(
        org.id, {"projects": 2, "ai_requests": 5}
      )
    assert exc_info.value.code == "USAGE_LIMIT_EXCEEDED"

    usage = await subscription_service.get_usage(org.id)
    by_metric = {m.metric: m for m in usage.metrics}
    assert by_metric["projects"].used == 1
    assert by_metric["ai_requests"].used == 1

  async def test_decrement_never_goes_negative(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
    make_plan,
    make_usage_counter,
  ):
    org = await make_organization()
    plan = await make_plan(quotas={"projects": 10})
    sub = await make_subscription(organization=org, plan=plan)
    await make_usage_counter(
      organization=org,
      metric="projects",
      period_start=sub.current_period_start,
      period_end=sub.current_period_end,
      quantity=1,
    )

    result = await subscription_service.decrement_usage(org.id, "projects", amount=5)
    assert result is not None
    assert result.quantity == 0

  async def test_unknown_metric_is_unrestricted(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
    make_plan,
  ):
    org = await make_organization()
    plan = await make_plan(quotas={"projects": 1})
    await make_subscription(organization=org, plan=plan)

    await subscription_service.check_quota(org.id, "custom_metric", quantity=999)
    counter = await subscription_service.increment_usage(org.id, "custom_metric", 999)
    assert counter.quantity == 999

  async def test_get_subscription_not_found(
    self,
    subscription_service: SubscriptionService,
    make_organization,
  ):
    org = await make_organization()
    with pytest.raises(TraceException) as exc_info:
      await subscription_service.get_subscription(org.id)
    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "SUBSCRIPTION_NOT_FOUND"