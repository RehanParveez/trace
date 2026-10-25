from __future__ import annotations
from datetime import datetime, timezone
import tempfile
from app.modules.drawings_boq.takeoff.prep.extract import PdfOpenError, extract_page, open_document
from app.modules.drawings_boq.takeoff.service import TakeoffService, build_calibration
from app.core.exceptions import TraceException
from app.modules.drawings_boq.takeoff.prep_repository import PrepRepository
from app.modules.drawings_boq.models import BuildingLevel, TakeoffCalibration, TakeoffCandidate
from sqlalchemy import select
from decimal import Decimal
import asyncio
import logging
import re
from uuid import UUID, uuid4
import math
import os
import time
from app.engine.measure import takeoff as tk
from app.engine.measure import readings as QS
from app.modules.drawings_boq.takeoff.decisions import store as decided
from app.modules.audit.models import AuditAction
from app.modules.drawings_boq.takeoff import repository as repo_mod
from app.modules.drawings_boq.takeoff.prep import census, facts as drawing_facts, schedules as drawing_schedules
from app.modules.drawings_boq.takeoff.prep.storeys import storey_heights
from app.modules.drawings_boq.takeoff.levels import ensure_level, level_spec
from app.modules.drawings_boq.takeoff.prep import details
from app.modules.drawings_boq.takeoff.prep import beam_details
from app.modules.drawings_boq.takeoff.prep import tank_details
from app.modules.drawings_boq.takeoff.extract import electrical as electrical_reader
from app.modules.drawings_boq.takeoff.prep import footing_sections, units as unit_reader
from app.modules.drawings_boq.takeoff.prep import checks as checks_mod
from app.modules.drawings_boq.takeoff.prep import picture_checks, reader_status
from app.modules.drawings_boq.takeoff.prep.analyze import ANALYSIS_VERSION, analyze_page
from app.modules.drawings_boq.takeoff.prep.codec import encode_index
from app.modules.drawings_boq.takeoff.sheet_reason import failure_text
from app.shared.storage import download_to_path

log = logging.getLogger(__name__)

SNAP_VERIFY_TOL_PT = 0.12
TAG_VERIFY_RADIUS_PT = 14.0
STANDARD_WALLS_MM = (75, 100, 115, 125, 150, 200, 230, 250, 300, 343, 350, 450)
MAX_VECTOR_SEGMENTS = 60000

def _now() -> datetime:
  return datetime.now(timezone.utc)

def _fmt(v: float, places: int = 3) -> float:
  return round(float(v), places)

def compact_scale(full: dict) -> dict:
  declared = full.get("declared") or {}
  measured = full.get("measured") or {}
  return {
    "version": full.get("version"), "agreement": full.get("agreement"), "recommended": full.get("recommended"),
    "declared": declared.get("primary"), "multi_scale": bool(declared.get("multi_scale")), "not_to_scale": bool(declared.get("not_to_scale")),
    "clusters": measured.get("clusters") or [], "dimensions_read": measured.get("pairs_found", 0),
    "dimension_mismatches": len(measured.get("mismatches") or []), "notes": full.get("notes") or [],
    "paper": full.get("paper"), "units_hint": full.get("units_hint"),
  }

def _download_bytes(storage_key: str) -> bytes:
  with tempfile.TemporaryDirectory() as tmp:
    path = os.path.join(tmp, "drawing.pdf")
    download_to_path(storage_key, path)
    with open(path, "rb") as handle:
      return handle.read()

def _open(contents: bytes):
  try:
    return open_document(contents)
  except PdfOpenError as exc:
    raise TraceException(exc.message, status_code=422, code=exc.code)

def _analyze_one(doc, page_no: int, user_unit: float, budget_s: float):
  raw = extract_page(doc, page_no - 1, budget_s=budget_s)
  result = analyze_page(raw, user_unit, budget_s=max(5.0, budget_s / 2))
  _read_details(doc, page_no, raw, result)
  return result, raw.stats

def _read_details(doc, page_no: int, raw, result) -> None:
  """Column details, beam sections and water tank drawings on the sheet: their marks, and (when the character reader is installed) the sizes written beside
  them. This is the one place the PDF is still open, so the pictures are read here and only their result is stored. Each reader fails on its own."""
  try:
    page = doc[page_no - 1]
  except Exception:
    result.meta["details_reader"] = "FAILED"
    return
  size = page.get_size()
  try:
    found = details.read_column_details(result.index.words, result.index, page, size, raw.cropbox, raw.rotation)
    if found["details"]:
      result.meta["details"] = found["details"]
      result.meta["details_reader"] = found["ocr"]
  except Exception:
    result.meta["details_reader"] = "FAILED"
  try:
    beams = beam_details.read_beam_details(result.index.words, result.index, page, size, raw.cropbox, raw.rotation)
    if beams["details"]:
      result.meta["beam_details"] = beams["details"]
      result.meta["beam_details_reader"] = beams["ocr"]
  except Exception:
    result.meta["beam_details_reader"] = "FAILED"
  try:
    tanks = tank_details.read_tank_details(result.index.words, page, size, raw.cropbox, raw.rotation)
    if tanks["details"]:
      result.meta["tank_details"] = tanks["details"]
      result.meta["tank_details_reader"] = tanks["ocr"]
  except Exception:
    result.meta["tank_details_reader"] = "FAILED"
  try:
    legend = electrical_reader.read_legend_rows(page, result.index.words, identity=result.meta.get("identity"))
    if legend:
      result.meta["electrical_legend"] = legend
  except Exception:
    result.meta["electrical_reader"] = "FAILED"
  try:
    sections = footing_sections.read(result.index, result.index.words)
    if sections:
      result.meta["footing_sections"] = sections
  except Exception:
    result.meta["footing_sections_reader"] = "FAILED"

