from __future__ import annotations
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update
from app.modules.drawings_boq.models import CalculationRun, RunStageLog, StagedQuantitySolid, QuantityLedger, RunDependencyEdge, RunElementState
from uuid import uuid4
from app.modules.drawings_boq.recalculation import calc_maintenance, calc_cache
from app.core.config import settings
import pytest
from app.core.exceptions import TraceException
from app.modules.drawings_boq.recalculation.calc_insight import CalcInsightService, run_budgets
from app.modules.drawings_boq.calc_repository import CalculationRunRepository

def _ago(**kw):
  return datetime.now(timezone.utc) - timedelta(**kw)

async def _make_stale(db, run, *, status="RUNNING", attempts=0, heartbeat_ago=3600, created_ago=None):
  vals = {"status": status, "attempts": attempts, "heartbeat_at": _ago(seconds=heartbeat_ago),
    "started_at": _ago(seconds=heartbeat_ago), "completed_at": None}
  if status == "QUEUED":
    vals.update(heartbeat_at=None, started_at=None, updated_at=_ago(seconds=created_ago or 7200))
  await db.execute(update(CalculationRun).where(CalculationRun.id == run.id).values(**vals))
  await db.flush()

async def _reload(db, run_id):
  db.expire_all()
  return await db.get(CalculationRun, run_id)

async def test_dead_worker_run_is_requeued_with_a_new_attempt(db_session, organization, project_factory, make_run):
  run = await make_run(organization, await project_factory(), [("CONC-COL", "1", "m3", "G1")])
  await _make_stale(db_session, run, status="RUNNING", attempts=0)
  db_session.add(RunStageLog(id=uuid4(), organization_id=organization.id, run_id=run.id, stage="build_solids",
    status="RUNNING", attempt=1, started_at=_ago(hours=1), counts={}))
  await db_session.flush()
  sent = []
  report = await calc_maintenance.recover_stale_runs(db_session, send=sent.append)
  assert report["requeued"] == 1 and report["failed"] == 0
  assert sent == [run.id]
  row = await _reload(db_session, run.id)
  assert row.status == "QUEUED" and row.attempts == 1 and row.started_at is None
  assert (await db_session.execute(select(RunStageLog).where(RunStageLog.run_id == run.id))).first() is None

async def test_run_out_of_attempts_fails_with_run_stale(db_session, organization, project_factory, make_run, monkeypatch):
  monkeypatch.setattr(settings, "calc_max_attempts", 3)
  run = await make_run(organization, await project_factory(), [("CONC-COL", "1", "m3", "G1")])
  await _make_stale(db_session, run, status="RUNNING", attempts=2)
  sent = []
  report = await calc_maintenance.recover_stale_runs(db_session, send=sent.append)
  assert report["failed"] == 1 and not sent
  row = await _reload(db_session, run.id)
  assert row.status == "FAILED" and row.error_code == "RUN_STALE"

async def test_healthy_run_is_left_alone(db_session, organization, project_factory, make_run):
  run = await make_run(organization, await project_factory(), [("CONC-COL", "1", "m3", "G1")])
  await _make_stale(db_session, run, status="RUNNING", heartbeat_ago=10)
  sent = []
  report = await calc_maintenance.recover_stale_runs(db_session, send=sent.append)
  assert report["checked"] == 0 and not sent
  assert (await _reload(db_session, run.id)).status == "RUNNING"

async def test_lost_queue_message_is_resent_then_fails(db_session, organization, project_factory, make_run, monkeypatch):
  monkeypatch.setattr(settings, "calc_max_attempts", 2)
  run = await make_run(organization, await project_factory(), [("CONC-COL", "1", "m3", "G1")])
  await _make_stale(db_session, run, status="QUEUED", attempts=0)
  sent = []
  report = await calc_maintenance.recover_stale_runs(db_session, send=sent.append)
  assert report["resent"] == 1 and sent == [run.id]
  assert (await _reload(db_session, run.id)).attempts == 1
  await db_session.execute(update(CalculationRun).where(CalculationRun.id == run.id).values(updated_at=_ago(hours=3)))
  report = await calc_maintenance.recover_stale_runs(db_session, send=sent.append)
  assert report["failed"] == 1
  row = await _reload(db_session, run.id)
  assert row.status == "FAILED" and row.error_code == "RUN_ENQUEUE_LOST"

