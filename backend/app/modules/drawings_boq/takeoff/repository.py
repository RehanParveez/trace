from __future__ import annotations
from app.engine.measure import takeoff as tk
from app.engine.measure.member_steel import STEEL_FAMILIES, clean_steel
from app.modules.drawings_boq.models import TakeoffViewAlignment, TakeoffSheet, TakeoffCalibration, BuildingLevel, CalculationRun, Drawing, TakeoffMeasurement, TakeoffCandidate, DrawingElement
from app.modules.drawings_boq.takeoff.prep import stairs as STR
from app.modules.drawings_boq.takeoff.evidence import evidence_for
from app.modules.drawings_boq.takeoff.register import row_id
from app.modules.drawings_boq.takeoff import frame_views as FV
from app.modules.drawings_boq.takeoff.space_loader import load_space
from dataclasses import replace
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from sqlalchemy import func, select

def _dec(value) -> Decimal | None:
  return None if value is None or value == "" else Decimal(str(value))

def _point(raw):
  return tk.parse_point(raw) if raw else None

def sheet_input(row: TakeoffSheet) -> tk.SheetInput:
  return tk.SheetInput(id=row.id, drawing_id=row.drawing_id, page_no=row.page_no, content_kind=row.content_kind,
    label=row.label, level_id=row.level_id)

def sheet_user_unit(sheet: TakeoffSheet) -> Decimal:
  value = _dec((sheet.prep_meta or {}).get("user_unit")) or Decimal(1)
  return value if value > 0 else Decimal(1)

def calibration_input_from_spec(method: str, ref: dict | None, check_ref: dict | None, ratio, user_unit: Decimal = Decimal(1),
  id=None, sheet_id=None, label=None) -> tk.CalibrationInput:
  ref, chk = ref or {}, check_ref or {}
  
  return tk.CalibrationInput(
    id=id, sheet_id=sheet_id, method=method, ratio=_dec(ratio),
    p1=_point(ref.get("p1")), p2=_point(ref.get("p2")), known_mm=_dec(ref.get("known_mm")),
    check_p1=_point(chk.get("p1")), check_p2=_point(chk.get("p2")), check_known_mm=_dec(chk.get("known_mm")),
    label=label, user_unit=user_unit)

def calibration_input(row: TakeoffCalibration, user_unit: Decimal = Decimal(1)) -> tk.CalibrationInput:
  return calibration_input_from_spec(row.method, row.ref, row.check_ref, row.ratio, user_unit,
    id=row.id, sheet_id=row.sheet_id, label=row.label)

def measurement_input(row: TakeoffMeasurement) -> tk.MeasurementInput:
  return tk.MeasurementInput(
    id=row.id, sheet_id=row.sheet_id, calibration_id=row.calibration_id, kind=row.kind, quantity_mode=row.quantity_mode,
    geometry=row.geometry or {}, params=row.params or {}, work_item_code=row.work_item_code, level_id=row.level_id,
    label=row.label, tag=row.tag, material_grade=row.material_grade, recon_mode=row.recon_mode, source=row.source)

MEMBER_CATEGORIES = ("FOOTING",)
FORMWORK_CATEGORIES = ("COLUMN", "FOOTING", "SLAB", "LINTEL", "BEAM", "STAIR")
FORMWORK_SITE = {"OHWT": "TANK", "UGWT": "TANK", "SEPTIC": "TANK", "COPING": "COPING", "CHAJJA": "CHAJJA", "BALCONY_SLAB": "BALCONY_SLAB"}

def _mm(value) -> Decimal | None:
  v = _dec(value)
  return v if v is not None and v > 0 else None

def stair_detail(cand: TakeoffCandidate, depth_mm: Decimal) -> dict | None:
  """What a flight's formwork needs beyond its box: riser, tread, number of steps and the waist slab, the last found from the equivalent depth the stair was measured with."""
  f = cand.facts or {}
  riser, tread, steps = _mm(f.get("riser_mm")), _mm(f.get("tread_mm")), f.get("steps")
  if riser is None or tread is None or not steps:
    return None
  waist = STR.waist_from_depth_mm(float(riser), float(tread), float(depth_mm))
  if waist <= 0:
    return None
  return {"riser_mm": float(riser), "tread_mm": float(tread), "steps": int(steps), "waist_mm": round(waist, 1)}

