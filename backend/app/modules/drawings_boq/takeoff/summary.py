from __future__ import annotations
from collections import defaultdict
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.projects.repository import ProjectRepository
from sqlalchemy import select
from app.modules.drawings_boq.models import TakeoffCalibration, Drawing, TakeoffSheet, TakeoffMeasurement, TakeoffExtraction
from app.modules.drawings_boq.takeoff import readability
from app.core.exceptions import TraceException

def build_summary(drawings, sheets, calibrations, measurements, extractions=None) -> list[dict]:
    
  by_drawing: dict = defaultdict(list)
  for s in sheets:
    by_drawing[s.drawing_id].append(s)
  calibrated = {c.sheet_id for c in calibrations if c.usable and c.is_default}
  sheet_drawing = {s.id: s.drawing_id for s in sheets}
  draft: dict = defaultdict(int)
  confirmed: dict = defaultdict(int)
  for m in measurements:
    d = sheet_drawing.get(m.sheet_id)
    if d is None:
      continue
    if m.status == "CONFIRMED":
      confirmed[d] += 1
    else:
      draft[d] += 1
  read_by: dict = defaultdict(list)
  page_of = {s.id: s.page_no for s in sheets}
  for e in extractions or []:
    d = sheet_drawing.get(e.sheet_id)
    if d is not None:
      read_by[d].append({"page_no": page_of.get(e.sheet_id), "stats": e.stats, "notes": e.notes, "scale_unverified": e.scale_unverified})
  rows = []
  for d in drawings:
    own = by_drawing.get(d.id)
    if not own:
      continue
    rows.append({
      "drawing_id": d.id, "original_filename": d.original_filename, "revision_label": d.revision_label,
      "is_current_revision": bool(d.is_current_revision), "sheets": len(own),
      "prepared_sheets": sum(1 for s in own if s.prep_status == "READY"),
      "calibrated_sheets": sum(1 for s in own if s.id in calibrated),
      "draft": draft.get(d.id, 0), "confirmed": confirmed.get(d.id, 0),
      **({"readability": readability.drawing_status(read_by.get(d.id, []))} if extractions is not None else {}),
    })
  rows.sort(key=lambda r: (r["original_filename"].lower(), str(r["drawing_id"])))
  return rows

async def project_takeoff_summary(session: AsyncSession, org: UUID, project_id: UUID) -> dict:
  if await ProjectRepository(session).get_by_id_and_org(project_id, org) is None:
    raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")
  sheets = list((await session.execute(
    select(TakeoffSheet).where(TakeoffSheet.organization_id == org, TakeoffSheet.project_id == project_id))).scalars().all())
  
  if not sheets:
    return {"drawings": []}
  drawing_ids = {s.drawing_id for s in sheets}
  drawings = list((await session.execute(
    select(Drawing).where(Drawing.organization_id == org, Drawing.id.in_(drawing_ids)))).scalars().all())
  sheet_ids = [s.id for s in sheets]
  calibrations = list((await session.execute(
    select(TakeoffCalibration).where(TakeoffCalibration.organization_id == org, TakeoffCalibration.sheet_id.in_(sheet_ids)))).scalars().all())
  measurements = list((await session.execute(
    select(TakeoffMeasurement).where(TakeoffMeasurement.organization_id == org, TakeoffMeasurement.sheet_id.in_(sheet_ids)))).scalars().all())
  extractions = list((await session.execute(
    select(TakeoffExtraction).where(TakeoffExtraction.organization_id == org, TakeoffExtraction.sheet_id.in_(sheet_ids)))).scalars().all())
  return {"drawings": build_summary(drawings, sheets, calibrations, measurements, extractions)}