async def test_recovery_sees_every_company(db_session, organization, other_organization, project_factory, project_b,
  make_run):
  a = await make_run(organization, await project_factory(), [("CONC-COL", "1", "m3", "G1")])
  b = await make_run(other_organization, project_b, [("CONC-COL", "1", "m3", "G1")])
  await _make_stale(db_session, a)
  await _make_stale(db_session, b)
  sent = []
  await calc_maintenance.recover_stale_runs(db_session, send=sent.append)
  assert set(sent) == {a.id, b.id}

async def test_staging_purge_removes_only_old_leftovers(db_session, organization, project_factory, make_run, monkeypatch):
  monkeypatch.setattr(settings, "calc_staging_retention_days", 7)
  run = await make_run(organization, await project_factory(), [("CONC-COL", "1", "m3", "G1")])
  for tag, age in (("old", 10), ("new", 1)):
    db_session.add(StagedQuantitySolid(id=uuid4(), organization_id=organization.id, run_id=run.id, element_id=None,
      geometry_kind="EXTRUDED_PROFILE", engine_version="t", stage="build_solids", created_at=_ago(days=age)))
  await db_session.flush()
  out = await calc_maintenance.purge_staging(db_session)
  assert out["solids"] == 1
  left = (await db_session.execute(select(StagedQuantitySolid).where(StagedQuantitySolid.run_id == run.id))).scalars().all()
  assert len(left) == 1

async def test_run_metrics_report_stage_timings_and_budgets(db_session, organization, project_a, make_run):
  oid = organization.id
  run = await make_run(organization, project_a, [("CONC-COL", "5", "m3", "G1")])
  rid = run.id
  db_session.add(RunStageLog(id=uuid4(), organization_id=oid, run_id=rid, stage="allocate",
    status="SUCCEEDED", attempt=1, started_at=_ago(minutes=5), finished_at=_ago(minutes=4), counts={}, duration_ms=2800,
    peak_rss_mb=410))
  await db_session.execute(update(CalculationRun).where(CalculationRun.id == rid).values(
    mode="INCREMENTAL", started_at=_ago(seconds=200), completed_at=_ago(seconds=170),
    metrics={"timings_ms": {"total": 31000, "allocate": 2800}, "counts": {"elements": 18708, "warnings": 4},
      "allocation": {"mode": "INCREMENTAL", "recompute": 25}, "peak_rss_mb": 525, "verify": {"matched": True}}))
  await db_session.flush()
  db_session.expire_all()
  out = await CalcInsightService(db_session).run_metrics(oid, rid)
  assert out["mode"] == "INCREMENTAL" and out["duration_ms"] == 31000
  assert out["stages"][0]["stage"] == "allocate" and out["stages"][0]["peak_rss_mb"] == 410
  budgets = {b["name"]: b for b in out["budgets"]}
  assert budgets["calculation_time"]["ok"] is True and budgets["calculation_time"]["limit"] == 300
  assert budgets["peak_memory"]["ok"] is True and budgets["peak_memory"]["actual"] == 525
  assert out["verify"] == {"matched": True}

def test_budget_flags_a_slow_or_heavy_run():
  bad = {b["name"]: b for b in run_budgets(None, {"peak_rss_mb": 99999}, 400_000)}
  assert bad["calculation_time"]["ok"] is False and bad["peak_memory"]["ok"] is False
  unknown = {b["name"]: b for b in run_budgets(None, {}, None)}
  assert unknown["calculation_time"]["ok"] is None and unknown["peak_memory"]["ok"] is None

async def test_metrics_of_another_company_are_not_found(db_session, organization, other_organization, project_a, make_run):
  run = await make_run(organization, project_a, [("CONC-COL", "5", "m3", "G1")])
  with pytest.raises(TraceException) as exc:
    await CalcInsightService(db_session).run_metrics(other_organization.id, run.id)
  assert exc.value.status_code == 404 and exc.value.code == "RUN_NOT_FOUND"

