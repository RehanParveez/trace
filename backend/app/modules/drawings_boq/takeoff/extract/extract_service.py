from __future__ import annotations
import logging
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import time
from uuid import UUID
from app.modules.drawings_boq.takeoff.prep_service import PrepService
from app.modules.drawings_boq.takeoff.prep.analyze import ANALYSIS_VERSION
from app.modules.drawings_boq.takeoff.prep import opening_heights as OHT
from app.modules.drawings_boq.takeoff.levels import ensure_level
from app.modules.drawings_boq.takeoff.register_service import RegisterService
from app.modules.drawings_boq.takeoff.extract.extract_repository import ExtractRepository
from app.modules.drawings_boq.takeoff.extract.scalegate import auto_scale_gate, composite_issue
from app.modules.drawings_boq.models import TakeoffExtraction, TakeoffCandidate
from app.modules.audit.models import AuditAction
from pydantic import ValidationError
from app.core.exceptions import TraceException
from app.engine.measure import readings as QS
from app.engine.measure import company as CO
from app.engine.measure import rulebook as RB
from app.modules.drawings_boq import company_conventions as CCV
from app.modules.drawings_boq import rule_book_service as RBS
from app.modules.drawings_boq.takeoff.decisions import store as decided
from app.engine.measure import takeoff as tk
from app.modules.drawings_boq.takeoff import repository as repo_mod
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.extract import slab_label as SL
from app.modules.drawings_boq.takeoff.extract import conflicts as CF
from app.modules.drawings_boq.takeoff.extract import revisions as RV
from app.modules.drawings_boq.finish_schedule.common import work_item_catalog
from app.modules.drawings_boq.takeoff.prep_schemas import AutoCalibrateRequest
from app.modules.drawings_boq.takeoff.extract import foundation as FD
from app.modules.drawings_boq.takeoff.extract import finishes as FN
from app.modules.drawings_boq.takeoff.extract import site_items as SI
from app.modules.drawings_boq.takeoff.extract import boundary as BDY
from app.modules.drawings_boq.takeoff.extract import drainage as DR
from app.modules.drawings_boq.takeoff.prep import stairs as STR
from app.modules.drawings_boq.takeoff import stair_twins as ST
from app.modules.drawings_boq.takeoff.extract import kinds as KD
from app.modules.drawings_boq.takeoff.extract import beam_sections as BS
from app.modules.drawings_boq.takeoff.extract import steel_rollup as SR
from app.modules.drawings_boq.takeoff.extract import floor_overlap as FO
from app.modules.drawings_boq.takeoff.extract import floor_sources as FS
from app.modules.drawings_boq.takeoff.prep import project_facts as PF
from app.modules.drawings_boq.takeoff.extract import accept_guard as AG
from app.modules.drawings_boq.takeoff.extract.beam_overlap_service import reconcile_beams
from app.modules.drawings_boq.takeoff.extract.slab_openings_service import reconcile_slab_openings
from app.modules.drawings_boq.takeoff.detail_only.apply import apply_decisions as apply_detail_decisions
from app.modules.drawings_boq.takeoff.grades import stamp as GS
from app.modules.drawings_boq.takeoff.printed_service import printed_for_drawings
from app.modules.drawings_boq.takeoff.extract import typed_memory as TM
from app.modules.drawings_boq.takeoff.extract import slab_openings as SO
from app.modules.drawings_boq.takeoff.extract.extract_schemas import CandidateResponse
from app.modules.drawings_boq.takeoff import corrections as CR
from app.modules.drawings_boq.takeoff.extract.pipeline import Candidate, _status, run_extraction
from app.modules.drawings_boq.takeoff.levels import view_level_id
from app.modules.drawings_boq.takeoff.schemas import MeasurementCreateRequest, MeasurementParams

log = logging.getLogger(__name__)

class NoPlanRegions(Exception):
  """The sheet does not split into floor plans."""

HEIGHT_FIELDS = {
  ("WALL", "height_mm"): ("wall_height_mm", "height_mm", "the wall height"),
  ("COLUMN", "height_mm"): ("column_height_mm", "depth_mm", "the column height"),
  ("FOOTING", "depth_mm"): ("footing_depth_mm", "depth_mm", "the footing depth"),
  ("SLAB", "thickness_mm"): ("slab_thickness_mm", "depth_mm", "the slab thickness"),
  ("BEAM", "depth_mm"): ("beam_depth_mm", "depth_mm", "the beam depth"),
  ("WALL", "tile_height_mm"): ("tile_height_mm", "height_mm", "the height of the kitchen wall tile"),
}

def height_field(category: str, need: str, facts: dict | None) -> tuple | None:
  if category == "WALL" and (facts or {}).get("foundation_item") in BDY.ITEMS:
    return BDY.field_of(need)
  if category == "WALL" and (facts or {}).get("foundation_item") in DR.TYPED_FIELD:
    item = facts["foundation_item"]
    return (DR.TYPED_FIELD[item], "length_mm", DR.WORDS[item]) if need == "length_mm" else None
  spec = HEIGHT_FIELDS.get((category, need))
  if spec is None:
    return None
  field, target, words = spec
  
  f = facts or {}
  if category == "BEAM" and f.get("beam_role") == "PLINTH":
    field, words = "plinth_beam_depth_mm", "the plinth beam depth"
  if category == "BEAM" and f.get("beam_role") == "BAND":
    field, words = "tie_band_depth_mm", "the tie band depth"
  if category == "COLUMN" and f.get("neck_of"):
    field, words = "neck_height_mm", "the neck column height (top of the footing to the floor)"
  if category == "WALL" and f.get("enclosure") == "TANK":
    field, words = "tank_wall_height_mm", "the tank wall height"
  return field, target, words

