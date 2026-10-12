from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from app.core.exceptions import TraceException
from app.engine.measure import takeoff as tk
import os
import tempfile
from decimal import Decimal
from pypdf import PdfReader
from io import BytesIO
from uuid import UUID, uuid4
from app.modules.audit.models import AuditAction
from app.modules.drawings_boq.takeoff.repository import TakeoffRepository
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.audit.service import AuditLogService
from app.modules.drawings_boq.service import DrawingBOQService
from app.modules.drawings_boq.standards.service import StandardsService
from app.modules.drawings_boq.boq_logic import UNIT_TABLE
from app.modules.drawings_boq.finish_schedule.common import audit_entity, require_work_item
from app.modules.drawings_boq.models import DrawingFormat, TakeoffCalibration, TakeoffMeasurement, TakeoffSheet
from app.modules.drawings_boq.takeoff import repository as repo_mod
from app.modules.drawings_boq.takeoff.scale import parse_scale_text, to_mm
from app.shared.storage import download_to_path

MAX_SHEETS = 300
MATERIAL_FIELDS = ("quantity_mode", "geometry", "params", "calibration_id", "work_item_code", "level_id", "recon_mode", "material_grade")

def _now() -> datetime:
  return datetime.now(timezone.utc)

def _fail(exc: tk.TakeoffError) -> TraceException:
  return TraceException(exc.message, status_code=422, code=exc.code)

def _point_json(raw) -> list:
  p = tk.parse_point(raw)
  return [float(p[0]), float(p[1])]

def _distance_spec(kd) -> dict:
  if isinstance(kd, dict):
    return {"p1": _point_json(kd["p1"]), "p2": _point_json(kd["p2"]), "known_mm": format(Decimal(str(kd["known_mm"])), "f")}
  return {"p1": _point_json(kd.p1), "p2": _point_json(kd.p2), "known_mm": format(to_mm(kd.value, kd.unit), "f")}

def build_calibration(method: str, reference, ratio, scale_text: str | None, check, user_unit: Decimal = Decimal(1)) -> dict:
  ref: dict = {}
  ratio_val = None
  if method == "TWO_POINT":
    if reference is None:
      raise TraceException("A two-point calibration needs two points and the real distance.", status_code=422, code="CALIBRATION_INCOMPLETE")
    ref = _distance_spec(reference)
  elif method == "SCALE_RATIO":
    ratio_val = Decimal(str(ratio)) if ratio is not None else parse_scale_text(scale_text)
    if ratio_val is None or ratio_val <= 0:
      raise TraceException(f"Could not read a scale from '{scale_text or ''}'. Type it like 1:100 or 1/8\" = 1'-0\".",
        status_code=422, code="SCALE_TEXT_UNREADABLE")
    if scale_text and scale_text.strip():
      ref = {"scale_text": scale_text.strip()}
  else:
    raise TraceException(f"Unknown calibration method '{method}'.", status_code=422, code="CALIBRATION_METHOD_INVALID")
  check_ref = _distance_spec(check) if check is not None else None
  try:
    ev = tk.evaluate_calibration(repo_mod.calibration_input_from_spec(method, ref, check_ref, ratio_val, user_unit))
  except tk.TakeoffError as exc:
    raise _fail(exc)
  q12, q4 = Decimal("0.000000000001"), Decimal("0.0001")
  return {
    "method": method, "ref": ref, "check_ref": check_ref, "ratio": ratio_val,
    "usable": ev.usable, "reason": ev.reason,
    "mm_per_pt": ev.mm_per_pt.quantize(q12) if ev.mm_per_pt is not None else None,
    "check_error_pct": ev.error_pct, "baseline_pt": ev.baseline_pt.quantize(q4) if ev.baseline_pt is not None else None,
    "quality_factor": ev.factor if ev.usable else Decimal(0), "warnings": list(ev.warnings),
  }

def computed_json(comp: tk.Computed) -> dict:
  return {
    "quantity": str(comp.quantity), "unit": comp.unit, "formula": comp.formula, "confidence": str(comp.confidence),
    "uncertainty_pct": str(comp.uncertainty_pct), "warnings": list(comp.warnings), "steps": comp.steps, "inputs": comp.inputs,
  }

