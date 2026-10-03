from __future__ import annotations
import asyncio
from decimal import Decimal
from uuid import UUID, uuid4, uuid5
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import TraceException
from app.engine.measure import engine as kernel
from app.engine.measure.fingerprint import compute_fingerprint
from app.engine.measure.models import CalculationContext, MappingInput, ModelElement
from app.modules.drawings_boq.calc_repository import CalculationRunRepository
from app.modules.drawings_boq.models import CalculationRun, DrawingElement, DrawingFormat, DrawingStatus
from app.modules.drawings_boq.repository import DrawingElementRepository, DrawingRepository, MeasurementRuleSetRepository
from app.modules.drawings_boq.standards.service import StandardsService
from app.modules.projects.repository import ProjectRepository
from app.modules.drawings_boq.service import DrawingBOQService

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
    normalization_status=e.normalization_status,
  )

def _solid_row(run: CalculationRun, s) -> dict:
  return {
    "id": s.id, "organization_id": run.organization_id, "run_id": run.id,
    "element_id": s.element_id, "level_id": s.level_id, "role": s.role,
    "component_type": s.component_type, "geometry_kind": s.geometry_kind, "material_grade": s.material_grade,
    "gross_volume_m3": s.gross_volume_m3, "gross_area_m2": s.gross_area_m2, "gross_length_m": s.gross_length_m,
    "count": s.count, "status": s.status, "issues": list(s.issues),
    "engine_version": run.engine_version, "stage": "build_solids",
  }

def _ledger_row(run: CalculationRun, e) -> dict:
  return {
    "id": uuid5(run.id, f"ledger|{e.solid_id}|{e.work_item_code}"),
    "organization_id": run.organization_id, "run_id": run.id, "solid_id": e.solid_id,
    "element_id": e.element_id, "level_id": e.level_id, "work_item_code": e.work_item_code,
    "quantity_net": e.quantity, "unit": e.unit, "material_grade": e.material_grade,
    "source_kind": "MODEL", "confidence": e.confidence, "formula_code": e.formula_code,
    "trace": e.trace, "warnings": list(e.warnings),
    "engine_version": run.engine_version, "stage": "measure",
  }