def view_key(cand: TakeoffCandidate, sheet: TakeoffSheet) -> str:
  return str((((cand.facts or {}).get("view") or {}).get("key")) or f"SHEET:{sheet.id}")

def sheet_positions(cand: TakeoffCandidate, m: TakeoffMeasurement) -> tuple:
  """Where each counted mark sits on its sheet in millimetres, or () when the sheet has no scale or the points do not read."""
  points = (m.geometry or {}).get("points") or []
  scale = _mm(cand.mm_per_pt)
  if scale is None or not points:
    return ()
  try:
    return tuple((round(float(pt[0]) * float(scale), 1), round(float(pt[1]) * float(scale), 1)) for pt in points)
  except (TypeError, ValueError, IndexError):
    return ()

def member_input(cand: TakeoffCandidate, m: TakeoffMeasurement, sheet: TakeoffSheet) -> tk.MemberInput | None:
  """A counted footing mark placed on its drawing view, or nothing when the mark has no position or no size to place it with."""
  points = (m.geometry or {}).get("points") or []
  scale = _mm(cand.mm_per_pt)
  p = m.params or {}
  length, width, depth = _mm(p.get("length_mm")), _mm(p.get("width_mm")), _mm(p.get("depth_mm"))
  if scale is None or not points or length is None or width is None or depth is None:
    return None
  view = ((cand.facts or {}).get("view") or {})
  frame = str(view.get("key") or f"SHEET:{sheet.id}")
  try:
    positions = tuple((round(float(pt[0]) * float(scale), 1), round(float(pt[1]) * float(scale), 1)) for pt in points)
  except (TypeError, ValueError, IndexError):
    return None
  return tk.MemberInput(
    measurement_id=m.id, candidate_id=cand.id, sheet_id=sheet.id, page_no=sheet.page_no, category=cand.category, tag=cand.tag, frame=frame,
    level_id=m.level_id, element_ids=tuple(row_id(sheet.id, cand.ckey, i) for i in range(len(positions))), points_mm=positions,
    length_mm=length, width_mm=width, depth_mm=depth, confidence=_dec(cand.confidence) or Decimal(1))

async def load_members(session: AsyncSession, org: UUID, measurements: list, sheets: dict) -> tuple:
  ids = [m.id for m in measurements if m.quantity_mode == "COUNT_X_VOLUME"]
  if not ids:
    return ()
  
  cands = (await session.execute(
    select(TakeoffCandidate).where(TakeoffCandidate.organization_id == org, TakeoffCandidate.measurement_id.in_(ids),
      TakeoffCandidate.category.in_(MEMBER_CATEGORIES), TakeoffCandidate.decision == "ACCEPTED"))).scalars().all()
  by_measurement = {c.measurement_id: c for c in cands}
  wanted = [row_id(sheets[m.sheet_id].id, by_measurement[m.id].ckey, i)
    for m in measurements if m.id in by_measurement for i in range(len((m.geometry or {}).get("points") or []))]
  present = set((await session.execute(select(DrawingElement.id).where(DrawingElement.organization_id == org, DrawingElement.id.in_(wanted)))).scalars().all()) if wanted else set()
  out = []
  for m in measurements:
    cand = by_measurement.get(m.id)
    
    if cand is None:
      continue
    member = member_input(cand, m, sheets[m.sheet_id])
    if member is not None:
      member = replace(member, element_ids=tuple(e if e in present else None for e in member.element_ids))
      out.append(member)
  return tuple(sorted(out, key=lambda b: str(b.measurement_id)))

def _rcc_wall(cand: TakeoffCandidate) -> bool:
  return cand.category == "WALL" and (cand.facts or {}).get("construction") == "RCC"

def _site_formwork(cand: TakeoffCandidate) -> str | None:
  """The formwork category of a site item that is cast in concrete and shuttered (a tank, a coping, a chajja, a balcony slab), or None."""
  return FORMWORK_SITE.get((cand.facts or {}).get("site_kind")) if cand.category == "SITE" else None

def _tank_detail(p: dict) -> dict | None:
  """The outside height and the wall thickness a tank was accepted with, which its shuttering needs; None for a tank accepted before they were kept."""
  height, wall = _mm(p.get("height_mm")), _mm(p.get("wall_mm"))
  return {"height_mm": float(height), "wall_mm": float(wall)} if height is not None and wall is not None else None