async def test_org_metrics_aggregate_modes_failures_and_percentiles(db_session, organization, project_factory, make_run,
  counter_redis, monkeypatch):
    
  monkeypatch.setattr("app.modules.drawings_boq.recalculation.calc_limits.CalcLimits._client", lambda self: counter_redis)
  oid = organization.id
  specs = [("COMPLETED", "FULL", None, 20), ("COMPLETED", "INCREMENTAL", None, 10), ("COMPLETED", "INCREMENTAL", None, 30),
    ("FAILED", "FULL", "RUN_STALE", None)]
  for i, (status, mode, code, secs) in enumerate(specs):
    run = await make_run(organization, await project_factory(), [("CONC-COL", "1", "m3", f"M{i}")])
    rid = run.id
    vals = {"status": status, "mode": mode, "error_code": code,
      "metrics": {"counts": {"elements": 100, "warnings": 1}, "peak_rss_mb": 200}}
    
    if secs:
      vals.update(started_at=_ago(seconds=secs + 5), completed_at=_ago(seconds=5))
    await db_session.execute(update(CalculationRun).where(CalculationRun.id == rid).values(**vals))
  await db_session.flush()
  db_session.expire_all()
  out = await CalcInsightService(db_session).org_metrics(oid, 30)
  assert out["runs_total"] == 4 and out["runs_by_status"] == {"COMPLETED": 3, "FAILED": 1}
  assert out["runs_by_mode"] == {"FULL": 1, "INCREMENTAL": 2}
  assert out["failure_codes"] == {"RUN_STALE": 1}
  assert out["elements_processed"] == 300 and out["warnings_total"] == 3
  assert out["incremental_share"] == pytest.approx(2 / 3, abs=1e-3)
  assert out["duration_seconds"]["p50"] == pytest.approx(20, abs=0.5) and out["duration_seconds"]["max"] == pytest.approx(30, abs=0.5)
  assert out["slowest_runs"][0]["duration_seconds"] == pytest.approx(30, abs=0.5)

async def _with_state(db, org, run):
  oid, rid = org.id, run.id
  ledger = (await db.execute(select(QuantityLedger).where(QuantityLedger.run_id == rid)
    .order_by(QuantityLedger.work_item_code))).scalars().all()
  els = [r.element_id for r in ledger]
  snapshot = [(r.work_item_code, r.solid_id, r.id) for r in ledger]
  for i, ((code, sid, lid), el) in enumerate(zip(snapshot, els)):
    db.add(RunElementState(id=uuid4(), organization_id=oid, run_id=rid, element_key=f"g:K{i}", element_id=el,
      solid_id=sid, alloc_hash="h" * 64, participating=True, warnings=[], owned_mm3=1.0))
  await db.flush()
  db.add(RunDependencyEdge(id=uuid4(), organization_id=oid, run_id=rid, key_a="g:K0", key_b="g:K1",
    element_a_id=els[0], element_b_id=els[1], overlap_mm3=250_000.0))
  await db.execute(update(CalculationRun).where(CalculationRun.id == rid).values(state_available=True))
  await db.flush()
  db.expire(run)
  return snapshot, els

async def test_impact_lists_touching_elements_and_the_ledger_rows_they_feed(db_session, organization, project_a, make_run):
  oid, rid = organization.id, None
  run = await make_run(organization, project_a, [("CONC-COL", "5", "m3", "G1"), ("CONC-SLAB", "9", "m3", "G2"),
    ("BRICK", "3", "m3", "G3")])
  rid = run.id
  ledger, els = await _with_state(db_session, organization, run)
  out = await CalcInsightService(db_session).impact(oid, rid, els[0])
  assert [t["element_id"] for t in out["touching"]] == [els[1]]
  assert out["touching"][0]["overlap_mm3"] == 250_000.0
  codes = {r["work_item_code"] for r in out["affected_ledger"]}
  assert codes == {ledger[0][0], ledger[1][0]}
  other = await CalcInsightService(db_session).impact(oid, rid, els[2])
  assert other["touching"] == []