def page_geometry(contents: bytes) -> list[dict]:
  try:
    reader = PdfReader(BytesIO(contents))
    
    if reader.is_encrypted:
      try:
        unlocked = int(reader.decrypt(""))
      except Exception:
        unlocked = 0
      if not unlocked:
        raise TraceException("This PDF is password protected.", status_code=422, code="PDF_ENCRYPTED")
    pages = list(reader.pages)
  except TraceException:
    raise
  except Exception:
    raise TraceException("This PDF could not be read.", status_code=422, code="PDF_UNREADABLE")
  if not pages:
    raise TraceException("This PDF has no pages.", status_code=422, code="PDF_EMPTY")
  if len(pages) > MAX_SHEETS:
    raise TraceException(f"This PDF has {len(pages)} pages; takeoff supports up to {MAX_SHEETS}.", status_code=422, code="PDF_TOO_MANY_PAGES")
  out = []
  for i, page in enumerate(pages, 1):
    box = page.cropbox
    width, height = float(box.width), float(box.height)
    try:
      user_unit = float(page.get("/UserUnit", 1) or 1)
    except Exception:
      user_unit = 1.0
    rotation = int(page.rotation or 0) % 360
    out.append({"page_no": i, "width_pt": width, "height_pt": height, "rotation": rotation if rotation in (0, 90, 180, 270) else 0,
      "user_unit": user_unit if user_unit > 0 else 1.0})
  return out