async def load_formwork(session: AsyncSession, org: UUID, measurements: list, sheets: dict) -> tuple:
  """The accepted column, footing, slab, lintel, beam and stair candidates behind the confirmed measurements, with the size each measurement used, and the
  RCC walls measured as length x height x thickness. A member needs no position or scale here: the shuttering of a member comes from its size alone, and an
  RCC wall's from the net area its own measurement worked out."""
  ids = [m.id for m in measurements if m.quantity_mode in ("COUNT_X_VOLUME", "LENGTH_X_HEIGHT_X_THICKNESS")]
  if not ids:
    return ()
  cands = (await session.execute(
    select(TakeoffCandidate).where(TakeoffCandidate.organization_id == org, TakeoffCandidate.measurement_id.in_(ids),
      TakeoffCandidate.category.in_(FORMWORK_CATEGORIES + ("WALL", "SITE")), TakeoffCandidate.decision == "ACCEPTED"))).scalars().all()
  by_measurement = {c.measurement_id: c for c in cands if (c.category not in ("WALL", "SITE") or _rcc_wall(c) or _site_formwork(c))}
  wanted = [row_id(sheets[m.sheet_id].id, by_measurement[m.id].ckey, i)
    for m in measurements if m.id in by_measurement and by_measurement[m.id].category != "WALL" for i in range(len((m.geometry or {}).get("points") or []))]
  present = set((await session.execute(select(DrawingElement.id).where(DrawingElement.organization_id == org, DrawingElement.id.in_(wanted)))).scalars().all()) if wanted else set()
  out = []
  
  for m in measurements:
    cand = by_measurement.get(m.id)
    if cand is None:
      continue
    p = m.params or {}
    sheet = sheets[m.sheet_id]
    if cand.category == "WALL":
      thickness, height, run = _mm(p.get("thickness_mm")), _mm(p.get("height_mm")), _mm(((cand.facts or {}).get("length_cc_m") or 0) * 1000)
      if m.quantity_mode != "LENGTH_X_HEIGHT_X_THICKNESS" or thickness is None or height is None or run is None:
        continue
      
      out.append(tk.FormworkInput(
        measurement_id=m.id, candidate_id=cand.id, sheet_id=sheet.id, page_no=sheet.page_no, category="RCC_WALL", tag=cand.tag or cand.label, level_id=m.level_id,
        element_ids=(None,), count=1, length_mm=run, width_mm=thickness, depth_mm=height, confidence=_dec(cand.confidence) or Decimal(1),
        steel=clean_steel(p.get("steel"))))
      continue
    length, width, depth = _mm(p.get("length_mm")), _mm(p.get("width_mm")), _mm(p.get("depth_mm"))
    points = (m.geometry or {}).get("points") or []
    if length is None or width is None or depth is None or not points:
      continue
    site = _site_formwork(cand)
    if site is not None:
      ids_site = tuple(row_id(sheet.id, cand.ckey, i) for i in range(len(points)))
      out.append(tk.FormworkInput(
        measurement_id=m.id, candidate_id=cand.id, sheet_id=sheet.id, page_no=sheet.page_no, category=site, tag=cand.tag, level_id=m.level_id,
        element_ids=tuple(e if e in present else None for e in ids_site), count=len(points),
        length_mm=length, width_mm=width, depth_mm=depth, confidence=_dec(cand.confidence) or Decimal(1),
        site=_tank_detail(p) if site == "TANK" else None))
      continue
    
    ids_here = tuple(row_id(sheet.id, cand.ckey, i) for i in range(len(points)))
    positions = sheet_positions(cand, m) if len(points) else ()
    out.append(tk.FormworkInput(
      measurement_id=m.id, candidate_id=cand.id, sheet_id=sheet.id, page_no=sheet.page_no, category=cand.category, tag=cand.tag, level_id=m.level_id,
      element_ids=tuple(e if e in present else None for e in ids_here), count=len(points), length_mm=length, width_mm=width, depth_mm=depth,
      confidence=_dec(cand.confidence) or Decimal(1), steel=clean_steel(p.get("steel")) if cand.category in STEEL_FAMILIES else None,
      stair=stair_detail(cand, depth) if cand.category == "STAIR" else None,
      frame=view_key(cand, sheet) if positions else None, points_mm=positions,
      role=(cand.facts or {}).get("beam_role") if cand.category == "BEAM" else None))
  return tuple(sorted(out, key=lambda b: str(b.measurement_id)))