def _now() -> datetime:
  return datetime.now(timezone.utc)

def _same_scale(a, b) -> bool:
  if a is None or b is None:
    return False
  a, b = Decimal(str(a)), Decimal(str(b))
  return abs(a - b) <= max(abs(a), abs(b)) * Decimal("0.000001")

def index_stamp(meta) -> str:
  return f"{meta.analysis_version}:{meta.updated_at.isoformat() if meta.updated_at else ''}"[:40]

def _fail(ident: UUID, code: str, message: str) -> dict:
  return {"id": str(ident), "code": code, "message": message}

def fill_missing(category: str, missing: list, params: dict, typed: dict, notes: list | None = None, facts: dict | None = None) -> tuple:
  if category == "SITE":
    return SI.fill_site((facts or {}).get("site_kind"), missing, params, typed, facts or {})
  item = (facts or {}).get("foundation_item") if category == "WALL" else None
  if item in FD.ITEMS:
    return FD.fill_foundation(item, missing, params, typed, facts or {})
  if item in FN.ITEMS:
    return FN.fill_finish(item, missing, params, typed, facts or {})
  if item in BDY.ITEMS:
    return BDY.fill_boundary(item, missing, params, typed, facts or {})
  if item in DR.ITEMS:
    return DR.fill_drainage(item, missing, params, typed, facts or {})
  out = dict(params or {})
  
  if category == "SLAB" and typed.get("slab_thickness_mm") is not None and any(n.get("code") == "SLAB_THICKNESS_DISAGREES" for n in notes or []):
    out["depth_mm"] = float(typed["slab_thickness_mm"])
    out["dims_basis"] = "SPECIFIED"
  if category == "COLUMN" and (facts or {}).get("neck_assumed") and typed.get("neck_height_mm") is not None:
    out["depth_mm"] = float(typed["neck_height_mm"])
    out["dims_basis"] = "SPECIFIED"
  if category == "STAIR" and "waist_mm" in (missing or []):
    value = typed.get("stair_waist_mm")
    
    if value is None:
      return out, ("CANDIDATE_NEEDS_DIMENSIONS", "Give the thickness of the waist slab under the steps to measure this stair.")
    f = facts or {}
    if not f.get("riser_mm") or not f.get("tread_mm"):
      return out, ("CANDIDATE_NEEDS_DIMENSIONS", "No size was found for this item. Draw it by hand.")
    out["depth_mm"] = round(STR.equivalent_depth_mm(float(f["riser_mm"]), float(f["tread_mm"]), float(value)), 1)
    out["dims_basis"] = "SPECIFIED"
    missing = [m for m in missing if m != "waist_mm"]
  for need in missing or []:
    spec = height_field(category, need, facts)
    
    if spec is None:
      return out, ("CANDIDATE_NEEDS_DIMENSIONS", "No size was found for this item. Draw it by hand.")
    field, target, words = spec
    value = typed.get(field)
    if value is None:
      return out, ("CANDIDATE_NEEDS_DIMENSIONS", f"Give {words} to measure this item.")
    out[target] = float(value)
    out["dims_basis"] = "SPECIFIED"
  return out, None

def _spec_grade(cand) -> str | None:
  grade = ((cand.facts or {}).get("spec_grade") or {}).get("grade")
  return str(grade)[:50] if grade else None

CONCRETE_MEMBER = {"FOOTING": "foundation", "COLUMN": "frame", "BEAM": "frame", "SLAB": "frame", "LINTEL": "frame"}

def _concrete_member(cand, code) -> dict:
  member = CONCRETE_MEMBER.get(cand.category)
  return {"member": member} if member and str(code or "").upper().startswith("CON-RCC") else {}

def _openings_params(cand, params: dict, typed: dict) -> dict:
  if cand.category == "SLAB":
    adj = SO.slab_adjustments(cand.facts, params.get("depth_mm"))
  elif cand.category == "STAIR":
    adj = SO.stair_adjustments(cand.facts, (cand.facts or {}).get("waist_mm") or typed.get("stair_waist_mm"))
  else:
    adj = []
  return {"adjustments": adj} if adj else {}

def _roof_params(cand) -> dict:
  f = cand.facts or {}
  if f.get("foundation_item") != "ROOF_TREATMENT" or f.get("roof_part") == "PROJECTION":
    return {}
  slope = f.get("slope") if isinstance(f.get("slope"), dict) else {}
  roof = {k: v for k, v in {"fall_mm": slope.get("avg_mm"), "fall_min_mm": slope.get("min_mm"), "fall_max_mm": slope.get("max_mm"), "edge_m": f.get("edge_m")}.items() if v}
  return {"roof": roof} if roof else {}

ACCEPT_TYPED_FIELDS = (
  "wall_height_mm", "column_height_mm", "footing_depth_mm", "slab_thickness_mm", "beam_depth_mm",
  "plinth_beam_depth_mm", "tie_band_depth_mm", "excavation_depth_mm", "fill_depth_mm", "trench_depth_mm",
  "pcc_thickness_mm", "pcc_strip_width_mm", "pcc_strip_width_thin_mm",
  "brick_step_1_height_mm", "brick_step_2_height_mm", "brick_step_3_height_mm", "brick_step_4_height_mm",
  "brick_step_offset_mm", "membrane_width_mm",
  "door_frame_width_mm", "door_frame_width_thin_mm", "tile_height_mm",
  "stair_waist_mm", "neck_height_mm", "tank_wall_height_mm",
  "boundary_side_mm", "boundary_rear_mm",
  "rain_pipe_length_mm", "sewer_length_mm",
  "site_length_mm", "site_width_mm", "site_height_mm", "site_thickness_mm",
)

