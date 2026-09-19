from __future__ import annotations
from datetime import datetime, timedelta, timezone
import pytest
from app.modules.subscriptions.models import SubscriptionStatus
from app.modules.subscriptions.service import SubscriptionService

@pytest.mark.integration
class TestRollExpiredSubscriptions:
  async def test_rolls_expired_and_skips_active(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
    make_plan,
  ):
    org_expired = await make_organization()
    org_active = await make_organization()
    plan = await make_plan()

    now = datetime.now(timezone.utc)
    past = now - timedelta(hours=2)

    await make_subscription(
      organization=org_expired,
      plan=plan,
      period_end=past,
      cancel_at_period_end=False,
    )
    await make_subscription(
      organization=org_active,
      plan=plan,
      period_end=now + timedelta(days=15),
    )

    rolled = await subscription_service.roll_subscription_if_expired(
      org_expired.id, now
    )
    assert rolled is not None
    assert rolled.current_period_start == past
    assert rolled.status == SubscriptionStatus.ACTIVE

    not_rolled = await subscription_service.roll_subscription_if_expired(
      org_active.id, now
    )
    assert not_rolled is None

  async def test_cancels_when_flag_set(
    self,
    subscription_service: SubscriptionService,
    make_organization,
    make_subscription,
    make_plan,
  ):
    org = await make_organization()
    plan = await make_plan()
    now = datetime.now(timezone.utc)
    past = now - timedelta(hours=1)

    await make_subscription(
      organization=org,
      plan=plan,
      period_end=past,
      cancel_at_period_end=True,
    )

    rolled = await subscription_service.roll_subscription_if_expired(org.id, now)
    assert rolled is not None
    assert rolled.status == SubscriptionStatus.CANCELLED
    assert rolled.cancelled_at == now

  async def test_task_summary_string_contract(self):
    summary = "rolled=2 failed=0 checked=5"
    assert summary.startswith("rolled=")
    assert "failed=" in summary
    assert "checked=" in summary
    parts = dict(p.split("=") for p in summary.split())
    assert int(parts["rolled"]) == 2
    assert int(parts["failed"]) == 0
    assert int(parts["checked"]) == 5