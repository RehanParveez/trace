from __future__ import annotations
from app.engine.measure import takeoff as tk
from app.modules.drawings_boq.models import TakeoffSheet, TakeoffCalibration, BuildingLevel, CalculationRun, Drawing, TakeoffMeasurement
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
  return tk.TakeoffInputs(
    sheets=tuple(sheet_input(s) for s in sorted(sheets.values(), key=lambda s: str(s.id))),
    calibrations=tuple(calibration_input(c, sheet_user_unit(sheets[c.sheet_id])) for c in sorted(cals, key=lambda c: str(c.id))
      if c.sheet_id in sheets),
    measurements=tuple(measurement_input(m) for m in sorted(measurements, key=lambda m: str(m.id))))

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