@dataclass
class AcceptPlan:
  """What accepting one candidate will measure: the work item, the params with every typed value filled in, the values still missing before the fill, the beam section chosen (or None), and whether a person typed steel."""
  code: str | None
  params: dict
  missing: list
  section: dict | None
  steel_typed: bool = False

def plan_accept(cand, given: dict, typed: dict, catalog: dict, *, section_pick=None, steel=None, allow_repeat_marks: bool = False) -> tuple:
  if cand.status == "INVALID":
    return None, ("CANDIDATE_INVALID", "This item has an error and cannot be measured.")
  if cand.category == "BEAM" and (cand.facts or {}).get("derived_from") != "WALLS" and not (cand.facts or {}).get("from_strips"):
    return None, ("CANDIDATE_NOT_MEASURABLE", "Beam marks are only counted. Draw the beam lengths with the length tool.")
  if not allow_repeat_marks and any(n.get("code") == "BEAM_FROM_FRAMING_PLAN" for n in cand.notes or []):
    return None, ("BEAM_FROM_FRAMING_PLAN", C.NOTES["BEAM_FROM_FRAMING_PLAN"][1])
  missing, start, section = cand.missing or [], cand.params or {}, None
  
  if section_pick is not None:
    section, problem = BS.chosen(cand.facts, section_pick)
    if problem:
      return None, problem
    start = BS.with_section(start, section)
    if section.get("depth_mm"):
      missing = [m for m in missing if m != "depth_mm"]
  params, problem = fill_missing(cand.category, missing, start, typed, cand.notes or [], cand.facts or {})
  
  if problem:
    return None, problem
  if steel is not None:
    params = {**params, "steel": steel.model_dump(mode="json", exclude_none=True)}
  code = KD.code_for(cand, given)
  if code and code not in catalog and given.get(KD.kind_of(cand)):
    return None, ("WORK_ITEM_NOT_FOUND", f"Work item '{code}' is not in the catalog.")
  if code and code not in catalog:
    code = None
  return AcceptPlan(code=code, params=params, missing=missing, section=section, steel_typed=steel is not None), None

def grade_stamp(cand, code, concrete_rules) -> dict | None:
  stamp = GS.stamp_for(cand, concrete_rules) if GS.member_of(cand) is not None and GS.is_concrete_code(code) else None
  return stamp if stamp is not None else GS.mix_stamp(cand)

def request_for(cand, plan: AcceptPlan, typed: dict, stamp, own_level) -> MeasurementCreateRequest:
  params = plan.params
  return MeasurementCreateRequest(kind=cand.kind, quantity_mode=cand.quantity_mode, geometry=cand.geometry,
    params=MeasurementParams(**{**params, **_openings_params(cand, params, typed), **_roof_params(cand), **_concrete_member(cand, plan.code)}), work_item_code=plan.code, level_id=own_level,
    label=cand.label, tag=cand.tag, source=cand.source, material_grade=stamp["grade"][:50] if stamp else _spec_grade(cand))

def apply_accepted(cand, plan: AcceptPlan, stamp, typed: dict) -> None:
  params, missing, section = plan.params, plan.missing, plan.section
  used = TM.fields_used(cand.category, missing, cand.facts, typed, cand.notes, height_field)
  
  if used:
    cand.facts = {**(cand.facts or {}), TM.KEY: used}
  if stamp:
    cand.facts = {**(cand.facts or {}), GS.KEY: stamp}
  if params != (cand.params or {}):
    if cand.category == "SLAB":
      cand.facts = {**(cand.facts or {}), "thickness_mm": params.get("depth_mm"), "thickness_source": "TYPED"}
    if cand.category == "SITE":
      cand.facts = {**(cand.facts or {}), "sizes_source": "TYPED", "sizes_mm": SI.typed_sizes((cand.facts or {}).get("site_kind"), missing, typed, cand.facts or {})}
    if FD.is_foundation(cand):
      cand.facts = {**(cand.facts or {}), "sizes_source": "TYPED", "sizes_mm": {k: params[k] for k in ("width_mm", "depth_mm") if params.get(k) is not None}}
    if section is not None:
      cand.facts = {**(cand.facts or {}), "section_mark": section["mark"], "section_chosen": True, "steel_text": section.get("steel_text"),
        "steel_source": {"grade": "PRINTED", "text": f"beam section {section['mark']} (chosen)"}}
    if plan.steel_typed:
      cand.facts = {**(cand.facts or {}), "steel_source": {"grade": "TYPED", "text": None}}
    cand.params = params
    if cand.category == "SLAB":
      cand.label = SL.current(cand)