async def test_impact_guards(db_session, organization, other_organization, project_a, make_run):
  oid, rid = organization.id, None
  ooid = other_organization.id
  run = await make_run(organization, project_a, [("CONC-COL", "5", "m3", "G1"), ("CONC-SLAB", "9", "m3", "G2")])
  rid = run.id
  ledger, els = await _with_state(db_session, organization, run)
  svc = CalcInsightService(db_session)
  
  with pytest.raises(TraceException) as exc:
    await svc.impact(oid, rid, uuid4())
  assert exc.value.code == "ELEMENT_NOT_IN_RUN" and exc.value.status_code == 404
  with pytest.raises(TraceException) as exc:
    await svc.impact(ooid, rid, els[0])
  assert exc.value.code == "RUN_NOT_FOUND"
  await db_session.execute(update(CalculationRun).where(CalculationRun.id == rid).values(state_available=False))
  db_session.expire_all()
  
  with pytest.raises(TraceException) as exc:
    await svc.impact(oid, rid, els[0])
  assert exc.value.code == "RUN_STATE_UNAVAILABLE" and exc.value.status_code == 409
  await db_session.execute(update(CalculationRun).where(CalculationRun.id == rid).values(state_available=True, status="RUNNING"))
  db_session.expire_all()
  with pytest.raises(TraceException) as exc:
    await svc.impact(oid, rid, els[0])
  assert exc.value.code == "RUN_NOT_COMPLETED"

async def test_state_pruning_keeps_only_the_newest_runs(db_session, organization, project_a, make_run):
  oid, pid = organization.id, project_a.id
  runs = []
  for i in range(3):
    r = await make_run(organization, project_a, [("CONC-COL", "5", "m3", f"P{i}"), ("CONC-SLAB", "9", "m3", f"Q{i}")])
    await db_session.execute(update(CalculationRun).where(CalculationRun.id == r.id).values(
      status="SUPERSEDED" if i < 2 else "COMPLETED", completed_at=_ago(hours=10 - i)))
    rid_i = r.id
    await _with_state(db_session, organization, r)
    runs.append(rid_i)
  repo = CalculationRunRepository(db_session)
  
  assert await repo.prune_state(oid, pid, keep=2) == 1
  flags = dict((await db_session.execute(
    select(CalculationRun.id, CalculationRun.state_available).where(CalculationRun.id.in_(runs)))).all())
  assert flags[runs[0]] is False and flags[runs[2]] is True
  left = (await db_session.execute(select(RunElementState).where(RunElementState.run_id == runs[0]))).first()
  assert left is None

def test_only_final_runs_are_cacheable():
  assert calc_cache.cacheable("COMPLETED") and calc_cache.cacheable("FAILED") and calc_cache.cacheable("SUPERSEDED")
  assert not calc_cache.cacheable("RUNNING") and not calc_cache.cacheable("QUEUED") and not calc_cache.cacheable("STAGED")

async def test_cache_round_trip_is_scoped_by_company_and_run(counter_redis):
  cache = calc_cache.RunReadCache(counter_redis)
  org_a, org_b, run = uuid4(), uuid4(), uuid4()
  await cache.put(org_a, run, "ledger", {"limit": 5}, {"rows": [1], "next": None})
  assert await cache.get(org_a, run, "ledger", {"limit": 5}) == {"rows": [1], "next": None}
  assert await cache.get(org_a, run, "ledger", {"limit": 6}) is None
  assert await cache.get(org_b, run, "ledger", {"limit": 5}) is None
  assert await cache.drop_run(org_a, run) == 1
  assert await cache.get(org_a, run, "ledger", {"limit": 5}) is None

async def test_cache_failure_never_breaks_a_read():
  class Down:
    async def get(self, *a, **k): raise ConnectionError()
    async def set(self, *a, **k): raise ConnectionError()
  cache = calc_cache.RunReadCache(Down())
  assert await cache.get(uuid4(), uuid4(), "x", {}) is None
  await cache.put(uuid4(), uuid4(), "x", {}, {"rows": []})