async def load_stored_alignments(session: AsyncSession, org: UUID, drawing_ids: list) -> dict:
  """What people decided about where views sit, per drawing: {drawing id: {"reference": key or None, "placements": {key: (dx, dy)}}}."""
  if not drawing_ids:
    return {}
  rows = (await session.execute(
    select(TakeoffViewAlignment).where(TakeoffViewAlignment.organization_id == org, TakeoffViewAlignment.drawing_id.in_(drawing_ids))
    .order_by(TakeoffViewAlignment.frame_key))).scalars().all()
  out: dict = {}
  for r in rows:
    d = out.setdefault(str(r.drawing_id), {"reference": None, "placements": {}})
    if r.role == "REFERENCE":
      d["reference"] = r.frame_key
    else:
      d["placements"][r.frame_key] = (float(r.dx_mm), float(r.dy_mm))
  return out

async def load_ranges(session: AsyncSession, org: UUID, measurements: list) -> tuple:
  ids = [m.id for m in measurements]
  if not ids:
    return ()
  cands = (await session.execute(
    select(TakeoffCandidate).where(TakeoffCandidate.organization_id == org, TakeoffCandidate.measurement_id.in_(ids),
      TakeoffCandidate.decision == "ACCEPTED"))).scalars().all()
  out = []
  
  for c in sorted(cands, key=lambda c: str(c.measurement_id)):
    ev = evidence_for(c)
    rg = ev["range"]
    out.append(tk.RangeInput(
      measurement_id=c.measurement_id, grade=str(ev["grade"]), bounded=bool(rg.get("bounded")), low_pct=rg.get("low_pct"), high_pct=rg.get("high_pct"),
      leaves_out=bool(rg.get("leaves_out")),
      drivers=tuple({"name": str(d["name"]), "basis": str(d["basis"]), "low_pct": d.get("low_pct"), "high_pct": d.get("high_pct")} for d in rg.get("drivers") or [])))
  return tuple(out)

async def load_takeoff_inputs(session: AsyncSession, org: UUID, drawing_ids: list[UUID]) -> tk.TakeoffInputs | None:
  if not drawing_ids:
    return None
  rows = (await session.execute(
    select(TakeoffMeasurement, TakeoffSheet)
    .join(TakeoffSheet, TakeoffSheet.id == TakeoffMeasurement.sheet_id)
    .where(TakeoffMeasurement.organization_id == org, TakeoffMeasurement.status == "CONFIRMED",
      TakeoffSheet.drawing_id.in_(list(drawing_ids)))
    .order_by(TakeoffMeasurement.id))).all()
  
  if not rows:
    return None
  measurements = [m for m, _ in rows]
  sheets = {s.id: s for _, s in rows}
  cal_ids = {m.calibration_id for m in measurements if m.calibration_id}
  cals = []
  
  if cal_ids:
    cals = list((await session.execute(
      select(TakeoffCalibration).where(TakeoffCalibration.organization_id == org,
        TakeoffCalibration.id.in_(cal_ids)))).scalars().all())
  formwork = await load_formwork(session, org, measurements, sheets)
  group_of_sheet = {s.id: str(s.drawing_id) for s in sheets.values()}
  stored = await load_stored_alignments(session, org, sorted({s.drawing_id for s in sheets.values()}, key=str))
  space, floors = await load_space(session, org, measurements, sheets)
  return tk.TakeoffInputs(
    sheets=tuple(sheet_input(s) for s in sorted(sheets.values(), key=lambda s: str(s.id))),
    calibrations=tuple(calibration_input(c, sheet_user_unit(sheets[c.sheet_id])) for c in sorted(cals, key=lambda c: str(c.id))
      if c.sheet_id in sheets),
    measurements=tuple(measurement_input(m) for m in sorted(measurements, key=lambda m: str(m.id))),
    members=await load_members(session, org, measurements, sheets),
    formwork=formwork, alignments=FV.build_alignments(formwork, group_of_sheet, stored), space=space, floors=floors,
    ranges=await load_ranges(session, org, measurements))

async def takeoff_drawing_ids(session: AsyncSession, org: UUID, project_id: UUID) -> set[UUID]:
  r = await session.execute(
    select(TakeoffSheet.drawing_id).distinct()
    .join(TakeoffMeasurement, TakeoffMeasurement.sheet_id == TakeoffSheet.id)
    .where(TakeoffMeasurement.organization_id == org, TakeoffMeasurement.project_id == project_id,
      TakeoffMeasurement.status == "CONFIRMED"))
  return {row[0] for row in r.all()}

class TakeoffRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def drawing(self, org: UUID, drawing_id: UUID) -> Drawing | None:
    return (await self.session.execute(
      select(Drawing).where(Drawing.id == drawing_id, Drawing.organization_id == org))).scalar_one_or_none()

  async def sheets(self, org: UUID, drawing_id: UUID) -> list[TakeoffSheet]:
    return list((await self.session.execute(
      select(TakeoffSheet).where(TakeoffSheet.organization_id == org, TakeoffSheet.drawing_id == drawing_id)
      .order_by(TakeoffSheet.page_no))).scalars().all())

  async def sheet(self, org: UUID, sheet_id: UUID, lock: bool = False) -> TakeoffSheet | None:
    stmt = select(TakeoffSheet).where(TakeoffSheet.id == sheet_id, TakeoffSheet.organization_id == org)
    if lock:
      stmt = stmt.with_for_update()
    return (await self.session.execute(stmt)).scalar_one_or_none()

  async def calibrations(self, org: UUID, sheet_ids: list[UUID]) -> list[TakeoffCalibration]:
    if not sheet_ids:
      return []
    return list((await self.session.execute(
      select(TakeoffCalibration).where(TakeoffCalibration.organization_id == org,
        TakeoffCalibration.sheet_id.in_(sheet_ids)).order_by(TakeoffCalibration.created_at, TakeoffCalibration.id)
    )).scalars().all())

  async def calibration(self, org: UUID, calibration_id: UUID, lock: bool = False) -> TakeoffCalibration | None:
    stmt = select(TakeoffCalibration).where(TakeoffCalibration.id == calibration_id, TakeoffCalibration.organization_id == org)
    if lock:
      stmt = stmt.with_for_update()
    return (await self.session.execute(stmt)).scalar_one_or_none()

  async def measurements(self, org: UUID, sheet_ids: list[UUID]) -> list[TakeoffMeasurement]:
    if not sheet_ids:
      return []
    return list((await self.session.execute(
      select(TakeoffMeasurement).where(TakeoffMeasurement.organization_id == org,
        TakeoffMeasurement.sheet_id.in_(sheet_ids)).order_by(TakeoffMeasurement.created_at, TakeoffMeasurement.id)
    )).scalars().all())

  async def measurements_for_calibration(self, org: UUID, calibration_id: UUID) -> list[TakeoffMeasurement]:
    return list((await self.session.execute(
      select(TakeoffMeasurement).where(TakeoffMeasurement.organization_id == org,
        TakeoffMeasurement.calibration_id == calibration_id))).scalars().all())

  async def measurements_for_sheet(self, org: UUID, sheet_id: UUID) -> list[TakeoffMeasurement]:
    return await self.measurements(org, [sheet_id])

  async def measurement(self, org: UUID, measurement_id: UUID, lock: bool = False) -> TakeoffMeasurement | None:
    stmt = select(TakeoffMeasurement).where(TakeoffMeasurement.id == measurement_id, TakeoffMeasurement.organization_id == org)
    if lock:
      stmt = stmt.with_for_update()
    return (await self.session.execute(stmt)).scalar_one_or_none()

  async def level_exists(self, org: UUID, level_id: UUID) -> bool:
    n = (await self.session.execute(
      select(func.count()).select_from(BuildingLevel).where(BuildingLevel.id == level_id,
        BuildingLevel.organization_id == org))).scalar_one()
    return bool(n)

  async def project_measurements(self, org: UUID, project_id: UUID) -> list[TakeoffMeasurement]:
    return list((await self.session.execute(
      select(TakeoffMeasurement).where(TakeoffMeasurement.organization_id == org,
        TakeoffMeasurement.project_id == project_id).order_by(TakeoffMeasurement.created_at, TakeoffMeasurement.id)
    )).scalars().all())

  async def latest_completed_run(self, org: UUID, project_id: UUID) -> CalculationRun | None:
    return (await self.session.execute(
      select(CalculationRun).where(CalculationRun.organization_id == org, CalculationRun.project_id == project_id,
        CalculationRun.status == "COMPLETED").order_by(CalculationRun.created_at.desc()).limit(1))).scalar_one_or_none()
