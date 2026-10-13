from __future__ import annotations
import asyncio
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4, uuid5
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.exceptions import TraceException
from app.engine.measure import engine as kernel
from app.engine.measure import derived as derived_module
from app.engine.measure.fingerprint import compute_fingerprint
from app.engine.measure.models import CalculationContext, MappingInput, ModelElement
from app.modules.drawings_boq.calc_repository import CalculationRunRepository
from app.modules.drawings_boq.measurement_params import MeasurementParametersService
from app.modules.drawings_boq.models import CalculationRun, DrawingElement, DrawingFormat, DrawingStatus, MeasurementConvention
from app.modules.drawings_boq.repository import DrawingElementRepository, DrawingRepository, MeasurementRuleSetRepository
from app.modules.drawings_boq.standards.service import StandardsService
from app.modules.projects.repository import ProjectRepository
from app.modules.drawings_boq.service import DrawingBOQService
from app.core.config import settings
from app.engine.measure import finishes as fin
from app.modules.drawings_boq.spatial_repository import load_reinforcements_inputs
from app.engine.measure import rebar as rb
from app.engine.measure import takeoff as tk
from app.modules.drawings_boq.takeoff.repository import takeoff_drawing_ids
from datetime import timedelta, timezone, datetime
import json
import random
import time
from app.dependencies.tenancy import scope_session_to_org, scope_session_as_platform_admin
from app.engine.measure.incremental import AllocationPlanner, alloc_signature, equivalent
from app.engine.measure.spatial import BaselineMismatch
from app.modules.drawings_boq.recalculation.calc_limits import CalcLimits
from app.modules.drawings_boq.recalculation import calc_obs
from app.modules.drawings_boq.recalculation import calc_cache as read_cache
from app.modules.drawings_boq.boq_service import BOQEngineService
from app.modules.drawings_boq.schemas import DeductionResponse
from app.modules.drawings_boq.schemas import LedgerRowResponse
from app.modules.drawings_boq.schemas import BarMarkResponse
from app.modules.drawings_boq.schemas import QuantitySolidResponse
from app.modules.drawings_boq.run_scope import SCOPE_KEY, build_scope_snapshot
from app.modules.drawings_boq.ledger_keys import ids_for_keys, ledger_id, restage_plan
from app.modules.drawings_boq.scope_check import OVERLAP_KEY, find_scope_overlaps, overlap_message

STALE_RUN_SECONDS = 2100           
_SNAPSHOT_KEYS = ("rule_set", "rule_profile_snapshot", SCOPE_KEY, OVERLAP_KEY)

def _rule_snapshot(rule_set, profile) -> dict:
  return {
    "rule_set": {"id": str(rule_set.id), "code": rule_set.code, "version": rule_set.immutable_version,
      "content_hash": rule_set.content_hash},
    "rule_profile_snapshot": json.loads(json.dumps(profile.to_dict(), default=str)),
  }

class RunError(Exception):
  def __init__(self, code: str, message: str):
    super().__init__(message)
    self.code = code

def _bbox(e: DrawingElement, which: str):
  vals = (getattr(e, f"bbox_{which}_x_mm"), getattr(e, f"bbox_{which}_y_mm"), getattr(e, f"bbox_{which}_z_mm"))
  return vals if all(v is not None for v in vals) else None

def _to_model_element(e: DrawingElement) -> ModelElement:
  return ModelElement(
    id=e.id, ifc_type=e.ifc_type, role=e.structural_role or "UNKNOWN", level_id=e.level_id,
    geometry_kind=e.geometry_kind, profile=e.profile, placement=e.placement, volume_mm3=e.volume_mm3,
    bbox_min_mm=_bbox(e, "min"), bbox_max_mm=_bbox(e, "max"),
    classification_confidence=e.classification_confidence if e.classification_confidence is not None else Decimal("0"),
    normalization_status=e.normalization_status, ifc_global_id=e.ifc_global_id,
  )

def _solid_row(run: CalculationRun, s, stage: str = "build_solids") -> dict:
  return {
    "id": s.id, "organization_id": run.organization_id, "run_id": run.id,
    "element_id": s.element_id, "level_id": s.level_id, "role": s.role,
    "component_type": s.component_type, "geometry_kind": s.geometry_kind, "material_grade": s.material_grade,
    "gross_volume_m3": s.gross_volume_m3, "gross_area_m2": s.gross_area_m2, "gross_length_m": s.gross_length_m,
    "count": s.count, "status": s.status, "issues": list(s.issues),
    "engine_version": run.engine_version, "stage": stage,
  }

def _ledger_row(run: CalculationRun, e, stage: str = "measure") -> dict:
  return {
    "id": ledger_id(run.id, e),
    "organization_id": run.organization_id, "run_id": run.id, "solid_id": e.solid_id,
    "element_id": e.element_id, "level_id": e.level_id, "work_item_code": e.work_item_code,
    "quantity_net": e.quantity, "unit": e.unit, "material_grade": e.material_grade,
    "source_kind": getattr(e, "source_kind", "MODEL"), "confidence": e.confidence, "formula_code": e.formula_code,
     "trace": e.trace, "warnings": list(e.warnings),
    "spec_key": getattr(e, "spec_key", None), "spec": getattr(e, "spec", None),
    "work_stage": getattr(e, "work_stage", None),
    "engine_version": run.engine_version, "stage": stage,
  }

