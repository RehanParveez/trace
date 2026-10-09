from __future__ import annotations
from sqlalchemy import update
from app.modules.drawings_boq.models import CalculationRun
from app.core.config import settings
from app.modules.drawings_boq.recalculation.calc_limits import CalcLimits, RETRYABLE_CODES, USAGE_METRIC
import pytest
from app.core.exceptions import TraceException

async def _set_status(db, run_id, status):
  await db.execute(update(CalculationRun).where(CalculationRun.id == run_id).values(status=status))
  await db.flush()

async def test_concurrent_cap_blocks_the_next_run_and_frees_when_one_finishes(
  db_session, organization, project_factory, make_run, counter_redis, monkeypatch):
  monkeypatch.setattr(settings, "calc_max_concurrent_runs_per_org", 2)
  monkeypatch.setattr(settings, "calc_run_rate_limit_per_minute", 0)
  monkeypatch.setattr(settings, "calc_run_rate_limit_per_hour", 0)
  runs = [await make_run(organization, await project_factory(), [("CONC-COL", "1", "m3", f"G{i}")]) for i in range(2)]
  limits = CalcLimits(db_session, counter_redis)
  await limits.ensure_can_create(organization.id)
  for r in runs:
    await _set_status(db_session, r.id, "RUNNING")
  with pytest.raises(TraceException) as exc:
    await limits.ensure_can_create(organization.id)
  assert exc.value.status_code == 429 and exc.value.code == "RUN_CONCURRENCY_LIMIT"
  await _set_status(db_session, runs[0].id, "COMPLETED")
  await limits.ensure_can_create(organization.id)

async def test_concurrent_cap_counts_only_this_company(
  db_session, organization, other_organization, project_a, project_b, make_run, counter_redis, monkeypatch):
  monkeypatch.setattr(settings, "calc_max_concurrent_runs_per_org", 1)
  monkeypatch.setattr(settings, "calc_run_rate_limit_per_minute", 0)
  monkeypatch.setattr(settings, "calc_run_rate_limit_per_hour", 0)
  busy = await make_run(organization, project_a, [("CONC-COL", "1", "m3", "G1")])
  await _set_status(db_session, busy.id, "QUEUED")
  await CalcLimits(db_session, counter_redis).ensure_can_create(other_organization.id)

async def test_rate_limit_per_minute(db_session, organization, counter_redis, monkeypatch):
  monkeypatch.setattr(settings, "calc_max_concurrent_runs_per_org", 0)
  monkeypatch.setattr(settings, "calc_run_rate_limit_per_minute", 2)
  monkeypatch.setattr(settings, "calc_run_rate_limit_per_hour", 0)
  limits = CalcLimits(db_session, counter_redis)
  await limits.ensure_can_create(organization.id)
  await limits.ensure_can_create(organization.id)
  with pytest.raises(TraceException) as exc:
    await limits.ensure_can_create(organization.id)
  assert exc.value.status_code == 429 and exc.value.code == "RUN_RATE_LIMITED"

async def test_rate_limit_is_per_company(db_session, organization, other_organization, counter_redis, monkeypatch):
  monkeypatch.setattr(settings, "calc_max_concurrent_runs_per_org", 0)
  monkeypatch.setattr(settings, "calc_run_rate_limit_per_minute", 1)
  monkeypatch.setattr(settings, "calc_run_rate_limit_per_hour", 0)
  limits = CalcLimits(db_session, counter_redis)
  await limits.ensure_can_create(organization.id)
  await limits.ensure_can_create(other_organization.id)
  with pytest.raises(TraceException):
    await limits.ensure_can_create(organization.id)

async def test_rate_limiter_failure_lets_the_run_through(db_session, organization, monkeypatch):
  monkeypatch.setattr(settings, "calc_max_concurrent_runs_per_org", 0)
  class Broken:
    async def eval(self, *a, **k):
      raise ConnectionError("redis down")
  await CalcLimits(db_session, Broken()).ensure_can_create(organization.id)

async def test_plan_quota_stops_runs_and_cached_runs_are_not_counted(
  db_session, organization, make_plan, make_subscription, counter_redis, monkeypatch):
  monkeypatch.setattr(settings, "calc_max_concurrent_runs_per_org", 0)
  monkeypatch.setattr(settings, "calc_run_rate_limit_per_minute", 0)
  monkeypatch.setattr(settings, "calc_run_rate_limit_per_hour", 0)
  plan = await make_plan(quotas={"projects": 5, "storage_bytes": 10**9, USAGE_METRIC: 2})
  
  await make_subscription(organization=organization, plan=plan)
  limits = CalcLimits(db_session, counter_redis)
  await limits.ensure_can_create(organization.id)
  await limits.record_run(organization.id)
  await limits.record_run(organization.id)
  with pytest.raises(TraceException) as exc:
    await limits.ensure_can_create(organization.id)
  assert exc.value.status_code == 402
  snap = await limits.snapshot(organization.id)
  assert snap["quota"]["used"] == 2 and snap["quota"]["limit"] == 2

async def test_organisation_without_subscription_is_not_blocked(db_session, organization, counter_redis, monkeypatch):
  monkeypatch.setattr(settings, "calc_max_concurrent_runs_per_org", 0)
  monkeypatch.setattr(settings, "calc_run_rate_limit_per_minute", 0)
  monkeypatch.setattr(settings, "calc_run_rate_limit_per_hour", 0)
  await CalcLimits(db_session, counter_redis).ensure_can_create(organization.id)

async def test_usage_snapshot_shows_cap_and_windows(db_session, organization, counter_redis, monkeypatch):
  monkeypatch.setattr(settings, "calc_max_concurrent_runs_per_org", 3)
  monkeypatch.setattr(settings, "calc_run_rate_limit_per_minute", 5)
  monkeypatch.setattr(settings, "calc_run_rate_limit_per_hour", 30)
  limits = CalcLimits(db_session, counter_redis)
  await limits.ensure_can_create(organization.id)
  snap = await limits.snapshot(organization.id)
  assert snap["concurrent"] == {"active": 0, "limit": 3}
  by_window = {w["window_seconds"]: w for w in snap["rate_limits"]}
  assert by_window[60]["used"] == 1 and by_window[60]["remaining"] == 4
  assert by_window[3600]["limit"] == 30

def test_retryable_codes_are_the_not_now_codes():
  assert RETRYABLE_CODES == {"RUN_IN_PROGRESS", "RUN_CONCURRENCY_LIMIT", "RUN_RATE_LIMITED"}