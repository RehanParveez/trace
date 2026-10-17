from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.modules.drawings_boq.models import DrawingElement, BuildingLevel, Drawing, DrawingFormat, TakeoffCandidate, TakeoffExtraction, TakeoffMeasurement, TakeoffSheet
from app.modules.drawings_boq.takeoff import register as R
from app.modules.drawings_boq.takeoff import repository as repo_mod
from app.modules.drawings_boq.takeoff import frame_views as FV
from app.modules.drawings_boq.takeoff import z_range as Z
from app.modules.drawings_boq.takeoff.evidence import tally as evidence_tally
from app.modules.drawings_boq.takeoff import ranges as RG
from app.modules.drawings_boq.takeoff.sheet_reason import sheet_reason
from app.modules.drawings_boq.takeoff.levels import view_level_id
from app.modules.drawings_boq.takeoff.prep_service import PrepService
from app.modules.drawings_boq.measurement_params import MeasurementParametersService
from sqlalchemy import delete, select
from app.core.exceptions import TraceException

MAX_ROWS = 20000
ROW_FIELDS = ("ifc_global_id", "ifc_type", "name", "raw_material_text", "unit", "quantity", "properties", "discipline", "structural_role",
  "classification_source", "classification_confidence", "quantity_source", "level_id", "length_mm", "width_mm", "height_mm", "thickness_mm",
  "area_mm2", "volume_mm3", "geometry_kind", "normalization_status", "normalization_issues", "type_mark", "type_name",
  "elevation_base_mm", "elevation_top_mm", "bbox_min_x_mm", "bbox_min_y_mm", "bbox_min_z_mm", "bbox_max_x_mm", "bbox_max_y_mm", "bbox_max_z_mm", "placement")
CLEARED = ("length_mm", "width_mm", "height_mm", "thickness_mm", "area_mm2", "volume_mm3")

def _is_pdf_row_clause():
  src = DrawingElement.properties["source"].as_string()
  return src == R.SOURCE