class ExtractService:
  def __init__(self, session):
    self.session = session
    self.prep = PrepService(session)
    self.core = self.prep.core
    self.repo = ExtractRepository(session)

  async def _scale(self, org: UUID, sheet):

    cal = await self.core._default_calibration(org, sheet.id)
    if cal is None:
      return None, None
    ev = tk.evaluate_calibration(repo_mod.calibration_input(cal, repo_mod.sheet_user_unit(sheet)))
    return (cal, ev) if ev.usable else (None, None)

  async def _heal(self, org: UUID, rows: list) -> bool:

    accepted = [r for r in rows if r.decision == "ACCEPTED"]
    if not accepted:
      return False
    alive = await self.repo.existing_measurement_ids(org, [r.measurement_id for r in accepted if r.measurement_id])
    changed = False
    
    for r in accepted:
      if r.measurement_id is None or r.measurement_id not in alive:
        r.decision, r.measurement_id, r.decided_at, r.decided_by_user_id = "NEW", None, None, None
        changed = True
    if changed:
      await self.session.flush()
    return changed

  async def _sync_register(self, org: UUID, sheet_ids) -> None:
    try:
      drawings = {(await self.core._sheet(org, sid)).drawing_id for sid in set(sheet_ids)}
      for drawing_id in drawings:
        async with self.session.begin_nested():
          await RegisterService(self.session).sync_drawing(org, drawing_id)
    except Exception:
      log.exception("PDF register could not be updated")

  @staticmethod
  def _summary(rows: list) -> dict:
    by_cat: dict = {}
    for r in rows:
      c = by_cat.setdefault(r.category, {"found": 0, "new": 0, "accepted": 0, "rejected": 0})
      c["found"] += 1
      c[r.decision.lower()] += 1
    return {"total": len(rows), "new": sum(1 for r in rows if r.decision == "NEW"), "accepted": sum(1 for r in rows if r.decision == "ACCEPTED"),
      "rejected": sum(1 for r in rows if r.decision == "REJECTED"), "warnings": sum(1 for r in rows if r.status != "VALID" and r.decision == "NEW"),
      "by_category": by_cat}

  async def _meta(self, org: UUID, sheet, ext: TakeoffExtraction | None) -> dict:
    if ext is None:
      return {"sheet_id": sheet.id, "ran": False}
    reasons: list = []
    cal, ev = await self._scale(org, sheet)
    if ev is None or not _same_scale(ev.mm_per_pt, ext.mm_per_pt):
      reasons.append("SCALE_CHANGED")
      
    meta = await self.prep.prep.meta(org, sheet.id)
    if meta is None or index_stamp(meta) != ext.index_stamp:
      reasons.append("SHEET_READ_AGAIN")
    if meta is not None and meta.analysis_version != ANALYSIS_VERSION:
      reasons.append("SHEET_READER_OLDER")
    if ext.extract_version != C.EXTRACT_VERSION:
      reasons.append("NEWER_LOGIC")
    return {"sheet_id": sheet.id, "ran": True, "ran_at": ext.updated_at, "stale": bool(reasons), "stale_reasons": reasons,
      "mm_per_pt": ext.mm_per_pt, "scale_unverified": ext.scale_unverified, "stats": ext.stats or {}, "unmapped_tags": ext.unmapped_tags or [],
      "notes": ext.notes or []}

  @staticmethod
  def _with_steel(rows: list) -> list:
    """Each member that has bars read carries the cut lengths and the weight of one member in its facts, worked out from its present size and bars."""
    out = []
    for r in rows:
      s = SR.summary_of(r) if r.decision != "REJECTED" else None
      if s is None or s.get("state") == "NO_BARS":
        out.append(r)
        continue
      copy = r if isinstance(r, CandidateResponse) else CandidateResponse.model_validate(r)
      copy.facts = {**copy.facts, "steel_summary": s}
      out.append(copy)
    return out

  async def _list(self, org: UUID, sheet) -> dict:
    rows = await self.repo.candidates(org, [sheet.id])
    if await self._heal(org, rows):
            await self.session.commit()
    ext = await self.repo.extraction(org, sheet.id)
    return {"sheet_id": sheet.id, "extraction": await self._meta(org, sheet, ext), "candidates": self._with_steel(await self._with_stair_twins(org, sheet, rows)), "summary": self._summary(rows)}

  async def _with_stair_twins(self, org: UUID, sheet, rows: list) -> list:
    if not any(r.category == "STAIR" and r.decision != "REJECTED" for r in rows):
      return rows
    sheets = {s.id: s for s in await self.core.repo.sheets(org, sheet.drawing_id)}
    every = await self.repo.candidates(org, list(sheets))
    solved = ST.solve(every, sheets)
    lone = set(solved.lone)
    
    out = []
    for r in rows:
      info = solved.info.get(r.id)
      if not info and r.id not in lone:
        out.append(r)
        continue
      copy = CandidateResponse.model_validate(r)
      if info:
        note = C.note("STAIR_TWIN_ABOVE", page=info["twin_of_page"], how=info["how"], gap_m=info["gap_m"])
        note["message"] += f" The stair is measured from the flight on sheet {info['twin_of_page']}."
        copy.facts = {**copy.facts, "twin_of_page": info["twin_of_page"], "twin_of_how": info["how"]}
      else:
        note = C.note("STAIR_FLIGHT_NO_PARTNER")
      copy.notes = [*copy.notes, note]
      out.append(copy)
    return out

  async def candidates(self, org: UUID, sheet_id: UUID) -> dict:
    sheet = await self.core._sheet(org, sheet_id)
    return await self._list(org, sheet)

  async def drawing_candidates(self, org: UUID, drawing_id: UUID) -> dict:
    await self.core._pdf_drawing(org, drawing_id)
    sheets = await self.core.repo.sheets(org, drawing_id)
    return {"drawing_id": drawing_id, "sheets": [await self._list(org, s) for s in sheets]}

  async def _ensure_scale(self, org: UUID, sheet, user_id: UUID, auto: bool):
    cal, ev = await self._scale(org, sheet)
    if ev is not None:
      return cal, ev, False
  
    if not auto:
      raise TraceException("Set the scale of this sheet first. The sizes found depend on it.", status_code=409, code="SHEET_NOT_CALIBRATED")
    meta = await self.prep.prep.meta(org, sheet.id)
    ok, code, message = auto_scale_gate(meta.analysis if meta is not None else None)
    if not ok:
      raise TraceException(message, status_code=409, code=code)
    await self.prep.auto_calibrate(org, sheet.id, user_id, AutoCalibrateRequest(use="RECOMMENDED", make_default=True))
    sheet = await self.core._sheet(org, sheet.id)
    cal, ev = await self._scale(org, sheet)
    if ev is None:
      raise TraceException("The recommended scale could not be used. Set the scale by hand.", status_code=409, code="SHEET_NOT_CALIBRATED")
    return cal, ev, True

  async def extract_sheet(self, org: UUID, sheet_id: UUID, user_id: UUID, payload, regions_only: bool = False, site_only: bool = False) -> dict:
    sheet = await self.core._sheet(org, sheet_id, lock=True)
    if sheet.prep_status != "READY":
      raise TraceException("Prepare this sheet first; its drawing has not been read yet.", status_code=409, code="SHEET_NOT_PREPARED")
    index = await self.prep._index(org, sheet.id)
    meta = await self.prep.prep.meta(org, sheet.id)
    cal, ev, created = await self._ensure_scale(org, sheet, user_id, payload.auto_calibrate)
    mm_per_pt = float(ev.mm_per_pt)
    unverified = "PDF_RATIO_UNVERIFIED" in (ev.warnings or ())
    
    drawing = await self.core._pdf_drawing(org, sheet.drawing_id)
    CO.hold(await CCV.in_force(self.session, org))
    book = await RBS.snapshot(self.session, org, sheet.project_id)
    if book is not None:
      RB.hold(book)
    in_force = decided.effective(drawing.ingestion_meta)
    bundle = await self.prep.fact_bundle(org, drawing)
    known = bundle["facts"]
    schedule, floor_heights, slab_values, beam_sections = known["schedule"], known["storey_heights"], known["slab_values"], known["beam_sections"]
    tank_details, footing_sections, spec_facts = known["tank_details"], known["footing_sections"], known["spec_facts"]
    electrical = await self.prep.sheet_electrical(org, sheet, index.words)
    units = await self.prep.sheet_units(org, sheet, known["units"])
    wall_vocab = await self.prep.drawing_wall_vocab(org, sheet.drawing_id, units["imperial"])
    mark_vocab = await self.prep.drawing_marks(org, drawing)
    opening_heights = OHT.decide(known["opening_labels"])
    title = (sheet.prep_meta or {}).get("title") or {}
    level_hint = None if title.get("composite") else title.get("level_hint")
    floors = self.prep._floor_keys(await self.prep.repo.sheets(org, sheet.drawing_id))
    lowest_level = bool(level_hint) and bool(floors) and floors[0] == level_hint
    try:
      with QS.deciding(decided.overrides(drawing.ingestion_meta)):
        result = await asyncio.to_thread(run_extraction, index, mm_per_pt, composite=bool(title.get("composite")), regions_only=regions_only, site_only=site_only, cal_factor=float(ev.factor), scale_unverified=unverified,
         content_kind=sheet.content_kind, budget_s=float(payload.budget_seconds), schedule=schedule, views_meta=(sheet.prep_meta or {}).get("views"), frame=(sheet.prep_meta or {}).get("frame"),
        col_details=known["column_details"], floor_heights=floor_heights, level_hint=level_hint, slab_values=slab_values, text_source=(sheet.prep_meta or {}).get("text_source", "TEXT"), scan_reading=(sheet.prep_meta or {}).get("scan_reading"), pdf_type=(sheet.prep_meta or {}).get("pdf_type"), identity=(sheet.prep_meta or {}).get("identity"),
        lowest_level=lowest_level, with_finishes=True, beam_sections=beam_sections, tank_details=tank_details,
        imperial=units["imperial"], wall_vocab=wall_vocab, footing_sections=footing_sections, spec_facts=spec_facts, electrical=electrical, mark_vocab=mark_vocab, opening_heights=opening_heights)
    except Exception:
      log.exception("PDF extraction failed for sheet %s", sheet.id)
      raise TraceException("This sheet could not be read automatically. Measure it by hand.", status_code=422, code="EXTRACTION_FAILED")
  
    if regions_only and not (result.stats.get("plan_regions") or {}).get("count"):
      raise NoPlanRegions()
    if site_only and not result.candidates:
      raise NoPlanRegions()                                   
    found = result.candidates
    result.stats["sheet_units"] = {"imperial": units["imperial"], "basis": units.get("basis"), "differs": bool(units.get("differs"))}
    if bundle.get("drawings", 1) > 1:
      result.stats["project_facts"] = PF.summary(bundle)
    if units.get("differs"):
      result.notes.append(C.note("SHEET_UNITS_DIFFER", imperial=bool(units["imperial"])))
    result.stats["floors_read_elsewhere"] = await self._repeated_floors(org, sheet, title, result)
    result.stats["drainage_seen"] = DR.seen(found)
    result.stats["drainage_elsewhere"] = await self._repeated_drainage(org, sheet, result)
    result.stats["decisions"] = in_force
    result.stats["company"] = CO.stamp()
    result.stats["rule_book"] = RB.book_ref()
    codes = {c.work_item for c in found if c.work_item}
    catalog = await work_item_catalog(self.session, org, codes) if codes else {}
    KD.drop_unknown_codes(found, catalog)
    await self._view_levels(org, sheet, found)
    added, updated, removed = await self._store(org, sheet, found, mm_per_pt)
    ext = await self.repo.extraction(org, sheet.id)
    
    if ext is None:
      ext = TakeoffExtraction(sheet_id=sheet.id, organization_id=org)
      self.session.add(ext)
    ext.extract_version = C.EXTRACT_VERSION
    ext.index_stamp = index_stamp(meta)
    ext.calibration_id = cal.id
    ext.mm_per_pt = Decimal(str(ev.mm_per_pt))
    ext.scale_unverified = unverified
    ext.stats = result.stats
    ext.unmapped_tags = result.unmapped_tags
    ext.notes = result.notes
    ext.ran_by_user_id = user_id
    ext.updated_at = _now()
    if (sheet.prep_meta or {}).get("read_issue"):
      sheet.prep_meta = {k: v for k, v in sheet.prep_meta.items() if k != "read_issue"}
    
    await self.core._log(org, user_id, sheet.drawing_id, AuditAction.UPDATE,
      f"Read sheet {sheet.page_no} automatically: {len(found)} items found")
    await self.session.flush()
    from app.modules.drawings_boq.takeoff.extract.column_shapes_service import reconcile_columns
    touched = await reconcile_columns(self, org, sheet.drawing_id)
    touched |= await reconcile_beams(self, org, sheet.drawing_id)
    touched |= await reconcile_slab_openings(self, org, sheet.drawing_id)
    touched |= await apply_detail_decisions(self, org, sheet.drawing_id)
    await self._sync_register(org, {sheet.id} | touched)
    await self.session.commit()
    out = await self._list(org, sheet)
    out.update(added=added, updated=updated, removed=removed, calibration_created=created)
    return out

  async def _repeated_floors(self, org: UUID, sheet, title: dict, result) -> list:
    """The floors of this sheet that another sheet of the drawing was also read for (see floor_overlap)."""
    sheets = [s for s in await self.core.repo.sheets(org, sheet.drawing_id) if s.id != sheet.id]
    exts = {e.sheet_id: e for e in await self.repo.extractions(org, [s.id for s in sheets])}
    others = [(s.page_no, exts[s.id].stats, (s.prep_meta or {}).get("title")) for s in sheets if s.id in exts]
    return FO.apply(result.candidates, result.notes, result.stats, title, FO.elsewhere(others), _status)

  async def _repeated_drainage(self, org: UUID, sheet, result) -> list:
    """The drainage items of this sheet that another sheet of the drawing was also read for."""
    sheets = [s for s in await self.core.repo.sheets(org, sheet.drawing_id) if s.id != sheet.id]
    exts = {e.sheet_id: e for e in await self.repo.extractions(org, [s.id for s in sheets])}
    return DR.apply(result.candidates, result.notes, DR.elsewhere([(s.page_no, exts[s.id].stats) for s in sheets if s.id in exts]), _status, sheet.page_no)

  async def _view_levels(self, org: UUID, sheet, found: list) -> None:
    ids: dict = {}
    for c in found:
      view = (c.facts or {}).get("view")
      hint = view.get("level_hint") if view else None
      if not hint:
        continue
      if hint not in ids:
        ids[hint] = await ensure_level(self.session, org, sheet.drawing_id, hint)
      if ids[hint] is not None:
        view["level_id"] = str(ids[hint])

  async def _store(self, org: UUID, sheet, found: list[Candidate], mm_per_pt: float) -> tuple:
    old = {r.ckey: r for r in await self.repo.candidates(org, [sheet.id])}
    await self._heal(org, list(old.values()))
    title = (sheet.prep_meta or {}).get("title") or {}
    sheet_floor = None if title.get("composite") else title.get("level_hint")
    aside = FS.set_aside_floors(list(old.values()), sheet_floor)
    sheet_mark = RV.sheet_mark(list(old.values()))
    added = updated = 0
    seen: set = set()
    for c in found:
      if c.key in seen:
        continue
    
      seen.add(c.key)
      row = old.get(c.key)
      if row is not None and row.decision == "ACCEPTED":
        continue
    
      mark = None
      if row is None:
        row = TakeoffCandidate(organization_id=org, project_id=sheet.project_id, sheet_id=sheet.id, ckey=c.key, decision="NEW")
        self.session.add(row)
        added += 1
        mark = aside.get(FO.level_of(c) or sheet_floor) if c.category != "SLAB" else None
        mark = mark or sheet_mark
        if mark is None and (c.facts or {}).get("drain_repeat"):
          mark = {"by": DR.REPEAT_BY, "page_no": c.facts["drain_repeat"]["page_no"]}
        if mark:
          row.decision, row.decided_at = "REJECTED", _now()
      else:
        updated += 1
        
      chosen = (row.facts or {}).get(CF.CHOICE_KEY) if row.decision == "NEW" else None
      row.category, row.kind, row.quantity_mode, row.label, row.tag = c.category, c.kind, c.quantity_mode, c.label[:200], c.tag
      row.geometry, row.params, row.missing = c.geometry, c.params, c.missing
      row.suggested_work_item, row.count, row.status = c.work_item, c.count, c.status
      kept = mark or ((row.facts or {}).get(FS.SET_ASIDE) if row.decision == "REJECTED" else None)
      row.confidence, row.facts, row.notes, row.source = Decimal(str(c.confidence)), ({**c.facts, FS.SET_ASIDE: kept} if kept else c.facts), c.notes, c.source
      row.extract_version, row.mm_per_pt = C.EXTRACT_VERSION, Decimal(str(mm_per_pt))
      CF.point(row)
      CF.reapply(row, chosen)
    gone = [r.id for k, r in old.items() if k not in seen and r.decision != "ACCEPTED" and not (r.facts or {}).get("from_shapes")]
    await self.repo.delete_candidates(org, gone)
    await self.session.flush()
    return added, updated, len(gone)

  async def _current_sheet_ids(self, org: UUID, sheets: list) -> set:
    out: set = set()
    exts = {e.sheet_id: e for e in await self.repo.extractions(org, [s.id for s in sheets])}
    in_force = decided.effective((await self.core._pdf_drawing(org, sheets[0].drawing_id)).ingestion_meta) if sheets else {}
    for sheet in sheets:
      ext = exts.get(sheet.id)
      if ext is None or sheet.prep_status != "READY" or ext.extract_version != C.EXTRACT_VERSION or decided.stale(ext.stats, in_force):
        continue
      meta = await self.prep.prep.meta(org, sheet.id)
      if meta is not None and ext.index_stamp == index_stamp(meta):
        out.add(sheet.id)
    return out

  async def _note_issue(self, org: UUID, sheet_id: UUID, code: str, message: str, severity: str = "ACTION") -> None:
    """Remembers why a sheet was not read, so the reason is still there after the page is reloaded. INFO needs nothing from the person."""
    sheet = await self.core._sheet(org, sheet_id, lock=True)
    sheet.prep_meta = {**(sheet.prep_meta or {}), "read_issue": {"code": code, "message": message, "severity": severity, "at": _now().isoformat()}}
    await self.session.flush()
    await self.session.commit()

  async def _set_aside(self, org: UUID, sheet_id: UUID, code: str, message: str, severity: str) -> None:
    """A composite sheet whose floors are read from their own sheets: what it listed before is removed, except what was already measured."""
    rows = await self.repo.candidates(org, [sheet_id])
    await self.repo.delete_candidates(org, [r.id for r in rows if r.decision != "ACCEPTED"])
    ext = await self.repo.extraction(org, sheet_id)
    if ext is not None:
      await self.session.delete(ext)
    await self.session.flush()
    await self._note_issue(org, sheet_id, code, message, severity)

  async def extract_drawing(self, org: UUID, drawing_id: UUID, user_id: UUID, payload) -> dict:
    await self.core._pdf_drawing(org, drawing_id)
    sheets = await self.core.repo.sheets(org, drawing_id)
    started = time.monotonic()
    done: list = []
    skipped: list = []
    current = await self._current_sheet_ids(org, sheets) if getattr(payload, "only_unread", False) else set()
    titles = {s.id: dict((s.prep_meta or {}).get("title") or {}) for s in sheets}
    composite = {sid for sid, t in titles.items() if t.get("composite")}
    
    plan = [(s.id, s.page_no) for s in sheets if s.id not in composite] + [(s.id, s.page_no) for s in sheets if s.id in composite]
    singles_read = any(e.sheet_id not in composite for e in await self.repo.extractions(org, [s.id for s in sheets]))
    for sheet_id, page_no in plan:
      if sheet_id in current:
        continue
      if sheet_id in composite:
        issue = composite_issue(titles[sheet_id], singles_read)
        if issue is not None:
          try:
            done.append(await self.extract_sheet(org, sheet_id, user_id, payload, regions_only=True))
            continue
        
          except NoPlanRegions:
            pass
          except TraceException:
            await self.session.rollback()
          try:
            done.append(await self.extract_sheet(org, sheet_id, user_id, payload, site_only=True))
            continue
          except NoPlanRegions:
            pass
          except TraceException:
            await self.session.rollback()
          code, severity, message = issue
          await self._set_aside(org, sheet_id, code, message, severity)
          skipped.append({"sheet_id": str(sheet_id), "page_no": page_no, "code": code, "message": message, "severity": severity})
          continue
      
      if time.monotonic() - started > 80 and done:
        skipped.append({"sheet_id": str(sheet_id), "page_no": page_no, "code": "TIME_BUDGET", "message": "Run it again for the remaining sheets."})
        continue
      try:
        done.append(await self.extract_sheet(org, sheet_id, user_id, payload))
        if sheet_id not in composite:
          singles_read = True
      except TraceException as exc:
        await self.session.rollback()
        skipped.append({"sheet_id": str(sheet_id), "page_no": page_no, "code": exc.code, "message": exc.message, "severity": "ACTION"})
        await self._note_issue(org, sheet_id, exc.code, exc.message, "ACTION")
    return {"drawing_id": drawing_id, "done": done, "skipped": skipped}

  async def accept(self, org: UUID, user_id: UUID, payload) -> dict:
    CO.hold(await CCV.in_force(self.session, org))
    rows = {r.id: r for r in await self.repo.candidates_by_ids(org, list(payload.ids), lock=True)}
    await self._heal(org, list(rows.values()))
    given = payload.work_items or {}
    guard = AG.Guard() if payload.allow_repeat_marks or not rows else await AG.load(self.session, org, next(iter(rows.values())).project_id, list(rows.values()))
    wanted = {c for c in [*(given.values()), *(KD.default_code(r) for r in rows.values())] if c}
    catalog = await work_item_catalog(self.session, org, wanted) if wanted else {}
    typed = {name: getattr(payload, name) for name in ACCEPT_TYPED_FIELDS}
    accepted: list = []
    failed: list = []
    sheet_levels: dict = {}
    sheet_drawings: dict = {}
    concrete_rules: dict = {}
    for cid in payload.ids:
      cand = rows.get(cid)
      
      if cand is None:
        failed.append(_fail(cid, "CANDIDATE_NOT_FOUND", "This item no longer exists. Read the sheet again."))
        continue
      if cand.decision == "ACCEPTED":
        failed.append(_fail(cid, "CANDIDATE_ALREADY_ACCEPTED", "This item is already a measurement."))
        continue
      plan, problem = plan_accept(cand, given, typed, catalog, section_pick=(payload.section_picks or {}).get(cid), steel=(payload.steel or {}).get(cid),
        allow_repeat_marks=bool(payload.allow_repeat_marks))
      if problem:
        failed.append(_fail(cid, *problem))
        continue
      
      params, missing, section, code = plan.params, plan.missing, plan.section, plan.code
      before_params, before_snap = dict(cand.params or {}), CR.snapshot(cand)
      if cand.sheet_id not in sheet_levels:
        sheet_levels[cand.sheet_id] = (await self.core._sheet(org, cand.sheet_id)).level_id
      own_level = view_level_id(cand) or sheet_levels[cand.sheet_id]
      rules: list = []
      
      if GS.member_of(cand) is not None and GS.is_concrete_code(code):
        if cand.sheet_id not in sheet_drawings:
          sheet_drawings[cand.sheet_id] = (await self.core._sheet(org, cand.sheet_id)).drawing_id
        did = sheet_drawings[cand.sheet_id]
        if did not in concrete_rules:
          concrete_rules[did] = ((await printed_for_drawings(self.session, org, [did])).get("grades") or {}).get("concrete") or []
        rules = concrete_rules[did]
      stamp = grade_stamp(cand, code, rules)
      held_by = guard.clash(cand, own_level)
      
      if held_by is not None:
        failed.append(_fail(cid, AG.CODE, held_by))
        continue
      try:
        request = request_for(cand, plan, typed, stamp, payload.level_id or own_level)
      except ValidationError:
        failed.append(_fail(cid, "CANDIDATE_BAD_VALUES", "The values found for this item cannot be used. Draw it by hand."))
        continue
      try:
        async with self.session.begin_nested():
          m = await self.core.create_measurement(org, cand.sheet_id, user_id, request, commit=False)
          cand.decision, cand.measurement_id, cand.decided_by_user_id, cand.decided_at = "ACCEPTED", m.id, user_id, _now()
          apply_accepted(cand, plan, stamp, typed)
      except TraceException as exc:
        failed.append(_fail(cid, exc.code, exc.message))
        continue
    
      if params != before_params:
        await CR.record(self.session, org=org, user_id=user_id, project_id=cand.project_id, sheet_id=cand.sheet_id, kind=CR.ITEM_VALUE_TYPED, subject=cand.tag or cand.label,
          before={**before_snap, "params": before_params}, after={"params": params, "missing": missing, "section": section["mark"] if section else None}, extract_version=cand.extract_version)
      guard.add(cand, own_level)
      accepted.append({"id": str(cid), "measurement_id": str(m.id), "work_item_code": code})
    if accepted:
      first = next(r for r in rows.values() if str(r.id) == accepted[0]["id"])
      sheet = await self.core._sheet(org, first.sheet_id)
      await self.core._log(org, user_id, sheet.drawing_id, AuditAction.CREATE,
        f"Accepted {len(accepted)} automatically found items as draft measurements")
    await self.session.flush()
    await self._sync_register(org, {r.sheet_id for r in rows.values()})
    await self.session.commit()
    return {"accepted": accepted, "failed": failed}

  async def _decide(self, org: UUID, user_id: UUID, ids: list, frm: str, to: str) -> dict:
    rows = {r.id: r for r in await self.repo.candidates_by_ids(org, list(ids), lock=True)}
    await self._heal(org, list(rows.values()))
    changed: list = []
    failed: list = []
    was: dict = {}
    
    for cid in ids:
      r = rows.get(cid)
      if r is None:
        failed.append(_fail(cid, "CANDIDATE_NOT_FOUND", "This item no longer exists."))
      elif r.decision == "ACCEPTED":
        failed.append(_fail(cid, "CANDIDATE_ALREADY_ACCEPTED", "This item is already a measurement. Delete the measurement first."))
      elif r.decision == frm:
        was[cid] = (r.project_id, r.sheet_id, r.extract_version, r.tag or r.label, CR.snapshot(r))
        r.decision, r.decided_by_user_id, r.decided_at = to, (user_id if to == "REJECTED" else None), (_now() if to == "REJECTED" else None)
        changed.append(cid)
    await self.session.flush()
    for cid in changed:
      project_id, sheet_id, version, subject, snap = was[cid]
      await CR.record(self.session, org=org, user_id=user_id, project_id=project_id, sheet_id=sheet_id, kind=CR.ITEM_REJECTED if to == "REJECTED" else CR.ITEM_RESTORED,
        subject=subject, before=snap, extract_version=version)
    if changed:
      await self._sync_register(org, {r.sheet_id for r in rows.values()})
    await self.session.commit()
    return {"changed": changed, "failed": failed}

  async def reject(self, org: UUID, user_id: UUID, ids: list) -> dict:
    return await self._decide(org, user_id, ids, "NEW", "REJECTED")

  async def restore(self, org: UUID, user_id: UUID, ids: list) -> dict:
    return await self._decide(org, user_id, ids, "REJECTED", "NEW")