class TakeoffService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = TakeoffRepository(session)
    self.audit = AuditLogService(session)
    self._profiles: dict = {}

  async def _log(self, org, user_id, entity_id, action, message) -> None:
    await self.audit.log(org, user_id, audit_entity("DRAWING"), entity_id, action, message)

  async def _profile(self, org: UUID, rule_set_code: str | None = None):
    if rule_set_code in self._profiles:
      return self._profiles[rule_set_code]
    profile = None
    try:
      
      rule_set = await DrawingBOQService(self.session).get_active_rule_set(org, rule_set_code)
      profile = await StandardsService(self.session).profile_for_rule_set(rule_set.id)
    except TraceException:
      if rule_set_code:
        raise
    self._profiles[rule_set_code] = profile
    return profile

  async def _pdf_drawing(self, org: UUID, drawing_id: UUID):
    drawing = await self.repo.drawing(org, drawing_id)
    if drawing is None:
      raise TraceException("Drawing not found.", status_code=404, code="DRAWING_NOT_FOUND")
    if drawing.format != DrawingFormat.PDF:
      raise TraceException("Takeoff is for PDF drawings. IFC drawings are measured from the model.", status_code=422, code="DRAWING_NOT_PDF")
    return drawing

  async def _sheet(self, org: UUID, sheet_id: UUID, lock: bool = False) -> TakeoffSheet:
    sheet = await self.repo.sheet(org, sheet_id, lock=lock)
    if sheet is None:
      raise TraceException("Sheet not found.", status_code=404, code="SHEET_NOT_FOUND")
    return sheet

  async def _calibration(self, org: UUID, calibration_id: UUID, lock: bool = False) -> TakeoffCalibration:
    cal = await self.repo.calibration(org, calibration_id, lock=lock)
    if cal is None:
      raise TraceException("Calibration not found.", status_code=404, code="CALIBRATION_NOT_FOUND")
    return cal

  async def _measurement(self, org: UUID, measurement_id: UUID, lock: bool = False) -> TakeoffMeasurement:
    m = await self.repo.measurement(org, measurement_id, lock=lock)
    if m is None:
      raise TraceException("Measurement not found.", status_code=404, code="MEASUREMENT_NOT_FOUND")
    return m

  async def _check_level(self, org: UUID, level_id: UUID | None) -> None:
    if level_id is not None and not await self.repo.level_exists(org, level_id):
      raise TraceException("Level not found.", status_code=404, code="LEVEL_NOT_FOUND")

  async def _check_work_item(self, org: UUID, code: str | None) -> str | None:
    code = (code or "").strip() or None
    if code is None:
      return None
    if code in tk.RESERVED_CODES:
      raise TraceException(f"{code} is measured from bar schedules or the model, not from a PDF drawing.",
        status_code=422, code="WORK_ITEM_RESERVED")
    await require_work_item(self.session, org, code)
    return code

  @staticmethod
  def _check_mode(kind: str, mode: str) -> None:
    if (kind, mode) not in tk.MODES:
      valid = ", ".join(sorted(m for k, m in tk.MODES if k == kind))
      raise TraceException(f"{mode} is not a quantity mode for a {kind.lower()} measurement. Use one of: {valid}.",
        status_code=422, code="INVALID_MODE")

  @staticmethod
  def _params_json(params) -> dict:
    return params.model_dump(mode="json", exclude_none=True) if hasattr(params, "model_dump") else dict(params or {})

  async def _default_calibration(self, org: UUID, sheet_id: UUID) -> TakeoffCalibration | None:
    cals = [c for c in await self.repo.calibrations(org, [sheet_id]) if c.is_default and c.usable]
    return cals[0] if cals else None

  def _evaluate(self, m: TakeoffMeasurement, sheet: TakeoffSheet, cal: TakeoffCalibration | None, profile) -> dict:
    try:
      cal_eval = tk.evaluate_calibration(repo_mod.calibration_input(cal, repo_mod.sheet_user_unit(sheet))) if cal is not None else None
      comp = tk.compute_measurement(repo_mod.measurement_input(m), repo_mod.sheet_input(sheet), cal_eval, profile)
      return computed_json(comp)
    except tk.TakeoffError as exc:
      return {"error": {"code": exc.code, "message": exc.message}}

  async def sync_sheets(self, org: UUID, drawing_id: UUID, user_id: UUID) -> dict:
    drawing = await self._pdf_drawing(org, drawing_id)
    with tempfile.TemporaryDirectory() as tmp:
      path = os.path.join(tmp, "drawing.pdf")
      await asyncio.to_thread(download_to_path, drawing.storage_key, path)
      with open(path, "rb") as handle:
        contents = handle.read()
    pages = await asyncio.to_thread(page_geometry, contents)
    existing = {s.page_no: s for s in await self.repo.sheets(org, drawing_id)}
    created = 0
    
    for p in pages:
      if p["page_no"] in existing:
        continue
      self.session.add(TakeoffSheet(
        id=uuid4(), organization_id=org, project_id=drawing.project_id, drawing_id=drawing.id, page_no=p["page_no"],
        width_pt=Decimal(str(round(p["width_pt"], 4))), height_pt=Decimal(str(round(p["height_pt"], 4))),
        rotation=p["rotation"], content_kind="UNKNOWN", prep_status="PENDING", detected_scale={},
        prep_meta={"user_unit": p["user_unit"]}))
      created += 1
    await self.session.flush()
    if created:
      await self._log(org, user_id, drawing.id, AuditAction.CREATE, f"Opened {created} sheet(s) for takeoff on {drawing.original_filename}")
    await self.session.commit()
    return await self.overview(org, drawing_id)

  async def overview(self, org: UUID, drawing_id: UUID) -> dict:
    await self._pdf_drawing(org, drawing_id)
    sheets = await self.repo.sheets(org, drawing_id)
    ids = [s.id for s in sheets]
    cals = await self.repo.calibrations(org, ids)
    ms = await self.repo.measurements(org, ids)
    calibrated = {c.sheet_id for c in cals if c.usable and c.is_default}
    return {
      "drawing_id": drawing_id, "sheets": sheets, "calibrations": cals, "measurements": ms,
      "summary": {
        "sheets": len(sheets), "calibrated_sheets": len(calibrated), "measurements": len(ms),
        "confirmed": sum(1 for m in ms if m.status == "CONFIRMED"), "draft": sum(1 for m in ms if m.status == "DRAFT"),
      },
    }

  async def update_sheet(self, org: UUID, sheet_id: UUID, user_id: UUID, payload) -> TakeoffSheet:
    sheet = await self._sheet(org, sheet_id, lock=True)
    fs = payload.model_fields_set
    kind_changed = False
    
    if "label" in fs:
      sheet.label = (payload.label or "").strip() or None
    if "level_id" in fs:
      await self._check_level(org, payload.level_id)
      sheet.level_id = payload.level_id
    if "scale_text" in fs:
      sheet.scale_text = (payload.scale_text or "").strip() or None
    if "content_kind" in fs and payload.content_kind is not None and payload.content_kind != sheet.content_kind:
      sheet.content_kind, kind_changed = payload.content_kind, True
      sheet.prep_meta = {**(sheet.prep_meta or {}), "kind_source": "USER"}
    await self.session.flush()
    
    if kind_changed:
      await self._refresh_sheet_measurements(org, sheet)
    await self._log(org, user_id, sheet.id, AuditAction.UPDATE, f"Updated takeoff sheet {sheet.page_no}")
    await self.session.commit()
    return sheet

  async def _refresh_sheet_measurements(self, org: UUID, sheet: TakeoffSheet) -> int:
    profile = await self._profile(org)
    cals = {c.id: c for c in await self.repo.calibrations(org, [sheet.id])}
    n = 0
    for m in await self.repo.measurements_for_sheet(org, sheet.id):
      m.computed = self._evaluate(m, sheet, cals.get(m.calibration_id), profile)
      n += 1
    await self.session.flush()
    return n

  async def _set_default(self, org: UUID, sheet_id: UUID, cal: TakeoffCalibration) -> None:
    await self.session.execute(
      update(TakeoffCalibration).where(TakeoffCalibration.organization_id == org, TakeoffCalibration.sheet_id == sheet_id,
        TakeoffCalibration.id != cal.id, TakeoffCalibration.is_default.is_(True)).values(is_default=False))
    await self.session.flush()
    cal.is_default = True
    await self.session.flush()

  async def create_calibration(self, org: UUID, sheet_id: UUID, user_id: UUID, payload) -> TakeoffCalibration:
    sheet = await self._sheet(org, sheet_id, lock=True)
    cols = build_calibration(payload.method, payload.reference, payload.ratio, payload.scale_text, payload.check,
      repo_mod.sheet_user_unit(sheet))
    cal = TakeoffCalibration(id=uuid4(), organization_id=org, sheet_id=sheet.id, label=(payload.label or "").strip() or None,
      created_by_user_id=user_id, is_default=False, **cols)
    self.session.add(cal)
    await self.session.flush()
    
    others = [c for c in await self.repo.calibrations(org, [sheet.id]) if c.id != cal.id and c.usable and c.is_default]
    if cal.usable and (payload.make_default or not others):
      await self._set_default(org, sheet.id, cal)
    if payload.method == "SCALE_RATIO" and (payload.scale_text or "").strip() and not sheet.scale_text:
      sheet.scale_text = payload.scale_text.strip()
    await self._log(org, user_id, cal.id, AuditAction.CREATE,
      f"Calibrated sheet {sheet.page_no} ({payload.method.replace('_', ' ').lower()}, {'usable' if cal.usable else 'not usable'})")
    await self.session.commit()
    return cal

  async def update_calibration(self, org: UUID, calibration_id: UUID, user_id: UUID, payload) -> TakeoffCalibration:
    cal = await self._calibration(org, calibration_id, lock=True)
    sheet = await self._sheet(org, cal.sheet_id, lock=True)
    fs = payload.model_fields_set
    reference = payload.reference if "reference" in fs and payload.reference is not None else cal.ref
    ratio, scale_text = cal.ratio, (cal.ref or {}).get("scale_text")
    
    if "ratio" in fs or "scale_text" in fs:
      ratio = payload.ratio if "ratio" in fs else None
      scale_text = payload.scale_text if "scale_text" in fs else None
    check = (payload.check if "check" in fs else cal.check_ref)
    cols = build_calibration(cal.method, reference if cal.method == "TWO_POINT" else None, ratio, scale_text, check,
      repo_mod.sheet_user_unit(sheet))
    
    for key, value in cols.items():
      setattr(cal, key, value)
    if "label" in fs:
      cal.label = (payload.label or "").strip() or None
    if not cal.usable and cal.is_default:
      cal.is_default = False
    await self.session.flush()
    recomputed, reverted = await self._recompute_dependents(org, cal, sheet)
    await self._log(org, user_id, cal.id, AuditAction.UPDATE,
      f"Updated calibration on sheet {sheet.page_no}; {recomputed} measurement(s) recomputed, {reverted} returned to draft")
    await self.session.commit()
    cal.measurements_recomputed, cal.measurements_reverted_to_draft = recomputed, reverted
    return cal

  async def _recompute_dependents(self, org: UUID, cal: TakeoffCalibration, sheet: TakeoffSheet) -> tuple[int, int]:
    profile = await self._profile(org)
    recomputed = reverted = 0
    for m in await self.repo.measurements_for_calibration(org, cal.id):
      m.computed = self._evaluate(m, sheet, cal, profile)
      recomputed += 1
      if not cal.usable and m.status == "CONFIRMED":
        m.status, m.confirmed_at, m.confirmed_by_user_id = "DRAFT", None, None
        reverted += 1
    await self.session.flush()
    return recomputed, reverted

  async def set_default_calibration(self, org: UUID, calibration_id: UUID, user_id: UUID) -> TakeoffCalibration:
    cal = await self._calibration(org, calibration_id, lock=True)
    if not cal.usable:
      raise TraceException(cal.reason or "This calibration is not usable.", status_code=422, code="CALIBRATION_UNUSABLE")
    await self._set_default(org, cal.sheet_id, cal)
    await self._log(org, user_id, cal.id, AuditAction.UPDATE, "Made calibration the sheet default")
    await self.session.commit()
    return cal

  async def delete_calibration(self, org: UUID, calibration_id: UUID, user_id: UUID) -> None:
    cal = await self._calibration(org, calibration_id, lock=True)
    users = await self.repo.measurements_for_calibration(org, cal.id)
    
    if users:
      raise TraceException(
        f"{len(users)} measurement(s) use this calibration. Delete them or move them to another calibration first.",
        status_code=409, code="CALIBRATION_IN_USE")
    sheet_id, was_default = cal.sheet_id, cal.is_default
    await self.session.delete(cal)
    await self.session.flush()
    if was_default:
      remaining = [c for c in await self.repo.calibrations(org, [sheet_id]) if c.usable]
      if remaining:
        await self._set_default(org, sheet_id, remaining[-1])
    await self._log(org, user_id, calibration_id, AuditAction.DELETE, "Deleted a calibration")
    await self.session.commit()

  async def create_measurement(self, org: UUID, sheet_id: UUID, user_id: UUID, payload) -> TakeoffMeasurement:
    sheet = await self._sheet(org, sheet_id, lock=True)
    self._check_mode(payload.kind, payload.quantity_mode)
    await self._check_level(org, payload.level_id)
    code = await self._check_work_item(org, payload.work_item_code)

    try:
      geometry = tk.normalized_geometry(payload.kind, payload.geometry)
    except tk.TakeoffError as exc:
      raise _fail(exc)
    cal = None
    if tk.needs_calibration(payload.kind, payload.quantity_mode):
      if payload.calibration_id is not None:
        cal = await self._calibration(org, payload.calibration_id)
        if cal.sheet_id != sheet.id:
          raise TraceException("That calibration belongs to another sheet.", status_code=422, code="CALIBRATION_WRONG_SHEET")
      else:
        cal = await self._default_calibration(org, sheet.id)
    source = payload.source
    if source != "MANUAL":
      from app.modules.drawings_boq.takeoff.prep_service import PrepService
      source = await PrepService(self.session).verified_source(org, sheet, payload.kind, geometry, source, payload.tag)
    m = TakeoffMeasurement(
      id=uuid4(), organization_id=org, project_id=sheet.project_id, sheet_id=sheet.id,
      calibration_id=cal.id if cal is not None else None, kind=payload.kind, quantity_mode=payload.quantity_mode,
      geometry=geometry, params=self._params_json(payload.params), work_item_code=code,
      level_id=payload.level_id if payload.level_id is not None else sheet.level_id,
      label=(payload.label or "").strip() or None, tag=(payload.tag or "").strip() or None,
      material_grade=(payload.material_grade or "").strip() or None, recon_mode=payload.recon_mode, source=source,
        status="DRAFT", geometry_hash=tk.geometry_hash(payload.kind, geometry), created_by_user_id=user_id)
    m.computed = self._evaluate(m, sheet, cal, await self._profile(org))
    self.session.add(m)
    await self.session.flush()
    await self._log(org, user_id, m.id, AuditAction.CREATE, f"Drew a {payload.kind.lower()} measurement on sheet {sheet.page_no}")
    await self.session.commit()
    return m

  async def update_measurement(self, org: UUID, measurement_id: UUID, user_id: UUID, payload) -> TakeoffMeasurement:
    m = await self._measurement(org, measurement_id, lock=True)
    sheet = await self._sheet(org, m.sheet_id)
    fs = payload.model_fields_set
    changed: set = set()
    if "quantity_mode" in fs and payload.quantity_mode is not None and payload.quantity_mode != m.quantity_mode:
      self._check_mode(m.kind, payload.quantity_mode)
      m.quantity_mode = payload.quantity_mode
      changed.add("quantity_mode")
      
    if "geometry" in fs and payload.geometry is not None:
      try:
        geometry = tk.normalized_geometry(m.kind, payload.geometry)
        
      except tk.TakeoffError as exc:
        raise _fail(exc)
      if geometry != m.geometry:
        m.geometry, m.geometry_hash = geometry, tk.geometry_hash(m.kind, geometry)
        changed.add("geometry")
        if m.source != "MANUAL":
          from app.modules.drawings_boq.takeoff.prep_service import PrepService
          m.source = await PrepService(self.session).verified_source(org, sheet, m.kind, geometry, m.source, m.tag)
      
    if "params" in fs and payload.params is not None:
      params = self._params_json(payload.params)
      if params != (m.params or {}):
        m.params = params
        changed.add("params")
    if "work_item_code" in fs:
      code = await self._check_work_item(org, payload.work_item_code)
      if code != m.work_item_code:
        m.work_item_code = code
        changed.add("work_item_code")
        
    if "level_id" in fs:
      await self._check_level(org, payload.level_id)
      if payload.level_id != m.level_id:
        m.level_id = payload.level_id
        changed.add("level_id")
    if "recon_mode" in fs and payload.recon_mode is not None and payload.recon_mode != m.recon_mode:
      m.recon_mode = payload.recon_mode
      changed.add("recon_mode")
    if "material_grade" in fs:
      grade = (payload.material_grade or "").strip() or None
      if grade != m.material_grade:
        m.material_grade = grade
        changed.add("material_grade")
    if "calibration_id" in fs and payload.calibration_id != m.calibration_id:
      if payload.calibration_id is not None:
        new_cal = await self._calibration(org, payload.calibration_id)
        if new_cal.sheet_id != m.sheet_id:
          raise TraceException("That calibration belongs to another sheet.", status_code=422, code="CALIBRATION_WRONG_SHEET")
      m.calibration_id = payload.calibration_id
      changed.add("calibration_id")
      
    if "label" in fs:
      m.label = (payload.label or "").strip() or None
    if "tag" in fs:
      m.tag = (payload.tag or "").strip() or None
    if changed & set(MATERIAL_FIELDS) and m.status == "CONFIRMED":
      m.status, m.confirmed_at, m.confirmed_by_user_id = "DRAFT", None, None
      
    if m.calibration_id is None and tk.needs_calibration(m.kind, m.quantity_mode):
      default = await self._default_calibration(org, m.sheet_id)
      m.calibration_id = default.id if default is not None else None
    cal = await self.repo.calibration(org, m.calibration_id) if m.calibration_id else None
    m.computed = self._evaluate(m, sheet, cal, await self._profile(org))
    await self.session.flush()
    await self._log(org, user_id, m.id, AuditAction.UPDATE, f"Edited a takeoff measurement ({', '.join(sorted(changed)) or 'labels'})")
    await self.session.commit()
    return m

  async def delete_measurement(self, org: UUID, measurement_id: UUID, user_id: UUID) -> None:
    m = await self._measurement(org, measurement_id, lock=True)
    await self.session.delete(m)
    await self._log(org, user_id, measurement_id, AuditAction.DELETE, "Deleted a takeoff measurement")
    await self.session.commit()

  async def _validate_confirmable(self, org: UUID, m: TakeoffMeasurement, sheet: TakeoffSheet) -> dict:
    def fail(message: str, code: str):
      raise TraceException(message, status_code=422, code=code)
    if not m.work_item_code:
      fail("Choose a work item before confirming.", "MEASUREMENT_NEEDS_WORK_ITEM")
    if m.work_item_code in tk.RESERVED_CODES:
      fail(f"{m.work_item_code} is measured from bar schedules or the model, not from a PDF drawing.", "WORK_ITEM_RESERVED")
    wi = await require_work_item(self.session, org, m.work_item_code)
    cal = await self.repo.calibration(org, m.calibration_id) if m.calibration_id else None
    
    if tk.needs_calibration(m.kind, m.quantity_mode):
      if cal is None:
        fail("Calibrate the sheet before confirming this measurement.", "PDF_UNCALIBRATED")
      if not cal.usable:
        fail(cal.reason or "The calibration is not usable.", "CALIBRATION_UNUSABLE")
        
    try:
      cal_eval = tk.evaluate_calibration(repo_mod.calibration_input(cal, repo_mod.sheet_user_unit(sheet))) if cal is not None else None
      comp = tk.compute_measurement(repo_mod.measurement_input(m), repo_mod.sheet_input(sheet), cal_eval, await self._profile(org))
    except tk.TakeoffError as exc:
      raise _fail(exc)
    if comp.quantity <= 0:
      fail("The measurement comes to zero. Check the dimensions and deductions.", "ZERO_QUANTITY")
    family = UNIT_TABLE.get((wi.unit or "").strip().lower())
    if family is not None and family[0] != comp.unit:
      fail(f"Work item {wi.code} is measured in {family[0]}, but this measurement gives {comp.unit}. Change the quantity mode or the work item.",
        "TAKEOFF_UNIT_MISMATCH")
      
    twin = (await self.session.execute(
      select(TakeoffMeasurement.id).where(
        TakeoffMeasurement.organization_id == org, TakeoffMeasurement.sheet_id == m.sheet_id,
        TakeoffMeasurement.status == "CONFIRMED", TakeoffMeasurement.id != m.id,
        TakeoffMeasurement.geometry_hash == m.geometry_hash, TakeoffMeasurement.work_item_code == m.work_item_code,
        TakeoffMeasurement.quantity_mode == m.quantity_mode))).first()
    if twin is not None:
      fail("The same extent is already confirmed for this work item on this sheet; confirming it again would count it twice.",
        "DUPLICATE_MEASUREMENT")
    return computed_json(comp)

  async def confirm(self, org: UUID, measurement_id: UUID, user_id: UUID) -> TakeoffMeasurement:
    m = await self._measurement(org, measurement_id, lock=True)
    sheet = await self._sheet(org, m.sheet_id)
    m.computed = await self._validate_confirmable(org, m, sheet)
    m.status, m.confirmed_at, m.confirmed_by_user_id = "CONFIRMED", _now(), user_id
    await self.session.flush()
    await self._log(org, user_id, m.id, AuditAction.APPROVE, f"Confirmed a takeoff measurement for {m.work_item_code}")
    await self.session.commit()
    return m

  async def unconfirm(self, org: UUID, measurement_id: UUID, user_id: UUID) -> TakeoffMeasurement:
    m = await self._measurement(org, measurement_id, lock=True)
    if m.status != "CONFIRMED":
      return m
    m.status, m.confirmed_at, m.confirmed_by_user_id = "DRAFT", None, None
    await self.session.flush()
    await self._log(org, user_id, m.id, AuditAction.STATUS_CHANGE, "Returned a takeoff measurement to draft")
    await self.session.commit()
    return m

  async def bulk_confirm(self, org: UUID, ids: list[UUID], user_id: UUID) -> dict:
    confirmed, failed = [], []
    
    for mid in dict.fromkeys(ids):
      try:
        m = await self._measurement(org, mid, lock=True)
        sheet = await self._sheet(org, m.sheet_id)
        m.computed = await self._validate_confirmable(org, m, sheet)
        m.status, m.confirmed_at, m.confirmed_by_user_id = "CONFIRMED", _now(), user_id
        await self.session.flush()
        confirmed.append(mid)
        
      except TraceException as exc:
        failed.append({"id": str(mid), "code": exc.code, "message": exc.message})
    if confirmed:
      await self._log(org, user_id, confirmed[0], AuditAction.APPROVE, f"Confirmed {len(confirmed)} takeoff measurement(s)")
    await self.session.commit()
    return {"confirmed": confirmed, "failed": failed}

  async def preview(self, org: UUID, payload) -> dict:
    sheet = await self._sheet(org, payload.sheet_id)
    self._check_mode(payload.kind, payload.quantity_mode)
    profile = await self._profile(org, payload.rule_set_code)
    try:
      geometry = tk.normalized_geometry(payload.kind, payload.geometry)
      cal = None
      if tk.needs_calibration(payload.kind, payload.quantity_mode):
        cal = (await self._calibration(org, payload.calibration_id)) if payload.calibration_id else await self._default_calibration(org, sheet.id)
        if cal is not None and cal.sheet_id != sheet.id:
          raise TraceException("That calibration belongs to another sheet.", status_code=422, code="CALIBRATION_WRONG_SHEET")

      source = payload.source
      if source != "MANUAL":
        from app.modules.drawings_boq.takeoff.prep_service import PrepService
        source = await PrepService(self.session).verified_source(org, sheet, payload.kind, geometry, source, None)

      probe = tk.MeasurementInput(
        id=uuid4(), sheet_id=sheet.id, calibration_id=cal.id if cal is not None else None, kind=payload.kind,
        quantity_mode=payload.quantity_mode, geometry=geometry, params=self._params_json(payload.params),
        work_item_code=None, source=source)
      cal_eval = tk.evaluate_calibration(repo_mod.calibration_input(cal, repo_mod.sheet_user_unit(sheet))) if cal is not None else None
      comp = tk.compute_measurement(probe, repo_mod.sheet_input(sheet), cal_eval, profile)
    except tk.TakeoffError as exc:
      return {"ok": False, "error": {"code": exc.code, "message": exc.message}}
    j = computed_json(comp)
    return {"ok": True, **j}

  async def reconciliation(self, org: UUID, project_id: UUID) -> dict:
    from app.modules.projects.repository import ProjectRepository
    if await ProjectRepository(self.session).get_by_id_and_org(project_id, org) is None:
      raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")
    run = await self.repo.latest_completed_run(org, project_id)
    if run is None:
      return {"run_id": None, "stats": {}, "measurements": []}
    rows = []
    for m in await self.repo.project_measurements(org, project_id):
      last = m.last_result or {}
      if last.get("run_id") != str(run.id):
        continue
      rows.append({**last, "measurement_id": str(m.id), "sheet_id": str(m.sheet_id), "label": m.label, "tag": m.tag, "kind": m.kind})
    return {"run_id": run.id, "stats": (run.stats or {}).get("pdf_takeoff") or {}, "measurements": rows}

  @staticmethod
  def modes() -> list[dict]:
    return [{"kind": k, "quantity_mode": mode, "output_unit": unit, "required_params": list(req), "formula_code": formula}
      for (k, mode), (formula, unit, req) in sorted(tk.MODES.items())]