def _deduction_row(run: CalculationRun, d, ctx: CalculationContext, stage: str = "allocate") -> dict:
  return {
    "id": uuid5(run.id, f"deduction|{d.from_solid_id}|{d.to_solid_id}|{d.deduction_type}|"
      f"{d.geometry.get('opening_element_id', '')}"),
    "organization_id": run.organization_id, "run_id": run.id,
    "from_solid_id": d.from_solid_id, "to_solid_id": d.to_solid_id,
    "deduction_type": d.deduction_type, "quantity": d.quantity, "unit": d.unit,
    "rule_code": d.rule_code, "rule_version": str(ctx.rule_set_version),
    "geometry": d.geometry, "explanation": d.explanation,
    "engine_version": run.engine_version, "stage": stage,
  }
  
def _bar_mark_row(run: CalculationRun, m, stage: str = "reinforcement") -> dict:
  return {
    "id": uuid5(run.id, f"mark|{m.solid_id}|{m.mark}"), "organization_id": run.organization_id, "run_id": run.id,
    "solid_id": m.solid_id, "element_id": m.element_id, "level_id": m.level_id, "mark": m.mark, "role": m.role,
    "shape_code": m.shape_code, "shape_params": m.shape_params, "designation": m.designation, "dia_mm": m.dia_mm,
    "grade": m.grade, "count": m.count, "spacing_mm": m.spacing_mm, "cut_len_mm": m.cut_len_mm,
    "stock_len_mm": m.stock_len_mm, "pieces": m.pieces, "lap_count": m.lap_count, "lap_len_mm": m.lap_len_mm,
    "total_len_m": m.total_len_m, "unit_weight_kg_m": m.unit_weight_kg_m, "total_kg": m.total_kg,
    "provenance": m.provenance, "confidence": m.confidence, "review_status": m.review_status,
    "schedule_row_id": m.schedule_row_id, "trace": m.trace, "warnings": list(m.warnings),
    "engine_version": run.engine_version, "stage": stage,
  }
  
def engine_v2_enabled(org_id) -> bool:
  ids = {s.strip() for s in (settings.engine_v2_org_ids or "").split(",") if s.strip()}
  return "*" in ids or str(org_id) in ids

def engine_spec_enabled(org_id) -> bool:
  ids = {s.strip() for s in (settings.engine_spec_org_ids or "").split(",") if s.strip()}
  return "*" in ids or str(org_id) in ids

def engine_stage_enabled(org_id) -> bool:
  ids = {s.strip() for s in (settings.engine_stage_org_ids or "").split(",") if s.strip()}
  return "*" in ids or str(org_id) in ids

def engine_layer_enabled(org_id) -> bool:
  ids = {s.strip() for s in (settings.engine_layer_org_ids or "").split(",") if s.strip()}
  return "*" in ids or str(org_id) in ids

def engine_derived_enabled(org_id) -> bool:
  ids = {s.strip() for s in (settings.engine_derived_org_ids or "").split(",") if s.strip()}
  return "*" in ids or str(org_id) in ids

def clean_derived_params(raw: dict | None) -> dict:
  out: dict = {}
  for name in (*derived_module.PARAMS, derived_module.NGL_PARAM):
    value = (raw or {}).get(name)
    if value is None or isinstance(value, bool):
      continue
    try:
      out[name] = float(value)
    except (TypeError, ValueError):
      continue
  return out