class RegisterService:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def _drawing(self, org: UUID, drawing_id: UUID) -> Drawing:
    drawing = (await self.session.execute(select(Drawing).where(Drawing.id == drawing_id, Drawing.organization_id == org))).scalar_one_or_none()
    if drawing is None:
      raise TraceException("Drawing not found.", status_code=404, code="DRAWING_NOT_FOUND")
    if drawing.format != DrawingFormat.PDF:
      raise TraceException("The PDF register is for PDF drawings. IFC drawings fill their register when they are read.", status_code=422,
        code="DRAWING_NOT_PDF")
    return drawing

  async def sync_drawing(self, org: UUID, drawing_id: UUID) -> dict:
    
    drawing = await self._drawing(org, drawing_id)
    sheets = list((await self.session.execute(select(TakeoffSheet).where(TakeoffSheet.organization_id == org, TakeoffSheet.drawing_id == drawing_id)
      .order_by(TakeoffSheet.page_no))).scalars().all())
    by_sheet = {s.id: s for s in sheets}
    cands = list((await self.session.execute(select(TakeoffCandidate).where(TakeoffCandidate.organization_id == org,
      TakeoffCandidate.sheet_id.in_(list(by_sheet) or [None])).order_by(TakeoffCandidate.sheet_id, TakeoffCandidate.category,
      TakeoffCandidate.label, TakeoffCandidate.id))).scalars().all())
    mids = [c.measurement_id for c in cands if c.measurement_id]
    measurements: dict = {}
    
    if mids:
      for m in (await self.session.execute(select(TakeoffMeasurement).where(TakeoffMeasurement.organization_id == org,
          TakeoffMeasurement.id.in_(mids)))).scalars().all():
        measurements[m.id] = {"id": m.id, "status": m.status, "computed": m.computed or {}}
    level_ids = {s.level_id for s in sheets if s.level_id} | {lv for lv in (view_level_id(c) for c in cands) if lv}
    levels: dict = {}
    floor_of: dict = {}

    if level_ids:
      level_rows = (await self.session.execute(select(BuildingLevel).where(BuildingLevel.organization_id == org,
        BuildingLevel.id.in_(list(level_ids))))).scalars().all()
      levels = {lv.id: lv.name for lv in level_rows}
      floor_of = {lv.id: (lv.ifc_storey_id or "").removeprefix("PDF:") for lv in level_rows}
    floors, footing = await self._datums(org, drawing)
    rows = R.build_rows(cands, by_sheet, measurements, levels, await self._frame_positions(org, drawing_id), floors, floor_of, footing)
    
    if len(rows) > MAX_ROWS:
      raise TraceException("This drawing has too many items to list.", status_code=422, code="REGISTER_TOO_LARGE")
    existing = {e.id: e for e in (await self.session.execute(select(DrawingElement).where(DrawingElement.drawing_id == drawing_id,
      DrawingElement.organization_id == org, _is_pdf_row_clause()))).scalars().all()}
    added = updated = 0
    keep: set = set()
    
    for row in rows:
      keep.add(row["id"])
      cur = existing.get(row["id"])
      if cur is None:
        self.session.add(DrawingElement(id=row["id"], drawing_id=drawing_id, organization_id=org,
          **{k: row.get(k) for k in ROW_FIELDS if k in row or k in ("quantity",)}))
        added += 1
        continue
    
      for k in ROW_FIELDS:
        setattr(cur, k, row.get(k))
        
      for k in CLEARED:
        if k not in row:
          setattr(cur, k, None)
      updated += 1
    gone = [i for i in existing if i not in keep]
    
    if gone:
      await self.session.execute(delete(DrawingElement).where(DrawingElement.organization_id == org, DrawingElement.drawing_id == drawing_id,
        DrawingElement.id.in_(gone)))
    await self.session.flush()
    read_ids = {x for x in (await self.session.execute(select(TakeoffExtraction.sheet_id).where(TakeoffExtraction.organization_id == org,
      TakeoffExtraction.sheet_id.in_(list(by_sheet) or [None])))).scalars().all()}
    per_sheet: dict = {}
    for r in rows:
      sid = r["properties"]["_pdf"]["sheet_id"]
      per_sheet[sid] = per_sheet.get(sid, 0) + 1
    waiting: list = []
    set_aside: list = []
    sheet_status: list = []
    
    for sh in sheets:
      issue = (sh.prep_meta or {}).get("read_issue") or {}
      title = (sh.prep_meta or {}).get("title") or {}
      if sh.id in read_ids:
        status = "READ"
      elif issue.get("severity") == "INFO":
        status = "SET_ASIDE"
      elif sh.prep_status != "READY":
        status = "NOT_PREPARED"
      else:
        status = "WAITING"
      reason = "NOT_PREPARED" if sh.prep_status != "READY" else "NOT_READ"
      why = sheet_reason(status, sh.page_no, sh.prep_status, sh.prep_error, issue)
      code, message, action, severity = why["code"], why["message"], why["action"], issue.get("severity")
      
      if status in ("WAITING", "NOT_PREPARED"):
        waiting.append({"page_no": sh.page_no, "sheet_id": str(sh.id), "error": sh.prep_error, "reason": reason, "code": code, "message": message, "action": action})
      elif status == "SET_ASIDE":
        set_aside.append({"page_no": sh.page_no, "sheet_id": str(sh.id), "code": code, "message": message})
      sheet_status.append({"page_no": sh.page_no, "sheet_id": str(sh.id), "title": title.get("title") or sh.label, "level": levels.get(sh.level_id) if sh.level_id else None,
        "status": status, "items": per_sheet.get(str(sh.id), 0), "code": code, "message": message if status != "READ" else None, "severity": severity,
        "action": action, "composite": bool(title.get("composite"))})
    by_cat: dict = {}
    
    for r in rows:
      by_cat[r["ifc_type"]] = by_cat.get(r["ifc_type"], 0) + 1
    return {"drawing_id": drawing_id, "total": len(rows), "added": added, "updated": updated, "removed": len(gone), "by_type": by_cat,
      "sheets": len(sheets), "sheets_read": len(read_ids), "waiting": waiting, "set_aside": set_aside, "sheet_status": sheet_status,
      "measured": sum(1 for r in rows if r["properties"]["_pdf"]["mode"] == "PDF_MEASURED"),
      "needs_review": sum(1 for r in rows if r["normalization_status"] != "VALID"),
      "decisions": len({r["properties"]["_pdf"]["candidate_id"] for r in rows if r["normalization_status"] != "VALID"}),
      "evidence": evidence_tally(rows), "totals": RG.totals(rows), "source_mix": RG.source_mix(rows)}

  async def floor_datums(self, org: UUID, drawing_id: UUID) -> dict:
    """The floors of a drawing with the level of each, as the register places members in height, and the natural ground and footing level used for footings.
    {"floors": [rows for the screen], "datum": what z = 0 is, "footing": {...}}."""
    drawing = await self._drawing(org, drawing_id)
    prepared = await PrepService(self.session).drawing_floor_heights(org, drawing_id)
    floors = Z.build_floors(prepared["heights"], prepared["floor_keys"])
    
    footing = await self._footing_level(org, drawing, floors, prepared["levels_mm"])
    return {"drawing_id": drawing_id, "datum": Z.datum_of(floors), "floors": Z.floors_report(floors, prepared["floor_keys"], prepared["heights"]),
      "footing": {"ngl_mm": footing.ngl_mm, "ngl_source": footing.ngl_source if footing.ngl_mm is not None else None,
        "bottom_below_ngl_mm": footing.bottom_below_ngl_mm, "usable": footing.usable}}

  async def _datums(self, org: UUID, drawing) -> tuple:
    prepared = await PrepService(self.session).drawing_floor_heights(org, drawing.id)
    floors = Z.build_floors(prepared["heights"], prepared["floor_keys"])
    return floors, await self._footing_level(org, drawing, floors, prepared["levels_mm"])

  async def _footing_level(self, org: UUID, drawing, floors: dict, levels_mm: list) -> Z.FootingLevel:
    """Natural ground level and the footing level below it. The ground level is the site assumption a person saved (how far natural ground lies below the
    finished floor level of the ground floor), else the lowest level mark printed below the ground floor when the drawing's own zero is the datum; the footing
    level is the answer a person gave for the footings."""
    stored = await MeasurementParametersService(self.session).stored_for_run(org, drawing.project_id)
    below = float(stored["footing_bottom_below_ngl_mm"]) if stored.get("footing_bottom_below_ngl_mm") is not None else None
    ground, datum = floors.get("GROUND"), Z.datum_of(floors)
    
    if stored.get("ngl_below_ffl_mm") is not None and ground is not None:
      return Z.FootingLevel(round(ground.level_mm - float(stored["ngl_below_ffl_mm"]), 1), below, Z.TYPED_NGL, datum)
    return Z.FootingLevel(Z.ngl_from_marks(floors, levels_mm), below, Z.MARK_NGL, datum)

  async def _frame_positions(self, org: UUID, drawing_id: UUID) -> dict:
    """{(measurement id, instance): where the mark sits on the building frame} for the confirmed measurements of this drawing, so the register carries the positions the
    engine used. Nothing is written for a mark whose view is not placed."""
    inputs = await repo_mod.load_takeoff_inputs(self.session, org, [drawing_id])
    if inputs is None or not inputs.formwork:
      return {}
    group = str(drawing_id)
    stored = (await repo_mod.load_stored_alignments(self.session, org, [drawing_id])).get(group)
    return FV.register_positions(inputs.formwork, {f.sheet_id: group for f in inputs.formwork}, {group: stored} if stored else None)

  async def sync_and_commit(self, org: UUID, drawing_id: UUID) -> dict:
    out = await self.sync_drawing(org, drawing_id)
    await self.session.commit()
    return out