class PrepService:
  def __init__(self, session):
    self.session = session
    self.core = TakeoffService(session)
    self.repo = self.core.repo
    self.prep = PrepRepository(session)

  async def _sheet(self, org: UUID, sheet_id: UUID, lock: bool = False):
    return await self.core._sheet(org, sheet_id, lock=lock)

  async def _index(self, org: UUID, sheet_id: UUID):
    index = await self.prep.load_index(org, sheet_id)
    if index is None:
      raise TraceException("Prepare this sheet first; its geometry has not been read yet.", status_code=409, code="SHEET_NOT_PREPARED")
    return index

  async def _mm_per_pt(self, org: UUID, sheet, calibration_id: UUID | None = None) -> Decimal | None:
    cal = None
    if calibration_id is not None:
      cal = await self.core._calibration(org, calibration_id)
      if cal.sheet_id != sheet.id:
        raise TraceException("That calibration belongs to another sheet.", status_code=422, code="CALIBRATION_WRONG_SHEET")
    else:
      cal = await self.core._default_calibration(org, sheet.id)
    if cal is None or not cal.usable:
      return None
    ev = tk.evaluate_calibration(repo_mod.calibration_input(cal, repo_mod.sheet_user_unit(sheet)))
    return ev.mm_per_pt if ev.usable else None

  @staticmethod
  def _stale(sheet) -> bool:
    return (sheet.prep_meta or {}).get("analysis_version") != ANALYSIS_VERSION

  async def prepare_drawing(self, org: UUID, drawing_id: UUID, user_id: UUID, payload) -> dict:
    started = time.monotonic()
    drawing = await self.core._pdf_drawing(org, drawing_id)
    sheets = await self.repo.sheets(org, drawing_id)
    if not sheets:
      await self.core.sync_sheets(org, drawing_id, user_id)
      sheets = await self.repo.sheets(org, drawing_id)
    wanted = set(payload.sheet_ids) if payload.sheet_ids else None
    if wanted is not None:
      unknown = wanted - {s.id for s in sheets}
      if unknown:
        raise TraceException("Some sheets do not belong to this drawing.", status_code=422, code="SHEET_NOT_IN_DRAWING")
    candidates = [s for s in sheets if wanted is None or s.id in wanted]
    todo = [s for s in candidates if payload.force or s.prep_status != "READY" or self._stale(s)]
    skipped = [s.id for s in candidates if s not in todo]
    prepared: list = []
    failed: list = []
    if todo:
      contents = await asyncio.to_thread(_download_bytes, drawing.storage_key)
      doc = await asyncio.to_thread(_open, contents)
      try:
        for sheet in todo:
          if time.monotonic() - started > payload.budget_seconds and prepared:
            break
          try:
            ok = await self._prepare_one(org, user_id, drawing, sheet, doc, float(payload.budget_seconds))
          except TraceException as exc:
            ok = False
            await self._mark_failed(org, sheet.id, exc.message)
          if ok:
            prepared.append(sheet.id)
          else:
            failed.append({"sheet_id": str(sheet.id), "page_no": sheet.page_no, "message": sheet.prep_error or "This sheet could not be read."})
      finally:
        try:
          doc.close()
        except Exception:
          pass
    refreshed = await self.repo.sheets(org, drawing_id)
    remaining = sum(1 for s in refreshed if (wanted is None or s.id in wanted) and (s.prep_status != "READY" or self._stale(s)) and s.prep_status != "FAILED")
    return {"drawing_id": drawing_id, "prepared": prepared, "skipped": skipped, "failed": failed, "remaining": remaining,
      "elapsed_seconds": round(time.monotonic() - started, 2), "sheets": refreshed}

  async def prepare_sheet(self, org: UUID, sheet_id: UUID, user_id: UUID, force: bool = False):
    sheet = await self._sheet(org, sheet_id)
    drawing = await self.core._pdf_drawing(org, sheet.drawing_id)
    if not force and sheet.prep_status == "READY" and not self._stale(sheet):
      return sheet
    contents = await asyncio.to_thread(_download_bytes, drawing.storage_key)
    doc = await asyncio.to_thread(_open, contents)
    try:
      ok = await self._prepare_one(org, user_id, drawing, sheet, doc, 60.0)
    finally:
      try:
        doc.close()
      except Exception:
        pass
    if not ok:
      raise TraceException(sheet.prep_error or "This sheet could not be read.", status_code=422, code="SHEET_PREP_FAILED")
    return await self._sheet(org, sheet_id)

  async def _mark_failed(self, org: UUID, sheet_id: UUID, message: str) -> None:
    sheet = await self._sheet(org, sheet_id, lock=True)
    sheet.prep_status, sheet.prep_error = "FAILED", (message or "")[:500]
    await self.session.flush()
    await self.session.commit()

  async def _prepare_one(self, org: UUID, user_id: UUID, drawing, sheet, doc, budget_s: float) -> bool:
    user_unit = float(repo_mod.sheet_user_unit(sheet))
    try:
      result, stats = await asyncio.to_thread(_analyze_one, doc, sheet.page_no, user_unit, min(budget_s, 40.0))
    except Exception as exc:  
      log.exception("Sheet %s (page %s) could not be prepared", sheet.id, sheet.page_no)
      await self._mark_failed(org, sheet.id, failure_text(sheet.page_no, exc))
      return False
  
    payload = await asyncio.to_thread(encode_index, result.index)
    full = result.detected_scale
    locked = await self._sheet(org, sheet.id, lock=True)
    old_meta = dict(locked.prep_meta or {})
    meta = {**result.meta, "prepared_at": _now().isoformat()}
    for keep in ("user_unit", "kind_source"):
      if keep in old_meta:
        meta[keep] = old_meta[keep]
    if (old_meta.get("identity") or {}).get("basis") == "PERSON":
      if meta.get("identity") is not None:
        meta["identity_read"] = meta["identity"]
      meta["identity"] = old_meta["identity"]
    kind_changed = False
    if old_meta.get("kind_source") != "USER" and locked.content_kind != result.content_kind:
      locked.content_kind, kind_changed = result.content_kind, True
    locked.detected_scale = compact_scale(full)
    locked.prep_meta = meta
    
    locked.text_chars, locked.vector_ops = result.text_chars, result.vector_ops
    locked.prep_status, locked.prep_error = "READY", None
    primary = (full.get("declared") or {}).get("primary")
    if not locked.scale_text and primary:
      locked.scale_text = str(primary.get("text"))[:60]
    title = result.meta.get("title") or {}
    if not locked.label and title.get("composite"):
      locked.label = "Several drawings on one sheet"
    elif not locked.label and (title.get("title") or title.get("sheet_no")):
      locked.label = " ".join(x for x in (title.get("sheet_no"), title.get("title")) if x)[:200]
    
    if locked.level_id is None and title.get("level_hint") and not title.get("composite"):
      locked.level_id = await ensure_level(self.session, org, locked.drawing_id, title.get("level_hint"))
    await self.prep.save(org, locked.id, ANALYSIS_VERSION, payload,
        {"segments": len(result.index.kinds), "rings": len(result.index.rings), "words": len(result.index.words)}, full)
    await self.session.flush()
    if kind_changed:
      await self.core._refresh_sheet_measurements(org, locked)
    await self.core._log(org, user_id, locked.id, AuditAction.UPDATE,
        f"Read sheet {locked.page_no} for takeoff ({result.content_kind.lower()}, scale check: {str(full.get('agreement')).lower().replace('_', ' ')})")
    await self.session.commit()
    return True

  async def drawing_facts(self, org: UUID, drawing_id: UUID) -> dict:
    """What the drawing's own words say (slab thickness, steel grade, concrete mix, covers, bearing capacity, level marks), gathered across its read sheets."""
    await self.core._pdf_drawing(org, drawing_id)
    sheets = await self.repo.sheets(org, drawing_id)
    read = [{"page_no": s.page_no, "label": s.label, "facts": (s.prep_meta or {}).get("facts")} for s in sheets if (s.prep_meta or {}).get("facts") is not None]
    out = {"drawing_id": drawing_id, "sheets_read": len(read), "sheets_total": len(sheets), **drawing_facts.gather(read)}
    out["schedule"] = drawing_schedules.gather(self._schedule_sheets(sheets))
    suggested = (out.get("suggest") or {}).get("wall_height")
    
    keys = [a["key"] for a in out["schedule"]["areas"] if a.get("kind") == "FLOOR"]
    heights = drawing_facts.floor_heights(keys, out["ladder"], suggested["slab_mm"] if suggested else None)
    floor_keys = self._floor_keys(sheets)
    printed = storey_heights(floor_keys, out.get("storeys"))
    heights = {**heights, **printed}
    out["suggest"]["wall_height_by_floor"] = heights
    structure = await self._structure(org, sheets)
    out["views"] = structure["views"]
    out["structure"] = structure["levels"]
    out["details"], out["details_reader"], out["checks"] = await self._detail_checks(org, sheets)
    out["checks"] = checks_mod.storey_checks(out.get("storeys"), printed, {k: (level_spec(k) or (k,))[0] for k in floor_keys}) + out["checks"]
    plan_notes = [{"mm": v["slab_note_mm"], "pages": [v["page_no"]]} for v in structure["views"] if v.get("structural") and not v.get("foundation") and v.get("slab_note_mm")]
    out["checks"] = out["checks"] + checks_mod.slab_checks(drawing_facts.slab_values(out["items"]), plan_notes)
    out["checks"] = out["checks"] + checks_mod.lintel_checks(out["schedule"].get("lintels") or [], out["schedule"].get("tie_band"))
    out["beam_details"], out["tank_details"] = picture_checks.rows([{"page_no": s.page_no, "beam_details": (s.prep_meta or {}).get("beam_details"),
      "tank_details": (s.prep_meta or {}).get("tank_details")} for s in sheets])
    out["picture_reader"] = reader_status.status() if (out["beam_details"] or out["tank_details"]) else None
    out["checks"] = out["checks"] + picture_checks.checks(out["beam_details"], out["tank_details"], out["picture_reader"] or reader_status.status())
    out["floors"] = await self._floor_checks(org, sheets, out["schedule"]["areas"], heights, structure["levels"])
    return out

  @staticmethod
  def _floor_keys(sheets: list) -> list:
    """The floors the drawing shows, lowest first: the floor of each single-floor sheet and of each structural framing plan on a composite sheet."""
    keys: set = set()
    for s in sheets:
      meta = s.prep_meta or {}
      title = meta.get("title") or {}
      if title.get("level_hint") and not title.get("composite"):
        keys.add(title["level_hint"])
      for v in meta.get("views") or []:
        if v.get("structural") and v.get("level_hint") and not v.get("foundation"):
          keys.add(v["level_hint"])
    return [k for k in drawing_facts.FLOOR_ORDER if k in keys]

  async def drawing_storey_heights(self, org: UUID, drawing_id: UUID) -> dict:
    """The clear storey height of each floor, from the building sections printed on any sheet of the drawing: {floor key: {clear_mm, ...}}."""
    sheets = await self.repo.sheets(org, drawing_id)
    read = [{"page_no": s.page_no, "label": s.label, "facts": (s.prep_meta or {}).get("facts")} for s in sheets if (s.prep_meta or {}).get("facts") is not None]
    return storey_heights(self._floor_keys(sheets), drawing_facts.gather(read).get("storeys"))

  async def drawing_floor_heights(self, org: UUID, drawing_id: UUID) -> dict:
    """What the drawing prints about the heights of its floors, for placing members in height: {"heights": {floor key: {clear_mm, floor_to_floor_mm, basis,
    level_mm}}, "floor_keys": the floors the drawing shows, "levels_mm": the level marks printed on the elevations}. The same heights the Facts tab offers for
    walls, section heights over level marks over the typical floor-to-floor height; level_mm is the printed level of the floor where there is one."""
    sheets = await self.repo.sheets(org, drawing_id)
    read = [{"page_no": s.page_no, "label": s.label, "facts": (s.prep_meta or {}).get("facts")} for s in sheets if (s.prep_meta or {}).get("facts") is not None]
    gathered = drawing_facts.gather(read)
    schedule = drawing_schedules.gather(self._schedule_sheets(sheets))
    suggested = (gathered.get("suggest") or {}).get("wall_height")
    keys = [a["key"] for a in schedule["areas"] if a.get("kind") == "FLOOR"]
    heights = drawing_facts.floor_heights(keys, gathered["ladder"], suggested["slab_mm"] if suggested else None)
    
    floor_keys = self._floor_keys(sheets)
    heights = {**heights, **storey_heights(floor_keys, gathered.get("storeys"))}
    levels = (gathered.get("ladder") or {}).get("levels_mm") or []
    return {"heights": heights, "floor_keys": floor_keys, "levels_mm": [float(x) for x in levels]}

  async def drawing_slab_values(self, org: UUID, drawing_id: UUID) -> list:
    """The slab thicknesses printed for slabs in general anywhere on the drawing: [{mm, count, pages, scopes}], most often printed first."""
    sheets = await self.repo.sheets(org, drawing_id)
    read = [{"page_no": s.page_no, "label": s.label, "facts": (s.prep_meta or {}).get("facts")} for s in sheets if (s.prep_meta or {}).get("facts") is not None]
    return drawing_facts.slab_values(drawing_facts.gather(read)["items"])

  async def drawing_spec_facts(self, org: UUID, drawing_id: UUID) -> dict:
    from app.modules.drawings_boq.takeoff.extract import spec_facts
    sheets = await self.repo.sheets(org, drawing_id)
    read = [{"page_no": s.page_no, "label": s.label, "facts": (s.prep_meta or {}).get("facts")} for s in sheets if (s.prep_meta or {}).get("facts") is not None]
    return spec_facts.build(drawing_facts.gather(read)["items"])

  async def _detail_checks(self, org: UUID, sheets: list) -> tuple:
    """The column details read on the drawing's sheets, and the checks between them and the plans."""
    
    found, reader = [], None
    for s in sheets:
      meta = s.prep_meta or {}
      for d in meta.get("details") or []:
        found.append({"mark": d["mark"], "caption": d.get("caption"), "page_no": s.page_no, "read": d.get("read") or "NONE", "w_in": d.get("w_in"), "h_in": d.get("h_in")})
      if meta.get("details"):
        got = meta.get("details_reader")
        reader = got if reader in (None, "OK") else reader
        
    if not found:
      return [], None, []
    rows = (await self.session.execute(select(TakeoffCandidate).where(TakeoffCandidate.organization_id == org,
      TakeoffCandidate.sheet_id.in_([s.id for s in sheets]), TakeoffCandidate.decision != "REJECTED", TakeoffCandidate.category == "COLUMN"))).scalars().all()
    plan_marks, mismatches, seen = set(), [], set()
    for c in rows:
      tag = c.tag or ""
      plan_marks.add(re.sub(r"[\s\-]", "", tag).upper())
      for n in c.notes or []:
        if n.get("code") == "COLUMN_PLAN_VS_DETAIL" and tag not in seen:
          seen.add(tag)
          d, t = n.get("drawn_mm") or [], n.get("detail_mm") or []
          if len(d) == 2 and len(t) == 2:
            mismatches.append({"tag": tag, "drawn_in": [round(v / 25.4, 1) for v in d], "detail_in": [round(v / 25.4, 1) for v in t]})
    return found, reader, checks_mod.column_checks(found, reader, {m for m in plan_marks if m}, mismatches)

  async def _structure(self, org: UUID, sheets: list) -> dict:
    """The drawings of every sheet that shows several (a structural sheet with foundation and framing plans), and what was found in each of them:
    columns, footings and beam marks per floor, with the slab note and panel count the plan prints. These never count as a floor having been read."""
    shown, by_sheet = [], {}
    for s in sheets:
      vs = (s.prep_meta or {}).get("views") or []
      if sum(1 for v in vs if v.get("structural")) >= 2:
        by_sheet[s.id] = s
        for v in vs:
          if v.get("plan") or v.get("structural"):
            shown.append({"page_no": s.page_no, "key": v["key"], "kind": v.get("kind"), "caption": v.get("caption"), "level_hint": v.get("level_hint"),
              "structural": bool(v.get("structural")), "foundation": bool(v.get("foundation")), "scale_ratio": (v.get("scale") or {}).get("ratio"),
              "scale_support": (v.get("scale") or {}).get("support"), "slab_note_mm": v.get("slab_note_mm"), "slab_panels": int(v.get("slab_panels") or 0)})
            
    levels: dict = {}
    for v in shown:
      if not v["structural"] or not v["level_hint"]:
        continue
      spec = level_spec(v["level_hint"])
      lv = levels.setdefault(v["level_hint"], {"key": v["level_hint"], "name": spec[0] if spec else v["level_hint"], "sequence": spec[1] if spec else 0,
        "columns": 0, "footings": 0, "beams": 0, "column_marks": [], "footing_marks": [], "beam_marks": [], "slab_panels": 0, "slab_thickness_mm": None,
        "pages": []})
      if not v["foundation"]:
        lv["slab_panels"] += v["slab_panels"]
        lv["slab_thickness_mm"] = lv["slab_thickness_mm"] or v["slab_note_mm"]
      if v["page_no"] not in lv["pages"]:
        lv["pages"].append(v["page_no"])
        
    if by_sheet:
      rows = (await self.session.execute(select(TakeoffCandidate).where(TakeoffCandidate.organization_id == org,
        TakeoffCandidate.sheet_id.in_(list(by_sheet)), TakeoffCandidate.decision != "REJECTED",
        TakeoffCandidate.category.in_(("COLUMN", "FOOTING", "BEAM"))))).scalars().all()
      for c in rows:
        hint = (((c.facts or {}).get("view")) or {}).get("level_hint")
        lv = levels.get(hint)
        if lv is None:
          continue
        n = int(c.count or 1)
        
        slot = {"COLUMN": "column", "FOOTING": "footing", "BEAM": "beam"}[c.category]
        p = c.params or {}
        size = [p.get("length_mm"), p.get("width_mm")] if p.get("length_mm") and p.get("width_mm") else None
        lv[slot + "s"] += n
        
        codes = [x.get("code") for x in (c.notes or [])]
        source = "SCHEDULE" if "SIZE_FROM_SCHEDULE" in codes else "DETAIL" if ("SIZE_FROM_COLUMN_DETAIL" in codes or "SIZE_FROM_DETAIL" in codes) else "PLAN" if size else None
        warns = [x.get("code") for x in (c.notes or []) if x.get("severity") == "warning"]
        lv[slot + "_marks"].append({"tag": c.tag or c.label, "count": n, "size_mm": size, "status": c.status, "size_source": source, "warnings": warns})
    for lv in levels.values():
      for slot in ("column_marks", "footing_marks", "beam_marks"):
        lv[slot].sort(key=lambda m: str(m["tag"]))
      lv["pages"].sort()
    return {"views": shown, "levels": sorted(levels.values(), key=lambda lv: lv["sequence"])}

  async def _floor_checks(self, org: UUID, sheets: list, areas: list, heights: dict | None = None, structure: list | None = None) -> list:
    floors = [a for a in areas if a.get("kind") == "FLOOR"]
    if not floors:
      return []

    drawing = await self.repo.drawing(org, sheets[0].drawing_id) if sheets else None
    with QS.deciding(decided.overrides(drawing.ingestion_meta if drawing else None)):
      floor_to_floor = QS.flag("wall_height_floor_to_floor")
    level_ids = {s.level_id for s in sheets if s.level_id}
    hint_of: dict = {}
    if level_ids:
      for lv in (await self.session.execute(select(BuildingLevel).where(BuildingLevel.organization_id == org, BuildingLevel.id.in_(list(level_ids))))).scalars().all():
        hint_of[lv.id] = (lv.ifc_storey_id or "").removeprefix("PDF:")
    by_hint: dict = {}
    for s in sheets:
      if s.level_id and not ((s.prep_meta or {}).get("title") or {}).get("composite"):
        by_hint.setdefault(hint_of.get(s.level_id), []).append(s)
    ids = [s.id for group in by_hint.values() for s in group]
    cands = []
    if ids:
      cands = list((await self.session.execute(select(TakeoffCandidate).where(TakeoffCandidate.organization_id == org,
        TakeoffCandidate.sheet_id.in_(ids), TakeoffCandidate.decision != "REJECTED"))).scalars().all())
      
    out = []
    for a in floors:
      group = by_hint.get(a["key"], [])
      sheet_ids = {s.id for s in group}
      mine = [c for c in cands if c.sheet_id in sheet_ids]
      st = next((lv for lv in (structure or []) if lv["key"] == a["key"]), None)
      row = {"key": a["key"], "name": a["name"], "covered_m2": a["m2"], "pages": sorted(s.page_no for s in group), "rooms": 0, "rooms_m2": 0.0,
        "doors": 0, "windows": 0, "ventilators": 0, "openings_m2": 0.0, "walls_m": 0.0, "coverage_pct": None, "message": None,
        "wall_height_mm": None, "wall_height_basis": None, "brick_9_m2": 0.0, "brick_45_m2": 0.0, "rcc_m2": 0.0,
        "columns": st["columns"] if st else 0, "footings": st["footings"] if st else 0, "beams": st["beams"] if st else 0,
        "slab_panels": st["slab_panels"] if st else 0, "slab_thickness_mm": st["slab_thickness_mm"] if st else None}
      
      h = (heights or {}).get(a["key"])
      if h:
        row["wall_height_mm"], row["wall_height_basis"] = ((h.get("floor_to_floor_mm") or h["clear_mm"]) if floor_to_floor else h["clear_mm"]), h["basis"]
      if not mine:
        row.update(status="NOT_READ", message="No sheet of this floor has been read yet." if not group else "The sheet of this floor has not been read for items yet.")
        out.append(row)
        continue
      for c in mine:
        f = c.facts or {}
        n = int(c.count or 1)
        if c.category == "ROOM":
          row["rooms"] += 1
          row["rooms_m2"] += float(f.get("area_m2") or 0.0)
          
        elif c.category in ("DOOR", "WINDOW"):
          kind = f.get("opening_kind") or c.category
          slot = "doors" if kind == "DOOR" else "ventilators" if kind == "VENTILATOR" else "windows"
          row[slot] += n
          row["openings_m2"] += n * float(f.get("area_each_m2") or 0.0)
        elif c.category == "WALL":
          if f.get("enclosure") == "TANK" or f.get("foundation_item"):
            continue
          length = float(f.get("length_cc_m") or 0.0)
          row["walls_m"] += length
          height = float((c.params or {}).get("height_mm") or row["wall_height_mm"] or 0.0)
          
          if height and length:
            net = max(length * height / 1000.0 - float((f.get("openings") or {}).get("area_m2") or 0.0), 0.0)
            thick = float(f.get("thickness_used_mm") or 0.0)
            slot = "rcc_m2" if f.get("construction") == "RCC" else "brick_45_m2" if thick <= 150.0 else "brick_9_m2"
            row[slot] += net
      row["rooms_m2"], row["openings_m2"], row["walls_m"] = round(row["rooms_m2"], 2), round(row["openings_m2"], 2), round(row["walls_m"], 1)
      for slot in ("brick_9_m2", "brick_45_m2", "rcc_m2"):
        row[slot] = round(row[slot], 2)
      share = row["rooms_m2"] / a["m2"] if a["m2"] else 0.0
      row["coverage_pct"] = round(100.0 * share, 1)
      if row["rooms"] == 0 or share < 0.6:
        row.update(status="LOW", message=f"The rooms found add up to {row['coverage_pct']:.0f}% of the covered area on the area table. Some rooms may be missing.")
      elif share > 1.0:
        row.update(status="HIGH", message="The rooms found add up to more than the covered area on the area table. A room may be counted twice, or the table is for another floor.")
      else:
        row["status"] = "OK"
      out.append(row)
    return out

  @staticmethod
  def _schedule_sheets(sheets: list) -> list:
    out = []
    for s in sheets:
      meta = s.prep_meta or {}
      title = meta.get("title") or {}
      if not meta.get("schedule") and not meta.get("projections"):
        continue
      out.append({"page_no": s.page_no, "schedule": meta.get("schedule"), "level_hint": None if title.get("composite") else title.get("level_hint"), "projections": meta.get("projections")})
    return out

  async def drawing_beam_sections(self, org: UUID, drawing_id: UUID) -> list:
    """The beam sections (plinth, roof, grade beams) read from the details printed on any sheet of the drawing: [{mark, kind, depth_mm, steel, pages, disagree}]."""
    sheets = await self.repo.sheets(org, drawing_id)
    return beam_details.gather([{"page_no": s.page_no, "details": (s.prep_meta or {}).get("beam_details")} for s in sheets if (s.prep_meta or {}).get("beam_details")])

  async def drawing_tank_details(self, org: UUID, drawing_id: UUID) -> list:
    """The plan and section of every water tank drawn on any sheet of the drawing: [{kind, view, caption, page_no, lengths, bar_notes}]."""
    sheets = await self.repo.sheets(org, drawing_id)
    return tank_details.gather([{"page_no": s.page_no, "details": (s.prep_meta or {}).get("tank_details")} for s in sheets if (s.prep_meta or {}).get("tank_details")])

  async def drawing_electrical_legend(self, org: UUID, drawing_id: UUID) -> dict:
    """The electrical legend printed on any sheet of the drawing: {pages: [page numbers of the legend sheets], rows: [one for each symbol: name, description, text tag, picture]}."""
    sheets = await self.repo.sheets(org, drawing_id)
    return electrical_reader.gather_legend([{"page_no": s.page_no, "legend": (s.prep_meta or {}).get("electrical_legend")} for s in sheets if (s.prep_meta or {}).get("electrical_legend")])

  async def sheet_electrical(self, org: UUID, sheet, words: list) -> dict | None:
    """The symbols of the drawing's electrical legend counted on this sheet, when it is an electrical plan; None when the drawing has no legend or this is not a plan. A failure is
    returned as {"failed": True} so the sheet says so."""
    if not electrical_reader.is_plan_sheet(words, (sheet.prep_meta or {}).get("identity")):
      return None
    legend = await self.drawing_electrical_legend(org, sheet.drawing_id)
    if not legend["rows"] or sheet.page_no in legend["pages"]:
      return None
    try:
      drawing = await self.core._pdf_drawing(org, sheet.drawing_id)
      contents = await asyncio.to_thread(_download_bytes, drawing.storage_key)
      return await asyncio.to_thread(electrical_reader.count_page_bytes, contents, sheet.page_no, legend["rows"])
    except Exception:
      logging.getLogger(__name__).exception("Electrical symbols could not be counted on sheet %s", sheet.id)
      return {"failed": True}

  async def drawing_footing_sections(self, org: UUID, drawing_id: UUID) -> list:
    """The footing sections read from the pictures on any sheet of the drawing: [{caption, wall_width_mm, steps, footing, pcc, total_depth_mm, read, issues, page_no}]."""
    sheets = await self.repo.sheets(org, drawing_id)
    return [{**sec, "page_no": s.page_no} for s in sheets for sec in ((s.prep_meta or {}).get("footing_sections") or [])]

  async def drawing_units(self, org: UUID, drawing_id: UUID) -> dict:
    """Whether the whole drawing is dimensioned in feet and inches, decided from every sheet's text together: {"imperial": True | False | None, "basis", "pages"}."""
    sheets = await self.repo.sheets(org, drawing_id)
    return unit_reader.drawing_imperial([{"page_no": s.page_no, "units": (s.prep_meta or {}).get("units"), "hint": (s.prep_meta or {}).get("units_hint")} for s in sheets])

  async def drawing_wall_vocab(self, org: UUID, drawing_id: UUID, imperial: bool | None) -> list:
    """The wall thicknesses (mm) the drawing's own floor sheets snapped to at least twice. The sheet that shows every plan at small size does not vote."""
    sheets = await self.repo.sheets(org, drawing_id)
    own = [s.id for s in sheets if not ((s.prep_meta or {}).get("title") or {}).get("composite")]
    if not own:
      return []
    got = (await self.session.execute(select(TakeoffCandidate.facts).where(TakeoffCandidate.organization_id == org, TakeoffCandidate.sheet_id.in_(own),
      TakeoffCandidate.category == "WALL", TakeoffCandidate.decision != "REJECTED"))).scalars().all()
    rows = [((f or {}).get("thickness_used_mm"), (f or {}).get("thickness_standard_mm"), False) for f in got if (f or {}).get("thickness_used_mm")]
    return unit_reader.wall_vocabulary(rows, imperial)

  async def drawing_schedule(self, org: UUID, drawing_id: UUID) -> dict:
    """The door / window / ventilator sizes and floor areas printed anywhere on the drawing. A mark on the plan of one sheet is sized by the schedule on another."""
    sheets = await self.repo.sheets(org, drawing_id)
    return drawing_schedules.gather(self._schedule_sheets(sheets))

  async def analysis(self, org: UUID, sheet_id: UUID) -> dict:
    sheet = await self._sheet(org, sheet_id)
    row = await self.prep.meta(org, sheet_id)
    return {"sheet_id": sheet.id, "prep_status": sheet.prep_status, "stale": self._stale(sheet), "content_kind": sheet.content_kind,
      "detected_scale": (row.analysis if row is not None else None) or sheet.detected_scale or {}, "meta": sheet.prep_meta or {}}

  async def auto_calibrate(self, org: UUID, sheet_id: UUID, user_id: UUID, payload) -> dict:
    sheet = await self._sheet(org, sheet_id, lock=True)
    row = await self.prep.meta(org, sheet_id)
    if sheet.prep_status != "READY" or row is None or not row.analysis:
      raise TraceException("Prepare this sheet first; its scale has not been read yet.", status_code=409, code="SHEET_NOT_PREPARED")
    full = row.analysis
    
    rec = self._choose_recommendation(full, payload.use)
    if rec is None:
      raise TraceException("No scale or readable dimensions were found on this sheet. Calibrate with two points and a known distance.",
        status_code=422, code="NO_SCALE_RECOMMENDATION")
    user_unit = repo_mod.sheet_user_unit(sheet)
    created, cal = await self._ensure_calibration(org, sheet, user_id, rec, user_unit, make_default=payload.make_default)
    extra = []
    if payload.include_regions and full.get("agreement") == "MULTI_SCALE":
      for c in (full.get("measured") or {}).get("clusters", [])[1:3]:
        if c.get("support", 0) < 3 or not c.get("bbox"):
          continue
        sub = {"ratio": c["ratio"], "scale_text": f"1:{_trim(c['ratio'])}", "basis": "MEASURED_FROM_DIMENSIONS", "trust": 0.85,
          "check": None, "support": c["support"], "region": c["bbox"]}
        _, extra_cal = await self._ensure_calibration(org, sheet, user_id, sub, user_unit, make_default=False)
        extra.append(extra_cal)
    await self.session.commit()
    return {"calibration": cal, "additional": extra, "created": created, "recommendation": rec, "notes": full.get("notes") or []}

  @staticmethod
  def _choose_recommendation(full: dict, use: str) -> dict | None:
    rec = full.get("recommended")
    measured = full.get("measured") or {}
    clusters = measured.get("clusters") or []
    pairs = [p for p in (measured.get("pairs") or []) if p.get("inlier")]
    def best_check(pairs_):
      if not pairs_:
        return None
      p = max(pairs_, key=lambda t: t["quality"] * min(t["length_pt"], 400.0))
      return {"p1": p["p1"], "p2": p["p2"], "value": format(Decimal(str(p["value_mm"])).normalize(), "f"), "unit": "mm", "text": p["text"],
        "length_pt": p["length_pt"]}
    if use == "RECOMMENDED":
      return rec
    if use == "DECLARED":
      d = (full.get("declared") or {}).get("primary")
      
      if not d:
        return None
      return {"method": "SCALE_RATIO", "ratio": d["ratio"], "scale_text": d.get("text") or f"1:{_trim(d['ratio'])}", "basis": "DECLARED",
        "trust": d.get("trust", 0.6), "check": best_check(pairs), "support": len(pairs)}
    if use == "DIMENSIONS":
      if not clusters or clusters[0].get("support", 0) < 2:
        return None
      c = clusters[0]
      return {"method": "SCALE_RATIO", "ratio": c["ratio"], "scale_text": f"1:{_trim(c['ratio'])}", "basis": "MEASURED_FROM_DIMENSIONS",
        "trust": 0.85, "check": best_check(pairs), "support": c["support"]}
    return None

  async def _ensure_calibration(self, org: UUID, sheet, user_id: UUID, rec: dict, user_unit: Decimal, make_default: bool):
    check = None
    if rec.get("check"):
      ck = rec["check"]
      check = {"p1": ck["p1"], "p2": ck["p2"], "known_mm": Decimal(str(ck["value"]))}
    cols = build_calibration("SCALE_RATIO", None, Decimal(str(rec["ratio"])), rec.get("scale_text"), check, user_unit)
    auto = {"basis": rec.get("basis"), "trust": rec.get("trust"), "support": rec.get("support"), "version": ANALYSIS_VERSION}
    if rec.get("region"):
      auto["region"] = rec["region"]
    cols["ref"] = {**(cols.get("ref") or {}), "auto": auto}
    label = self._label(rec)
    
    existing = [c for c in await self.repo.calibrations(org, [sheet.id]) if (c.ref or {}).get("auto") and c.method == "SCALE_RATIO"
      and c.ratio is not None and abs(Decimal(c.ratio) / cols["ratio"] - 1) < Decimal("0.0001")
      and (c.check_ref or None) == (cols["check_ref"] or None) and ((c.ref or {}).get("auto") or {}).get("region") == auto.get("region")]
    if existing:
      cal = existing[0]
      if make_default and cal.usable and not cal.is_default:
        await self.core._set_default(org, sheet.id, cal)
      return False, cal
    cal = TakeoffCalibration(id=uuid4(), organization_id=org, sheet_id=sheet.id, label=label, created_by_user_id=user_id, is_default=False, **cols)
    self.session.add(cal)
    await self.session.flush()
    others = [c for c in await self.repo.calibrations(org, [sheet.id]) if c.id != cal.id and c.usable and c.is_default]
    if cal.usable and (make_default or not others):
      await self.core._set_default(org, sheet.id, cal)
    await self.core._log(org, user_id, cal.id, AuditAction.CREATE,
      f"Auto-calibrated sheet {sheet.page_no} from {str(rec.get('basis')).lower().replace('_', ' ')} ({'usable' if cal.usable else 'not usable'})")
    return True, cal

  @staticmethod
  def _label(rec: dict) -> str:
    base = f"Auto 1:{_trim(rec['ratio'])}"
    n = rec.get("support") or 0
    if rec.get("region"):
      return f"{base} (view)"[:120]
    if n:
      return f"{base} · {n} printed dimension{'s' if n != 1 else ''} agree"[:120]
    return f"{base} · printed scale, unverified"[:120]

  async def vector_window(self, org: UUID, sheet_id: UUID, bbox: tuple | None, max_segments: int) -> dict:
    await self._sheet(org, sheet_id)
    index = await self._index(org, sheet_id)
    x0, y0, x1, y1 = bbox if bbox else index.bbox
    cap = max(100, min(int(max_segments), MAX_VECTOR_SEGMENTS))
    edges, total, truncated = index.window(x0, y0, x1, y1, cap)
    return {"bbox": [_fmt(x0), _fmt(y0), _fmt(x1), _fmt(y1)],
      "segments": [[_fmt(a), _fmt(b), _fmt(c), _fmt(d), int(k)] for a, b, c, d, k in edges], "total": total, "truncated": truncated}

  async def text(self, org: UUID, sheet_id: UUID, query: str | None, mode: str, bbox: tuple | None, limit: int = 5000) -> dict:
    await self._sheet(org, sheet_id)
    index = await self._index(org, sheet_id)
    if query:
      words = census.find_words(index.words, query, "WORD" if mode == "WORD" else "CONTAINS" if mode == "CONTAINS" else "TAG")
      if bbox:
        words = [w for w in words if bbox[0] <= w["x"] <= bbox[2] and bbox[1] <= w["y"] <= bbox[3]]
    else:
      src = index.words
      if bbox:
        src = [w for w in src if bbox[0] <= w.cx <= bbox[2] and bbox[1] <= w.cy <= bbox[3]]
      words = [{"text": w.text, "x": _fmt(w.cx), "y": _fmt(w.cy), "angle": _fmt(w.angle, 1), "size": _fmt(w.size, 2)} for w in src]
    total = len(words)
    return {"total": total, "words": words[:limit], "truncated": total > limit}

  async def snap(self, org: UUID, sheet_id: UUID, payload) -> dict:
    await self._sheet(org, sheet_id)
    index = await self._index(org, sheet_id)
    want = tuple(payload.want) if payload.want else ("ENDPOINT", "INTERSECTION", "MIDPOINT", "EDGE")
    out = []
    for x, y in payload.points:
      hit = index.nearest(float(x), float(y), payload.radius_pt, want)
      if hit is None:
        out.append({"input": [float(x), float(y)], "snapped": False})
      else:
        out.append({"input": [float(x), float(y)], "snapped": True, "x": _fmt(hit["x"], 4), "y": _fmt(hit["y"], 4), "kind": hit["kind"],
          "distance": _fmt(hit["distance"], 4)})
    return {"results": out}

  async def pick(self, org: UUID, sheet_id: UUID, payload) -> dict:
    sheet = await self._sheet(org, sheet_id)
    index = await self._index(org, sheet_id)
    x, y = float(payload.point[0]), float(payload.point[1])
    mm_per_pt = await self._mm_per_pt(org, sheet, payload.calibration_id)
    hit = index.nearest(x, y, payload.radius_pt)
    snap = None if hit is None else {"x": _fmt(hit["x"], 4), "y": _fmt(hit["y"], 4), "kind": hit["kind"], "distance": _fmt(hit["distance"], 4)}
    wall = None
    if payload.wall and hit is not None:
      if mm_per_pt:
        w = index.wall_at(x, y, float(mm_per_pt), radius=payload.radius_pt)
      else:
        edge = index.nearest(x, y, payload.radius_pt, want=("EDGE",))
        w = {"run": list(index.run_of(edge["segment"])), "partner": None} if edge is not None and not index.kinds[edge["segment"]] else None
      if w is not None:
        wall = {"run": [[_fmt(v, 4) for v in p] for p in w["run"]], "partner": None}
        
        if w.get("partner"):
          part = w["partner"]
          t = part["thickness_mm"]
          near = min(STANDARD_WALLS_MM, key=lambda s_: abs(t / s_ - 1.0))
          wall.update({"partner": True, "centreline": [[_fmt(v, 4) for v in p] for p in w["centreline"]], "overlap": _fmt(part["overlap"], 3),
            "offset_pt": _fmt(part["offset_pt"], 4), "thickness_mm": _fmt(t, 1),
            "suggested_thickness_mm": near if abs(t / near - 1.0) <= 0.04 else int(round(t / 5.0) * 5)})
        elif not mm_per_pt:
          wall["note"] = "Calibrate the sheet to read the wall thickness."
          
    region = None
    if payload.region:
      found = index.region_at(x, y)
      if found is not None:
        ring_i, holes = found
        r = index.rings[ring_i]
        per = sum(math.dist(r.pts[i], r.pts[(i + 1) % len(r.pts)]) for i in range(len(r.pts)))
        region = {"outer": [[_fmt(a, 4), _fmt(b, 4)] for a, b in r.pts], "area_pt2": _fmt(r.area, 3), "perimeter_pt": _fmt(per, 3),
          "holes": [{"ring": [[_fmt(a, 4), _fmt(b, 4)] for a, b in index.rings[h].pts], "area_pt2": _fmt(index.rings[h].area, 3)} for h in holes[:30]]}
        if mm_per_pt:
          f = float(mm_per_pt)
          region["area_m2"] = _fmt(r.area * f * f / 1e6, 4)
          region["perimeter_m"] = _fmt(per * f / 1000.0, 3)
          region["holes_area_m2"] = _fmt(sum(index.rings[h].area for h in holes) * f * f / 1e6, 4)
          
    labels = []
    if payload.label_radius_pt > 0:
      for w in index.words:
        d = math.hypot(w.cx - x, w.cy - y)
        if d <= payload.label_radius_pt:
          labels.append((d, {"text": w.text, "x": _fmt(w.cx), "y": _fmt(w.cy), "distance": _fmt(d, 2)}))
      labels.sort(key=lambda t: t[0])
    return {"snap": snap, "wall": wall, "region": region, "labels": [l for _, l in labels[:20]],
        "mm_per_pt": format(mm_per_pt.normalize(), "f") if mm_per_pt else None}

  async def tags(self, org: UUID, sheet_id: UUID) -> dict:
    await self._sheet(org, sheet_id)
    index = await self._index(org, sheet_id)
    return {"tags": [{"tag": g["tag"], "count": g["count"], "in_drawing": g["in_drawing"]} for g in census.tag_census(index.words)]}

  async def tag_detail(self, org: UUID, sheet_id: UUID, tag: str, include_dense: bool) -> dict:
    await self._sheet(org, sheet_id)
    index = await self._index(org, sheet_id)
    hits = census.find_words(index.words, tag, "TAG")
    
    if not hits:
      raise TraceException(f"The tag {tag} was not found on this sheet.", status_code=404, code="TAG_NOT_FOUND")
    counted = [h for h in hits if include_dense or not h["dense"]]
    note = None
    dense = len(hits) - len([h for h in hits if not h["dense"]])
    if dense and not include_dense:
      note = f"{dense} occurrence(s) sit inside a dense block of text (a schedule, legend or notes) and are left out of the count."
    pts = [[h["x"], h["y"]] for h in counted]
    return {"tag": tag.strip().upper(), "count": len(hits), "in_drawing": len(hits) - dense,
      "points": [{"x": h["x"], "y": h["y"], "dense": h["dense"]} for h in hits],
      "suggestion": {"kind": "COUNT", "quantity_mode": "DIRECT", "geometry": {"points": pts}, "source": "TAG_SCAN",
        "tag": tag.strip().upper(), "label": f"{tag.strip().upper()} x{len(pts)}"},
      "note": note}

  async def shapes(self, org: UUID, sheet_id: UUID) -> dict:
    sheet = await self._sheet(org, sheet_id)
    index = await self._index(org, sheet_id)
    mm = await self._mm_per_pt(org, sheet)
    groups = census.shape_groups(index.rings, max((index.bbox[2] - index.bbox[0]) * (index.bbox[3] - index.bbox[1]), 1.0))
    out = []
    for g in groups:
      out.append(self._shape_summary(g, mm))
    return {"shapes": out, "mm_per_pt": format(mm.normalize(), "f") if mm else None}

  @staticmethod
  def _shape_summary(g: dict, mm) -> dict:
    return {"id": g["id"], "shape": g["shape"], "a_pt": g["a_pt"], "b_pt": g["b_pt"],
      "a_mm": _fmt(g["a_pt"] * float(mm), 1) if mm else None, "b_mm": _fmt(g["b_pt"] * float(mm), 1) if mm else None,
        "count": g["count"], "filled": g["filled"]}

  async def shape_detail(self, org: UUID, sheet_id: UUID, group_id: str) -> dict:
    sheet = await self._sheet(org, sheet_id)
    index = await self._index(org, sheet_id)
    mm = await self._mm_per_pt(org, sheet)
    for g in census.shape_groups(index.rings, max((index.bbox[2] - index.bbox[0]) * (index.bbox[3] - index.bbox[1]), 1.0)):
      if g["id"] == group_id:
        label = f"{g['shape'].title()} {g['count']} nos"
        return {"shape": self._shape_summary(g, mm), "points": g["points"],
          "suggestion": {"kind": "COUNT", "quantity_mode": "DIRECT", "geometry": {"points": g["points"]}, "source": "VECTOR_SNAP",
            "tag": None, "label": label}}
    raise TraceException("That shape group was not found on this sheet.", status_code=404, code="SHAPE_GROUP_NOT_FOUND")

  async def verified_source(self, org: UUID, sheet, kind: str, geometry: dict, source: str, tag: str | None = None) -> str:
    
    if source in ("MANUAL", "PRINTED"):
      return source
    index = await self.prep.load_index(org, sheet.id)
    if index is None:
      return "MANUAL"
    pts: list = []
    if kind == "LENGTH":
      pts = list(geometry.get("points") or [])
    elif kind == "AREA":
      pts = list(geometry.get("outer") or []) + [p for h in (geometry.get("holes") or []) for p in h]
    else:
      pts = list(geometry.get("points") or [])
      
    if not pts:
      return "MANUAL"
    if kind == "COUNT":
      if source == "TAG_SCAN":
        if not tag:
          return "MANUAL"
        want = tag.strip().upper()
        words = [w for w in index.words if w.text.strip().upper() == want]
        ok = all(any(math.hypot(w.cx - p[0], w.cy - p[1]) <= TAG_VERIFY_RADIUS_PT for w in words) for p in pts)
        return "TAG_SCAN" if ok else "MANUAL"
      centres = [((r.bbox[0] + r.bbox[2]) / 2.0, (r.bbox[1] + r.bbox[3]) / 2.0) for r in index.rings]
      ok = all(any(math.hypot(c[0] - p[0], c[1] - p[1]) <= 1.0 for c in centres) or index.on_geometry(float(p[0]), float(p[1]), 3.0) for p in pts)
      return "VECTOR_SNAP" if ok else "MANUAL"
    if source != "VECTOR_SNAP":
      return "MANUAL"
    ok = all(index.on_geometry(float(p[0]), float(p[1]), SNAP_VERIFY_TOL_PT) for p in pts)
    return "VECTOR_SNAP" if ok else "MANUAL"

def _trim(v) -> str:
  s = format(Decimal(str(round(float(v), 4))).normalize(), "f")
  return s