class CalculationService:
  def __init__(self, session: AsyncSession, heartbeat_factory=None):
    self.session = session
    self.runs = CalculationRunRepository(session)
    self.drawings = DrawingRepository(session)
    self.elements = DrawingElementRepository(session)
    self.rule_sets = MeasurementRuleSetRepository(session)
    self.standards = StandardsService(session)
    self.projects = ProjectRepository(session)
    self._heartbeat_factory = heartbeat_factory

  async def _load_inputs(self, organization_id: UUID, drawing_ids: list[UUID], rule_set_id: UUID, project_id: UUID):
    profile = await self.standards.profile_for_rule_set(rule_set_id)
    mappings = tuple(sorted(
      (MappingInput(ifc_type=m.ifc_type, work_item_code=m.work_item_code,
        confidence_base=Decimal(str(m.confidence_base))) for m in profile.mappings),
      key=lambda m: m.ifc_type,
    ))
    elements: list[ModelElement] = []
    for drawing_id in sorted(drawing_ids, key=str):
      async for element in self.runs.stream_model_elements(drawing_id, organization_id):
        elements.append(element)
    reinforcements = await load_reinforcements_inputs(self.session, organization_id, project_id, sorted(drawing_ids, key=str))
    return profile, mappings, elements, reinforcements

  async def _convention_params(self, code: str | None) -> dict:
    if not code:
      return {}
    row = (await self.session.execute(
      select(MeasurementConvention).where(
        MeasurementConvention.code == code, MeasurementConvention.is_active.is_(True))
    )).scalar_one_or_none()
    return dict(row.parameters or {}) if row is not None else {}

  @staticmethod
  def _fingerprint(elements, mappings, profile, rule_set, settings: dict,
    convention_code: str | None, convention_params: dict, reinforcements=None) -> str:
    return compute_fingerprint(
      elements=elements, mappings=mappings, profile_fingerprint=profile.fingerprint(),
      rule_set_ref=f"{rule_set.id}:{rule_set.immutable_version}:{rule_set.content_hash}",
      convention_code=convention_code, engine_version=kernel.ENGINE_VERSION,
      settings=settings, convention_params=convention_params,
      spatial={**fin.finish_sched_payload(reinforcements.spaces, reinforcements.openings, reinforcements.schedule_lines), "rebar": rb.rebar_payload(reinforcements.rebar),
        "takeoff": tk.takeoff_payload(reinforcements.takeoff)} if reinforcements else None,
    )

  async def request_run(self, organization_id: UUID, project_id: UUID, user_id: UUID,
    drawing_ids: list[UUID] | None, rule_set_code: str | None, convention_code: str | None = None,
    force_full: bool = False, verify: bool = False, enqueue: bool = True, confirm_overlap: bool = False,
    derived_params: dict | None = None):

    project = await self.projects.get_by_id_and_org(project_id, organization_id)
    if project is None:
      raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")

    drawings = await self.drawings.list_by_project(organization_id, project_id)
    eligible = [d for d in drawings
    if d.format == DrawingFormat.IFC and d.status == DrawingStatus.PARSED and d.is_current_revision]
    takeoff_ids = await takeoff_drawing_ids(self.session, organization_id, project_id)
    takeoff_drawings = [d for d in drawings if d.format == DrawingFormat.PDF and d.id in takeoff_ids and d.is_current_revision]
    
    if drawing_ids:
      wanted = set(drawing_ids)
      chosen = [d for d in (*eligible, *takeoff_drawings) if d.id in wanted]
      if len(chosen) != len(wanted):
        raise TraceException("One or more drawings are not current, parsed IFC drawings, or current PDFs with confirmed takeoff, in this project.",
          status_code=422, code="DRAWING_NOT_ELIGIBLE")
    elif len(eligible) <= 1:
      chosen = [*eligible, *takeoff_drawings]
      
    else:
      names = ", ".join(sorted(d.original_filename for d in eligible)[:6])
      raise TraceException(
        f"This project has {len(eligible)} current IFC drawings ({names}). Choose the drawing or drawings to calculate. "
        "A run only measures what you select.",
        status_code=422, code="DRAWING_SELECTION_REQUIRED")
    if not chosen:
      raise TraceException("This project has no parsed IFC drawing and no confirmed PDF takeoff measurements to calculate.",
        status_code=422, code="NO_PARSED_DRAWINGS")

    scope_overlaps: list[dict] = []
    ifc_chosen = [d for d in chosen if d.format == DrawingFormat.IFC]
    if len(ifc_chosen) > 1:
      scope_overlaps = await self._scope_overlaps(organization_id, ifc_chosen)
      if scope_overlaps and not confirm_overlap:
        raise TraceException(overlap_message(scope_overlaps), status_code=422, code="DRAWINGS_OVERLAP")

    rule_set = await DrawingBOQService(self.session).get_active_rule_set(organization_id, rule_set_code)
    if convention_code and kernel.get_convention(convention_code) is None:
      raise TraceException(f"Unknown measurement convention '{convention_code}'.", status_code=422, code="UNKNOWN_CONVENTION")
    if convention_code and rule_set.convention_code and convention_code != rule_set.convention_code:
      raise TraceException("The measurement convention is chosen by the rule set. Clone the rule set to use another convention.",
        status_code=422, code="CONVENTION_OVERRIDE_NOT_ALLOWED")
      
    effective_convention = rule_set.convention_code or convention_code
    ids = sorted((d.id for d in chosen), key=str)
    settings = {"scope": "building", "preferred_rule_code": rule_set_code, "project_id": str(project_id)}
    if engine_spec_enabled(organization_id):
      settings["spec"] = True
      if engine_stage_enabled(organization_id):
        settings["stages"] = True
      if engine_layer_enabled(organization_id):
        settings["layers"] = True
    if engine_derived_enabled(organization_id):
      settings["derived"] = True
      stored_params = await MeasurementParametersService(self.session).stored_for_run(organization_id, project_id)
      cleaned = clean_derived_params({**stored_params, **(derived_params or {})})
      if cleaned:
        settings["derived_params"] = cleaned
    profile, mappings, elements, reinforcements = await self._load_inputs(organization_id, ids, rule_set.id, project_id)
    convention_params = await self._convention_params(effective_convention)
    fingerprint = self._fingerprint(elements, mappings, profile, rule_set, settings, effective_convention,
      convention_params, reinforcements)

    if not (force_full or verify):
      existing = await self.runs.get_completed_by_fingerprint(organization_id, fingerprint)
      if existing is not None:
        return existing, True

    await self.runs.fail_stale(project_id, datetime.now(timezone.utc) - timedelta(seconds=STALE_RUN_SECONDS))
    limits = CalcLimits(self.session)
    await limits.ensure_can_create(organization_id)
    run = CalculationRun(
      id=uuid4(), organization_id=organization_id, project_id=project_id, requested_by_user_id=user_id,
      rule_set_id=rule_set.id, convention_code=effective_convention, drawing_revision_ids=ids,
      engine_version=kernel.ENGINE_VERSION, fingerprint=fingerprint, status="QUEUED",
      progress_pct=0,
      settings={**settings, **_rule_snapshot(rule_set, profile), SCOPE_KEY: build_scope_snapshot(chosen), OVERLAP_KEY: scope_overlaps},
      force_full=bool(force_full), verify=bool(verify), attempts=0,
    )
    try:
      await self.runs.create(run)
      await self.session.commit()
    except IntegrityError:
      await self.session.rollback()
      active = await self.runs.get_active_for_project(organization_id, project_id)
      if active is not None:
        raise TraceException(f"A calculation run is already in progress for this project (run {active.id}).",
          status_code=409, code="RUN_IN_PROGRESS")
      existing = await self.runs.get_completed_by_fingerprint(organization_id, fingerprint)
      if existing is not None:
        return existing, True
      raise

    try:
      if enqueue:
        from app.modules.drawings_boq.calc_tasks import calculate_run_task
        calculate_run_task.apply_async(args=[str(run.id)], queue="calc_engine")
    except Exception:
      await self.runs.mark_failed(run.id, "ENQUEUE_FAILED", "Could not enqueue the calculation task.")
      await self.session.commit()
      raise TraceException("Calculation queue is unavailable. Try again shortly.",
        status_code=503, code="RUN_ENQUEUE_FAILED")
    await limits.record_run(organization_id)
    calc_obs.log_event("run_requested", run_id=run.id, organization_id=organization_id, engine_version=run.engine_version,
      project_id=str(project_id), elements=len(elements), force_full=bool(force_full), verify=bool(verify))
    return run, False

  async def _scope_overlaps(self, organization_id: UUID, drawings) -> list[dict]:
    shared, counts = await self.runs.shared_global_ids(organization_id, [d.id for d in drawings])
    return find_scope_overlaps(
      {(str(a), str(b)): n for (a, b), n in shared.items()}, {str(k): v for k, v in counts.items()},
      {str(d.id): d.original_filename for d in drawings})

  async def _stage(self, run: CalculationRun, name: str, work, progress: int) -> dict:
    if not await self.runs.touch_heartbeat(run.id, self._attempt):
      raise RunError("RUN_ATTEMPT_SUPERSEDED", "Another attempt took over this run.")
    await self.runs.start_stage(run, name)
    await self.session.commit()
    started = time.perf_counter()
    counts = await work()
    duration_ms = int((time.perf_counter() - started) * 1000)
    rss = calc_obs.rss_mb()
    await self.runs.finish_stage(run.id, name, counts, duration_ms, rss)
    await self.runs.set_progress(run.id, progress)
    await self.session.commit()
    self._timings[name] = duration_ms
    calc_obs.log_event("stage_finished", run_id=run.id, organization_id=run.organization_id,
      engine_version=run.engine_version, stage=name, duration_ms=duration_ms, peak_rss_mb=rss,
      **{k: v for k, v in counts.items() if isinstance(v, (int, float, str)) and not isinstance(v, bool)})
    return counts

  async def _skip(self, run: CalculationRun, *names: str, reason: str = "skipped in this run") -> None:
    for name in names:
      await self.runs.log_skipped(run, name, reason)
    await self.session.commit()

  async def _heartbeat_loop(self, run_id: UUID, attempt: int, stop: asyncio.Event) -> None:
    interval = max(int(settings.calc_heartbeat_seconds), 1)
    factory = self._heartbeat_factory
    if factory is None:
      from app.core.database import WorkerSessionLocal
      factory = WorkerSessionLocal
    while not stop.is_set():
      try:
        await asyncio.wait_for(stop.wait(), timeout=interval)
        break
      except asyncio.TimeoutError:
        pass
      try:
        async with factory() as session:
          await scope_session_as_platform_admin(session)
          alive = await CalculationRunRepository(session).touch_heartbeat(run_id, attempt)
          await session.commit()
        if not alive:
          self._superseded = True
      except Exception:
        calc_obs.logger.warning("heartbeat write failed for run %s", run_id, exc_info=True)

  async def execute_run(self, run_id: UUID) -> None:
    run = await self.runs.claim_queued(run_id)
    if run is None:
      return
    await self.session.commit()

    await scope_session_to_org(self.session, run.organization_id)
    org = run.organization_id
    project_id = run.project_id
    rule_set_id = run.rule_set_id
    drawing_ids = list(run.drawing_revision_ids)
    run_settings = {k: v for k, v in (run.settings or {}).items() if k not in _SNAPSHOT_KEYS}
    expected_fingerprint = run.fingerprint
    engine_version = run.engine_version
    convention_code = run.convention_code
    requested_by = run.requested_by_user_id
    self._attempt = run.attempts
    self._timings: dict = {}
    self._superseded = False
    self._rss_start = calc_obs.current_rss_mb()
    force_full = bool(run.force_full)
    verify = bool(run.verify) or (random.random() < float(settings.calc_verify_sample_rate))
    run_started = time.perf_counter()
    stop_heartbeat = asyncio.Event()
    heartbeat = None
    if self._heartbeat_factory is not False:
      heartbeat = asyncio.create_task(self._heartbeat_loop(run_id, self._attempt, stop_heartbeat))
    calc_obs.log_event("run_started", run_id=run_id, organization_id=org, engine_version=engine_version,
      attempt=self._attempt, force_full=force_full, verify=verify)

    metrics: dict = {"timings_ms": self._timings}
    planner = None
    try:
      rule_set = await self.rule_sets.get_by_id(rule_set_id)
      if rule_set is None:
        raise RunError("RULE_SET_NOT_FOUND", "Rule set no longer exists.")
      with calc_obs.timed() as t_load:
        profile, mappings, elements, p6 = await self._load_inputs(org, drawing_ids, rule_set.id, project_id)
        convention_params = await self._convention_params(convention_code)
        matches = self._fingerprint(elements, mappings, profile, rule_set, run_settings,
          convention_code, convention_params, p6) == expected_fingerprint
      self._timings["load_inputs"] = t_load.ms
      if not matches:
        raise RunError("INPUT_CHANGED", "Drawings or rules changed after the run was requested. Request a new run.")

      ctx = CalculationContext(
        run_id=run_id, engine_version=engine_version, fingerprint=expected_fingerprint,
        convention_code=convention_code, rule_set_code=rule_set.code,
        rule_set_version=rule_set.immutable_version, mappings=mappings,
        convention_params=convention_params, openings=p6.openings, spaces=p6.spaces,
        schedule_lines=p6.schedule_lines, rebar=p6.rebar, takeoff=p6.takeoff,
        spec_mode=bool(run_settings.get("spec")), stage_mode=bool(run_settings.get("stages")),
        layer_mode=bool(run_settings.get("layers")), derived_mode=bool(run_settings.get("derived")),
        derived_params=dict(run_settings.get("derived_params") or {}),
      )
      state: dict = {"extra_solids": [], "extra_ledger": [], "finish_skipped": {}, "marks": [], "rebar_stats": {}, "rebar_skipped": {}}
      convention = kernel.get_convention(convention_code)
      state["alloc"] = kernel.AllocationResult.empty()
      signature = alloc_signature(engine_version, convention_code, convention_params)
      use_incremental = convention is not None and bool(settings.calc_incremental_enabled) and not force_full

      async def validate():
        state["accepted"], state["rejected"] = await asyncio.to_thread(kernel.validate_input, ctx, elements)
        return {"elements_in": len(elements), "accepted": len(state["accepted"]), "rejected": len(state["rejected"])}

      async def build():
        solids, skipped = await asyncio.to_thread(kernel.build_solids, ctx, state["accepted"])
        state["solids"], state["skipped"] = solids, skipped
        await self.runs.clear_staged(run_id)
        await self.runs.stage_solids([_solid_row(run, s, "build_solids") for s in solids])
        return {"solids": len(solids), "review_required": sum(1 for s in solids if s.status == "REVIEW_REQUIRED"),
          "skipped_by_role": skipped}

      def make_planner(baseline):
        concrete_solids, concrete_elements = kernel.split_steel(state["solids"], state["accepted"])
        return AllocationPlanner(ctx, convention, concrete_solids, concrete_elements, baseline,
          float(settings.calc_incremental_max_change_ratio))

      async def spatial():
        baseline = None
        if use_incremental:
          with calc_obs.timed() as t_base:
            base_run = await self.runs.find_baseline_run(org, project_id, signature, run_id)
            baseline = await self.runs.load_baseline(base_run) if base_run is not None else None
          self._timings["load_baseline"] = t_base.ms
          state["baseline_run_id"] = base_run.id if base_run is not None else None
        planner = make_planner(baseline)
        await asyncio.to_thread(planner.spatial)
        if not use_incremental:
          planner.fallback_reason = "FORCED_FULL" if force_full else "INCREMENTAL_DISABLED"
        state["planner"] = planner
        index = planner.index
        return {"participating": len(index.prisms), "candidate_pairs": len(index.candidates),
          "unallocated": len(index.unallocated), "mode": planner.mode,
          **({"fallback_reason": planner.fallback_reason} if planner.fallback_reason else {})}

      def full_replan(reason: str, upto: str):
        fresh = make_planner(None)
        fresh.fallback_reason = reason
        fresh.spatial()
        if upto in ("relations", "allocate"):
          fresh.relations()
        return fresh

      def relations_work():
        pl = state["planner"]
        try:
          return pl, pl.relations()
        except BaselineMismatch:
          pl = full_replan("BASELINE_INCONSISTENT", "relations")
          return pl, pl.overlaps

      async def relations():
        pl, overlaps = await asyncio.to_thread(relations_work)
        state["planner"], state["overlaps"] = pl, overlaps
        return {"overlaps": len(overlaps), "mode": pl.mode}

      def allocate_work():
        pl = state["planner"]
        try:
          return pl, pl.allocate()
        except BaselineMismatch:
          pl = full_replan("BASELINE_INCONSISTENT", "allocate")
          return pl, pl.allocate()

      async def allocate():
        pl, alloc = await asyncio.to_thread(allocate_work)
        verify_result = None
        if verify and pl.mode == "INCREMENTAL":
          def check_against_full():
            full = make_planner(None)
            full.spatial()
            full.relations()
            return full, full.allocate()
          full_pl, full_alloc = await asyncio.to_thread(check_against_full)
          problems = equivalent(full_alloc, alloc)
          verify_result = {"checked": True, "matched": not problems, "problems": problems}
          if problems:
            calc_obs.log_event("incremental_mismatch", run_id=run_id, organization_id=org,
              engine_version=engine_version, level=40, problems=problems)
            pl, alloc = full_pl, full_alloc
            pl.fallback_reason = "VERIFY_MISMATCH"
        state["planner"], state["alloc"] = pl, alloc
        state["verify"] = verify_result
        await self.runs.stage_deductions([_deduction_row(run, d, ctx, "allocate") for d in alloc.deductions])
        return {"deductions": len(alloc.deductions), "mode": pl.mode, **alloc.stats,
          **({"verify": verify_result} if verify_result else {}), **({"reuse": pl.reuse_stats} if pl.reuse_stats else {})}

      async def openings():
        res = await asyncio.to_thread(fin.apply_openings, ctx, profile, state["solids"], p6.openings)
        state["alloc"] = fin.merge_openings(state["alloc"], res)
        await self.runs.stage_deductions([_deduction_row(run, d, ctx, "openings") for d in res.deductions])
        return res.stats

      async def measure():
        ledger, unmapped = await asyncio.to_thread(kernel.measure, ctx, state["solids"], state["alloc"])
        state["ledger"], state["unmapped"] = ledger, unmapped
        state["wall_material"] = kernel.wall_material_stats(state["solids"], ledger)
        state["steel"] = kernel.steel_stats(state["solids"], ledger, state["rejected"])
        await self.runs.stage_ledger([_ledger_row(run, e, "measure") for e in ledger])
        return {"ledger_rows": len(ledger), "unmapped_by_type": unmapped, "wall_material": state["wall_material"],
          "steel": state["steel"]}

      async def finishes():
        res = await asyncio.to_thread(fin.measure_finishes, ctx, profile, p6.spaces, p6.openings)
        await self.runs.stage_solids([_solid_row(run, s, "finishes") for s in res.solids])
        await self.runs.stage_ledger([_ledger_row(run, e, "finishes") for e in res.ledger])
        state["extra_solids"] += res.solids
        state["extra_ledger"] += res.ledger
        state["finish_skipped"] = res.skipped
        return {"spaces": len(p6.spaces), "finish_lines": len(res.ledger), "skipped": res.skipped}

      async def schedules():
        model_codes = frozenset(e.work_item_code for e in state["ledger"] + state["extra_ledger"])
        res = await asyncio.to_thread(fin.schedule_lines_ledger, ctx, p6.schedule_lines, model_codes)
        await self.runs.stage_solids([_solid_row(run, s, "schedules") for s in res.solids])
        await self.runs.stage_ledger([_ledger_row(run, e, "schedules") for e in res.ledger])
        state["extra_solids"] += res.solids
        state["extra_ledger"] += res.ledger
        return {"schedule_lines": len(res.ledger)}

      async def reinforcement():
        res = await asyncio.to_thread(rb.measure_rebar, ctx, profile, state["solids"], state["ledger"], p6.rebar)
        await self.runs.stage_solids([_solid_row(run, s, "reinforcement") for s in res.solids])
        await self.runs.stage_ledger([_ledger_row(run, e, "reinforcement") for e in res.ledger])
        await self.runs.stage_bar_marks([_bar_mark_row(run, m) for m in res.marks])
        state["extra_solids"] += res.solids
        state["extra_ledger"] += res.ledger
        state["marks"], state["rebar_stats"], state["rebar_skipped"] = res.marks, res.stats, res.skipped
        return {**res.stats, "skipped": res.skipped}
      
      async def pdf_takeoff():
        res = await asyncio.to_thread(tk.measure_takeoff, ctx, profile, p6.takeoff, state["ledger"] + state["extra_ledger"])
        if res.dropped_keys:
          gone_ids = ids_for_keys(run_id, state["ledger"] + state["extra_ledger"], res.dropped_keys)
          state["ledger"] = tk.apply_replacements(state["ledger"], res.dropped_keys)
          state["extra_ledger"] = tk.apply_replacements(state["extra_ledger"], res.dropped_keys)
          live = {e.solid_id for e in state["ledger"] + state["extra_ledger"]}
          gone = {sid for sid, _ in res.dropped_keys if sid not in live}
          synthetic_gone = [s.id for s in state["extra_solids"] if s.id in gone]
          await self.runs.drop_staged_ledger(run_id, gone_ids, synthetic_gone)
          state["extra_solids"] = [s for s in state["extra_solids"] if s.id not in set(synthetic_gone)]
        await self.runs.stage_solids([_solid_row(run, s, "pdf_takeoff") for s in res.solids])
        await self.runs.stage_ledger([_ledger_row(run, e, "pdf_takeoff") for e in res.ledger])
        state["extra_solids"] += res.solids
        state["extra_ledger"] += res.ledger
        state["takeoff_stats"], state["takeoff_results"] = res.stats, res.results
        return {"measurements": res.stats.get("measurements", 0), "counted": res.stats.get("counted", 0),
          "verified": res.stats.get("verified", 0), "skipped": res.stats.get("skipped", {}),
          "replaced_work_items": len(res.stats.get("replaced", []))}
      async def layer_split():
        res = await asyncio.to_thread(kernel.split_layers, ctx, state["accepted"], state["solids"], state["ledger"])
        old_ids, added = restage_plan(run_id, state["ledger"], res)
        await self.runs.drop_staged_ledger(run_id, old_ids)
        await self.runs.stage_ledger([_ledger_row(run, e, "measure") for e in added])
        state["ledger"] = res.ledger
        state["layer_stats"] = res.stats
        return {"rows_split": res.stats.get("rows_split", 0), "rows_merged": res.stats.get("rows_merged", 0),
          "finish_excluded_m3": res.stats.get("finish_excluded_m3", "0"), "unpriced_m3": res.stats.get("unpriced_m3", "0")}

      async def derived_works():
        res = await asyncio.to_thread(kernel.measure_derived, ctx, profile, state["accepted"], state["solids"], state["ledger"])
        await self.runs.stage_solids([_solid_row(run, s, "derived") for s in res.solids])
        await self.runs.stage_ledger([_ledger_row(run, e, "derived") for e in res.ledger])
        state["extra_solids"] += res.solids
        state["extra_ledger"] += res.ledger
        state["derived_stats"] = res.stats
        return {"rows": len(res.ledger), "foundations": res.stats.get("foundations", 0),
          "excavation_m3": res.stats.get("excavation_m3", "0"), "pcc_m3": res.stats.get("pcc_m3", "0"),
          "backfill_m3": res.stats.get("backfill_m3", "0"), **({"reason": res.stats["reason"]} if res.stats.get("reason") else {})}

      async def stage_split():
        res = await asyncio.to_thread(kernel.split_stages, ctx, state["accepted"], state["solids"], state["alloc"], state["ledger"])
        old_ids, added = restage_plan(run_id, state["ledger"], res)
        await self.runs.drop_staged_ledger(run_id, old_ids)
        await self.runs.stage_ledger([_ledger_row(run, e, "measure") for e in added])
        state["ledger"] = res.ledger
        state["stage_stats"] = res.stats
        return {"rows_split": res.stats.get("rows_split", 0), "rows_tagged": res.stats.get("rows_tagged", 0)}

      async def check():
        await asyncio.to_thread(kernel.self_check, state["solids"] + state["extra_solids"],
          state["ledger"] + state["extra_ledger"], state["alloc"])
        failures = rb.self_check_rebar(state["marks"], state["extra_ledger"])
        if failures:
          raise kernel.InvariantViolation(failures)
        return {"invariants": "passed"}

      await self._stage(run, "validate_input", validate, 15)
      await self._stage(run, "build_solids", build, 30)
      if convention is not None:
        await self._stage(run, "spatial_index", spatial, 40)
        await self._stage(run, "find_relations", relations, 50)
        await self._stage(run, "allocate", allocate, 60)
        planner = state["planner"]
      else:
        await self._skip(run, "spatial_index", "find_relations", "allocate",
          reason="no registered measurement convention on this rule set")
      await self._stage(run, "openings", openings, 65)
      await self._stage(run, "measure", measure, 70)
      await self._stage(run, "finishes", finishes, 75)
      await self._stage(run, "schedules", schedules, 78)
      await self._skip(run, "recipes", reason="not implemented in this engine version")
      await self._stage(run, "reinforcement", reinforcement, 79)
      if p6.takeoff is not None and getattr(p6.takeoff, "measurements", None):
        await self._stage(run, "pdf_takeoff", pdf_takeoff, 79)
      else:
        await self._skip(run, "pdf_takeoff", reason="no confirmed PDF takeoff measurements in this run")
        
      if ctx.layer_mode and ctx.spec_mode:
        await self._stage(run, "layer_split", layer_split, 79)
      else:
        await self._skip(run, "layer_split", reason="layer splitting is not switched on for this company")

      if ctx.stage_mode:
        await self._stage(run, "stage_split", stage_split, 79)
      else:
        await self._skip(run, "stage_split", reason="work stages are not switched on for this company")

      if ctx.derived_mode:
        await self._stage(run, "derived_works", derived_works, 80)
      else:
        await self._skip(run, "derived_works", reason="derived works are not switched on for this company")
      
      await self._stage(run, "self_check", check, 80)

      if not await self.runs.touch_heartbeat(run_id, self._attempt):
        raise RunError("RUN_ATTEMPT_SUPERSEDED", "Another attempt took over this run.")
      await self.runs.set_progress(run_id, 90, status="STAGED")
      await self.session.commit()

      with calc_obs.timed() as t_promote:
        promoted = await self.runs.promote(run_id)
      with calc_obs.timed() as t_clear:
        await self.runs.clear_staged(run_id)
      with calc_obs.timed() as t_supersede:
        await self.runs.supersede_older_completed(org, project_id, run_id, drawing_ids)
      self._timings["promote"] = t_promote.ms
      self._timings["clear_staging"] = t_clear.ms
      self._timings["supersede"] = t_supersede.ms

      state_counts = {}
      if planner is not None:
        with calc_obs.timed() as t_state:
          state_elements, state_edges = await asyncio.to_thread(planner.state)
          await self.runs.persist_state(run, state_elements, state_edges)
        self._timings["persist_state"] = t_state.ms
        state_counts = {"elements": len(state_elements), "edges": len(state_edges)}

      warnings_total = sum(len(e.warnings) for e in state["ledger"] + state["extra_ledger"])
      rss = calc_obs.rss_mb()
      mode = planner.mode if planner is not None else "FULL"
      allocation_summary = planner.summary() if planner is not None else {"mode": "FULL"}
      metrics.update({
        "mode": mode, "allocation": allocation_summary,
        "counts": {"elements": len(elements), "accepted": len(state["accepted"]), "rejected": len(state["rejected"]),
          "solids": promoted["solids"], "ledger_rows": promoted["ledger_rows"], "deductions": promoted["deductions"],
          "bar_marks": promoted["bar_marks"], "warnings": warnings_total, "state": state_counts},
        "peak_rss_mb": rss, "rss_start_mb": self._rss_start, "memory_budget_mb": int(settings.calc_memory_budget_mb),
        "within_memory_budget": rss <= int(settings.calc_memory_budget_mb),
        "verify": state.get("verify"),
      })
      await self.runs.set_metrics(
        run_id, metrics, mode=mode, baseline_run_id=state.get("baseline_run_id") if mode == "INCREMENTAL" else None,
        alloc_signature=signature if planner is not None else None, state_available=planner is not None)
      await self.runs.record_takeoff_results(org, state.get("takeoff_results") or [], run_id)
      await self.runs.complete(run_id, {
        "promoted": promoted,
        "elements_in": len(elements),
        "rejected_sample": [
          {"element_id": str(r.element_id), "ifc_type": r.ifc_type, "code": r.code} for r in state["rejected"][:200]
        ],
        "rejected_total": len(state["rejected"]),
        "skipped_by_role": state["skipped"],
        "unmapped_by_type": state["unmapped"],
        "wall_material": state.get("wall_material", {}),
        "steel": state.get("steel", {}),
        "allocation": state["alloc"].stats,
        "finishes_skipped": state["finish_skipped"],
        "spaces": len(p6.spaces),
        "rebar": state["rebar_stats"],
        "pdf_takeoff": state.get("takeoff_stats", {}),
        "spec": kernel.spec_stats(ctx, state["ledger"] + state["extra_ledger"]),
        "stages": state.get("stage_stats") or kernel.stage_stats(ctx),
        "layers": state.get("layer_stats") or kernel.layer_stats(ctx),
        "derived": state.get("derived_stats") or kernel.derived_stats(ctx),
        "material": kernel.material_stats(state["solids"], state["ledger"]),
        "coverage": kernel.coverage_stats(elements, state["rejected"], state["skipped"], state["unmapped"], state["ledger"]),
        "confidence": kernel.confidence_stats(state["ledger"] + state["extra_ledger"]),
      })
      if planner is not None:
        await self.runs.prune_state(org, project_id, int(settings.calc_state_keep_runs))

      await self.session.commit()

      with calc_obs.timed() as t_boq:
        await self._build_boq_after_run(org, run_id, requested_by)
      self._timings["boq_build"] = t_boq.ms
      total_ms = int((time.perf_counter() - run_started) * 1000)
      self._timings["total"] = total_ms
      await self.runs.set_metrics(run_id, {"timings_ms": self._timings})
      await self.session.commit()
      calc_obs.log_event("run_completed", run_id=run_id, organization_id=org, engine_version=engine_version,
        mode=mode, duration_ms=total_ms, elements=len(elements), ledger_rows=promoted["ledger_rows"],
        warnings=warnings_total, peak_rss_mb=rss)

    except Exception as exc:
      await self.session.rollback()
      if isinstance(exc, RunError) and exc.code == "RUN_ATTEMPT_SUPERSEDED":
        calc_obs.log_event("run_attempt_superseded", run_id=run_id, organization_id=org, engine_version=engine_version,
          attempt=self._attempt, level=30)
        return
      if await self._superseded_by_other_attempt(run_id):
        return
      from celery.exceptions import SoftTimeLimitExceeded
      if isinstance(exc, RunError):
        code = exc.code
      elif isinstance(exc, kernel.InvariantViolation):
        code = "SELF_CHECK_FAILED"
      elif isinstance(exc, SoftTimeLimitExceeded):
        code = "RUN_TIME_LIMIT"
      else:
        code = "RUN_FAILED"
      failed_stage = next((n for n in ("validate_input", "build_solids", "spatial_index", "find_relations", "allocate",
        "openings", "measure", "finishes", "schedules", "reinforcement", "layer_split", "stage_split", "derived_works", "self_check") if n not in self._timings), None)
      await self.runs.fail_running_stages(run_id, str(exc))
      await self.runs.mark_failed(run_id, code, str(exc))
      await self.runs.clear_staged(run_id)
      await self.runs.set_metrics(run_id, {"timings_ms": self._timings, "failure": {
        "code": code, "stage": failed_stage, "message": str(exc)[:500]}, "peak_rss_mb": calc_obs.rss_mb()})
      await self.session.commit()
      calc_obs.log_event("run_failed", run_id=run_id, organization_id=org, engine_version=engine_version, level=40,
        failure_code=code, stage=failed_stage, message=str(exc)[:300])
    finally:
      stop_heartbeat.set()
      if heartbeat is not None:
        try:
          await heartbeat
        except Exception:
          pass

  async def _superseded_by_other_attempt(self, run_id: UUID) -> bool:
    row = await self.runs.get_attempt_state(run_id)
    return row is not None and (row[0] != self._attempt or row[1] not in ("RUNNING", "STAGED", "PROMOTED"))

  async def _build_boq_after_run(self, org: UUID, run_id: UUID, actor) -> None:
    try:
      result = await BOQEngineService(self.session).build_from_run(org, run_id, actor)
      await self.runs.merge_stats(run_id, {"boq": {k: str(v) for k, v in result.items()}})
    except Exception as exc:
      await self.session.rollback()
      await self.runs.merge_stats(run_id, {"boq_error": str(exc)[:500]})
    await self.session.commit()

  async def get_run(self, organization_id: UUID, run_id: UUID) -> CalculationRun:
    run = await self.runs.get_by_id_and_org(run_id, organization_id)
    if run is None:
      raise TraceException("Calculation run not found.", status_code=404, code="RUN_NOT_FOUND")
    return run

  async def list_stages(self, organization_id: UUID, run_id: UUID):
    await self.get_run(organization_id, run_id)
    return await self.runs.list_stages(run_id, organization_id)

  async def _page(self, name: str, schema, fetch, organization_id: UUID, run_id: UUID, kwargs: dict, cached: bool):
    run = await self.get_run(organization_id, run_id)
    limit = kwargs["limit"]
    params = {k: (str(v) if v is not None else None) for k, v in kwargs.items()}
    use_cache = cached and read_cache.cacheable(run.status)
    cache = read_cache.RunReadCache() if use_cache else None
    if cache is not None:
      hit = await cache.get(organization_id, run_id, name, params)
      if hit is not None:
        return hit["rows"], hit["next"]
    rows = await fetch(run_id, organization_id, **kwargs)
    page, next_cursor = rows[:limit], (rows[limit - 1].id if len(rows) > limit else None)
    if cache is None:
      return page, next_cursor
    dumped = [schema.model_validate(r).model_dump(mode="json") for r in page]
    nxt = str(next_cursor) if next_cursor else None
    await cache.put(organization_id, run_id, name, params, {"rows": dumped, "next": nxt})
    return dumped, nxt

  async def list_ledger(self, organization_id: UUID, run_id: UUID, cached: bool = False, **kwargs):
    return await self._page("ledger", LedgerRowResponse, self.runs.list_ledger, organization_id, run_id, kwargs, cached)

  async def list_bar_marks(self, organization_id: UUID, run_id: UUID, cached: bool = False, **kwargs):
    return await self._page("bar_marks", BarMarkResponse, self.runs.list_bar_marks, organization_id, run_id, kwargs, cached)

  async def list_solids(self, organization_id: UUID, run_id: UUID, cached: bool = False, **kwargs):
    return await self._page("solids", QuantitySolidResponse, self.runs.list_solids, organization_id, run_id, kwargs, cached)

  async def list_deductions(self, organization_id: UUID, run_id: UUID, cached: bool = False, **kwargs):
    return await self._page("deductions", DeductionResponse, self.runs.list_deductions, organization_id, run_id, kwargs, cached)