class CalculationService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.runs = CalculationRunRepository(session)
    self.drawings = DrawingRepository(session)
    self.elements = DrawingElementRepository(session)
    self.rule_sets = MeasurementRuleSetRepository(session)
    self.standards = StandardsService(session)
    self.projects = ProjectRepository(session)

  async def _load_inputs(self, organization_id: UUID, drawing_ids: list[UUID], rule_set_id: UUID):
    profile = await self.standards.profile_for_rule_set(rule_set_id)
    mappings = tuple(sorted(
      (MappingInput(ifc_type=m.ifc_type, work_item_code=m.work_item_code,
        confidence_base=Decimal(str(m.confidence_base))) for m in profile.mappings),
      key=lambda m: m.ifc_type,
    ))
    elements: list[ModelElement] = []
    for drawing_id in sorted(drawing_ids, key=str):
      rows = await self.elements.list_by_drawing(drawing_id, organization_id)
      elements.extend(_to_model_element(r) for r in rows)
    return profile, mappings, elements

  @staticmethod
  def _fingerprint(elements, mappings, profile, rule_set, settings: dict) -> str:
    return compute_fingerprint(
      elements=elements, mappings=mappings, profile_fingerprint=profile.fingerprint(),
      rule_set_ref=f"{rule_set.id}:{rule_set.immutable_version}:{rule_set.content_hash}",
      convention_code=rule_set.convention_code, engine_version=kernel.ENGINE_VERSION, settings=settings,
    )

  async def request_run(self, organization_id: UUID, project_id: UUID, user_id: UUID,
    drawing_ids: list[UUID] | None, rule_set_code: str | None):

    project = await self.projects.get_by_id_and_org(project_id, organization_id)
    if project is None:
      raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")

    drawings = await self.drawings.list_by_project(organization_id, project_id)
    eligible = [d for d in drawings
                
    if d.format == DrawingFormat.IFC and d.status == DrawingStatus.PARSED and d.is_current_revision]
    if drawing_ids:
      wanted = set(drawing_ids)
      chosen = [d for d in eligible if d.id in wanted]
      if len(chosen) != len(wanted):
        raise TraceException("One or more drawings are not current, parsed IFC drawings in this project.",
          status_code=422, code="DRAWING_NOT_ELIGIBLE")
    else:
      chosen = eligible
    if not chosen:
      raise TraceException("This project has no parsed IFC drawing to calculate.",
        status_code=422, code="NO_PARSED_DRAWINGS")

    rule_set = await DrawingBOQService(self.session).get_active_rule_set(organization_id, rule_set_code)
    ids = sorted((d.id for d in chosen), key=str)
    settings = {"scope": "building", "preferred_rule_code": rule_set_code}
    profile, mappings, elements = await self._load_inputs(organization_id, ids, rule_set.id)
    fingerprint = self._fingerprint(elements, mappings, profile, rule_set, settings)

    existing = await self.runs.get_completed_by_fingerprint(organization_id, fingerprint)
    if existing is not None:
      return existing, True

    run = CalculationRun(
      id=uuid4(), organization_id=organization_id, project_id=project_id, requested_by_user_id=user_id,
      rule_set_id=rule_set.id, convention_code=rule_set.convention_code, drawing_revision_ids=ids,
      engine_version=kernel.ENGINE_VERSION, fingerprint=fingerprint, status="QUEUED",
      progress_pct=0, settings=settings,
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
      from app.modules.drawings_boq.calc_tasks import calculate_run_task
      calculate_run_task.apply_async(args=[str(run.id)], queue="calc_engine")
    except Exception:
      await self.runs.mark_failed(run.id, "ENQUEUE_FAILED", "Could not enqueue the calculation task.")
      await self.session.commit()
      raise TraceException("Calculation queue is unavailable. Try again shortly.",
        status_code=503, code="RUN_ENQUEUE_FAILED")
    return run, False

  async def _stage(self, run: CalculationRun, name: str, work, progress: int) -> dict:
    await self.runs.start_stage(run, name)
    await self.session.commit()
    counts = await work()
    await self.runs.finish_stage(run.id, name, counts)
    await self.runs.set_progress(run.id, progress)
    await self.session.commit()
    return counts

  async def _skip(self, run: CalculationRun, *names: str) -> None:
    for name in names:
      await self.runs.log_skipped(run, name, "not implemented in engine 2026.10.1")
    await self.session.commit()

  async def execute_run(self, run_id: UUID) -> None:
    run = await self.runs.claim_queued(run_id)
    if run is None:
      return
    await self.session.commit()

    org = run.organization_id
    project_id = run.project_id
    rule_set_id = run.rule_set_id
    drawing_ids = list(run.drawing_revision_ids)
    run_settings = dict(run.settings or {})
    expected_fingerprint = run.fingerprint
    engine_version = run.engine_version
    convention_code = run.convention_code

    try:
      rule_set = await self.rule_sets.get_by_id(rule_set_id)
      if rule_set is None:
        raise RunError("RULE_SET_NOT_FOUND", "Rule set no longer exists.")
      profile, mappings, elements = await self._load_inputs(org, drawing_ids, rule_set.id)
      if self._fingerprint(elements, mappings, profile, rule_set, run_settings) != expected_fingerprint:
        raise RunError("INPUT_CHANGED", "Drawings or rules changed after the run was requested. Request a new run.")

      ctx = CalculationContext(
        run_id=run_id, engine_version=engine_version, fingerprint=expected_fingerprint,
        convention_code=convention_code, rule_set_code=rule_set.code,
        rule_set_version=rule_set.immutable_version, mappings=mappings,
      )
      state: dict = {}

      async def validate():
        state["accepted"], state["rejected"] = await asyncio.to_thread(kernel.validate_input, ctx, elements)
        return {"elements_in": len(elements), "accepted": len(state["accepted"]), "rejected": len(state["rejected"])}

      async def build():
        solids, skipped = await asyncio.to_thread(kernel.build_solids, ctx, state["accepted"])
        state["solids"], state["skipped"] = solids, skipped
        await self.runs.clear_staged(run_id)
        await self.runs.stage_solids([_solid_row(run, s) for s in solids])
        return {"solids": len(solids), "review_required": sum(1 for s in solids if s.status == "REVIEW_REQUIRED"),
                "skipped_by_role": skipped}

      async def measure():
        ledger, unmapped = await asyncio.to_thread(kernel.measure, ctx, state["solids"])
        state["ledger"], state["unmapped"] = ledger, unmapped
        await self.runs.stage_ledger([_ledger_row(run, e) for e in ledger])
        return {"ledger_rows": len(ledger), "unmapped_by_type": unmapped}

      async def check():
        await asyncio.to_thread(kernel.self_check, state["solids"], state["ledger"])
        return {"invariants": "passed"}

      await self._stage(run, "validate_input", validate, 15)
      await self._stage(run, "build_solids", build, 40)
      await self._skip(run, "spatial_index", "find_relations", "allocate")
      await self._stage(run, "measure", measure, 65)
      await self._skip(run, "recipes", "reinforcement")
      await self._stage(run, "self_check", check, 80)

      await self.runs.set_progress(run_id, 90, status="STAGED")
      await self.session.commit()

      promoted = await self.runs.promote(run_id)
      await self.runs.supersede_older_completed(org, project_id, run_id, drawing_ids)
      await self.runs.complete(run_id, {
        "promoted": promoted,
        "elements_in": len(elements),
        "rejected_sample": [
          {"element_id": str(r.element_id), "ifc_type": r.ifc_type, "code": r.code} for r in state["rejected"][:200]
        ],
        "rejected_total": len(state["rejected"]),
        "skipped_by_role": state["skipped"],
        "unmapped_by_type": state["unmapped"],
      })
      await self.session.commit()

    except Exception as exc:
      await self.session.rollback()
      if isinstance(exc, RunError):
        code = exc.code
      elif isinstance(exc, kernel.InvariantViolation):
        code = "SELF_CHECK_FAILED"
      else:
        code = "RUN_FAILED"
      await self.runs.fail_running_stages(run_id, str(exc))
      await self.runs.mark_failed(run_id, code, str(exc))
      await self.session.commit()


      async def validate():
        state["accepted"], state["rejected"] = await asyncio.to_thread(kernel.validate_input, ctx, elements)
        return {"elements_in": len(elements), "accepted": len(state["accepted"]), "rejected": len(state["rejected"])}

      async def build():
        solids, skipped = await asyncio.to_thread(kernel.build_solids, ctx, state["accepted"])
        state["solids"], state["skipped"] = solids, skipped
        await self.runs.clear_staged(run.id)
        await self.runs.stage_solids([_solid_row(run, s) for s in solids])
        return {"solids": len(solids), "review_required": sum(1 for s in solids if s.status == "REVIEW_REQUIRED"),
          "skipped_by_role": skipped}

      async def measure():
        ledger, unmapped = await asyncio.to_thread(kernel.measure, ctx, state["solids"])
        state["ledger"], state["unmapped"] = ledger, unmapped
        await self.runs.stage_ledger([_ledger_row(run, e) for e in ledger])
        return {"ledger_rows": len(ledger), "unmapped_by_type": unmapped}

      async def check():
        await asyncio.to_thread(kernel.self_check, state["solids"], state["ledger"])
        return {"invariants": "passed"}

      await self._stage(run, "validate_input", validate, 15)
      await self._stage(run, "build_solids", build, 40)
      await self._skip(run, "spatial_index", "find_relations", "allocate")
      await self._stage(run, "measure", measure, 65)
      await self._skip(run, "recipes", "reinforcement")
      await self._stage(run, "self_check", check, 80)

      await self.runs.set_progress(run.id, 90, status="STAGED")
      await self.session.commit()

      promoted = await self.runs.promote(run.id)
      await self.runs.supersede_older_completed(org, run.project_id, run.id)
      await self.runs.complete(run.id, {
        "promoted": promoted,
        "elements_in": len(elements),
        "rejected_sample": [
          {"element_id": str(r.element_id), "ifc_type": r.ifc_type, "code": r.code} for r in state["rejected"][:200]
        ],
        "rejected_total": len(state["rejected"]),
        "skipped_by_role": state["skipped"],
        "unmapped_by_type": state["unmapped"],
      })
      await self.session.commit()

    except Exception as exc:
      await self.session.rollback()
      if isinstance(exc, RunError):
        code = exc.code
      elif isinstance(exc, kernel.InvariantViolation):
        code = "SELF_CHECK_FAILED"
      else:
        code = "RUN_FAILED"
      await self.runs.fail_running_stages(run.id, str(exc))
      await self.runs.mark_failed(run.id, code, str(exc))
      await self.session.commit()

  async def get_run(self, organization_id: UUID, run_id: UUID) -> CalculationRun:
    run = await self.runs.get_by_id_and_org(run_id, organization_id)
    if run is None:
      raise TraceException("Calculation run not found.", status_code=404, code="RUN_NOT_FOUND")
    return run

  async def list_stages(self, organization_id: UUID, run_id: UUID):
    await self.get_run(organization_id, run_id)
    return await self.runs.list_stages(run_id, organization_id)

  async def list_ledger(self, organization_id: UUID, run_id: UUID, **kwargs):
    await self.get_run(organization_id, run_id)
    limit = kwargs.pop("limit")
    rows = await self.runs.list_ledger(run_id, organization_id, limit=limit, **kwargs)
    return (rows[:limit], rows[limit - 1].id if len(rows) > limit else None)

  async def list_solids(self, organization_id: UUID, run_id: UUID, **kwargs):
    await self.get_run(organization_id, run_id)
    limit = kwargs.pop("limit")
    rows = await self.runs.list_solids(run_id, organization_id, limit=limit, **kwargs)
    return (rows[:limit], rows[limit - 1].id if len(rows) > limit else None)