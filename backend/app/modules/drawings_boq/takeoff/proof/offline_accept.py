from __future__ import annotations
from app.modules.drawings_boq.takeoff.proof.offline_run import NAMESPACE, work_item_catalog
from app.modules.drawings_boq.takeoff import approve_pick as AP
from uuid import UUID, uuid5
from app.modules.drawings_boq.models import TakeoffSheet, TakeoffCandidate, TakeoffCalibration, TakeoffMeasurement
from decimal import Decimal
import copy
from dataclasses import dataclass, field
from app.core.exceptions import TraceException
from app.modules.drawings_boq.takeoff.prep_service import PrepService
from app.modules.drawings_boq.takeoff.levels import LEVELS, KEY_PREFIX, view_level_id
from app.modules.drawings_boq.takeoff.extract import floor_sources as FS
from app.engine.measure import takeoff as tk
from pydantic import ValidationError
from app.modules.drawings_boq.takeoff.proof import benchmark as BM
from app.modules.drawings_boq.takeoff import repository as repo_mod
from types import SimpleNamespace
from app.modules.drawings_boq.takeoff import service as svc_mod
from app.modules.drawings_boq.takeoff.extract import ready as RD
from app.modules.drawings_boq.takeoff.extract import slab_openings as SO
from app.modules.drawings_boq.takeoff.extract import slab_openings_service as SOS
from app.modules.drawings_boq.takeoff.extract import beam_overlap_service as BOS
from app.modules.drawings_boq.takeoff.prep import facts as drawing_facts, printed_params
from app.modules.drawings_boq.takeoff.extract import extract_service as ES
from app.modules.drawings_boq.takeoff import z_range as Z
from app.modules.drawings_boq.takeoff.extract import accept_guard as AG
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff import space_loader as SL

ORG = uuid5(NAMESPACE, "organisation")
PROJECT = uuid5(NAMESPACE, "project")
BATCH = AP.DEFAULT_BATCH
MAX_ROUNDS = 80
ALL_POLICY = {"accept_assumed": True, "accept_warned": True, "accept_added": False}      
READY_POLICY = {"accept_assumed": False, "accept_warned": False, "accept_added": False}  

def uid(*parts) -> UUID:
  return uuid5(NAMESPACE, "|".join(str(p) for p in parts))

@dataclass
class Accepted:
  case: str
  drawings: dict = field(default_factory=dict)          
  sheets: dict = field(default_factory=dict)            
  read: dict = field(default_factory=dict)              
  candidates: list = field(default_factory=list)
  calibrations: list = field(default_factory=list)
  measurements: list = field(default_factory=list)      
  floor_of: dict = field(default_factory=dict)          
  meta: dict = field(default_factory=dict)              
  printed: dict = field(default_factory=dict)           
  problems: list = field(default_factory=list)
  tally: dict = field(default_factory=dict)

def _sheet_for(case: str, drawing_id: UUID, r: dict, levels: dict) -> TakeoffSheet:
  title = r.get("title") or {}
  hint = None if title.get("composite") else title.get("level_hint")
  meta = dict(r.get("meta") or {})
  meta.setdefault("user_unit", 1)
  return TakeoffSheet(id=uid(case, drawing_id, "sheet", r["page_no"]), organization_id=ORG, project_id=PROJECT, drawing_id=drawing_id, page_no=r["page_no"], width_pt=Decimal(1),
    height_pt=Decimal(1), rotation=0, content_kind=r.get("content_kind") or "UNKNOWN", label=None, level_id=levels.get(hint) if hint else None, scale_text=None, detected_scale={},
    prep_status="READY", prep_error=None, prep_meta=meta)

def _levels(case: str, drawing_id: UUID, read: list) -> tuple:
  hints: set = set()
  for r in read:
    title = r.get("title") or {}
    if title.get("level_hint") and not title.get("composite"):
      hints.add(title["level_hint"])
    for c in r["candidates"]:
      v = (c.facts or {}).get("view")
      if v and v.get("level_hint"):
        hints.add(v["level_hint"])

  ids = {h: uid(case, drawing_id, "level", h) for h in sorted(h for h in hints if h in LEVELS)}
  return ids, {v: k for k, v in ids.items()}

def _candidate(c, sheet: TakeoffSheet, mm_per_pt: float, levels: dict) -> TakeoffCandidate:
  facts = copy.deepcopy(c.facts or {})
  view = facts.get("view")
  if view and view.get("level_hint") in levels:
    view["level_id"] = str(levels[view["level_hint"]])

  return TakeoffCandidate(
    id=uid(sheet.id, "candidate", c.key), organization_id=ORG, project_id=PROJECT, sheet_id=sheet.id, ckey=c.key, category=c.category, kind=c.kind, quantity_mode=c.quantity_mode,
    label=c.label[:200], tag=c.tag, geometry=copy.deepcopy(c.geometry), params=copy.deepcopy(c.params), missing=list(c.missing), suggested_work_item=c.work_item, count=c.count,
    status=c.status, confidence=Decimal(str(c.confidence)), facts=facts, notes=copy.deepcopy(c.notes), source=c.source,
    decision="REJECTED" if FS.is_set_aside(c) else "NEW", measurement_id=None, mm_per_pt=Decimal(str(mm_per_pt)), extract_version=C.EXTRACT_VERSION, decided_at=None)

def _apply_slab_openings(sheets: list, read: list) -> None:
  exts = {r["sheet_id"]: SimpleNamespace(stats=r.get("stats") or {}) for r in read}
  rows = [c for r in read for c in r["candidates"]]
  levels = SO.by_level(sheets, exts)
  known = {(c.facts or {}).get("floor") for c in rows if c.category == "SLAB"} | set(levels)
  SOS.annotate(rows, SO.place(levels, {k for k in known if k}))

def _apply_beam_sources(sheets: list, read: list) -> None:
  exts = {r["sheet_id"]: SimpleNamespace(stats=r.get("stats") or {}) for r in read}
  rows = [c for r in read for c in r["candidates"]]
  BOS.annotate(rows, BOS.strips_by_level(sheets, exts), BOS.walls_by_level(rows, {s.id: s.page_no for s in sheets}))

def _calibration(case: str, sheet: TakeoffSheet, ratio: float) -> TakeoffCalibration:
  text = f"1:{ratio:g}"
  built = svc_mod.build_calibration("SCALE_RATIO", None, Decimal(str(round(ratio, 6))), text, None, repo_mod.sheet_user_unit(sheet))
  return TakeoffCalibration(id=uid(sheet.id, "calibration"), organization_id=ORG, sheet_id=sheet.id, method="SCALE_RATIO", ref=built["ref"], check_ref=built["check_ref"], ratio=built["ratio"],
    label=text, is_default=True, usable=built["usable"], reason=built["reason"], mm_per_pt=built["mm_per_pt"], check_error_pct=built["check_error_pct"], baseline_pt=built["baseline_pt"],
    quality_factor=built["quality_factor"], warnings=built["warnings"])

def _measurement(case: str, sheet: TakeoffSheet, cand: TakeoffCandidate, request, cal) -> TakeoffMeasurement:
  svc_mod.TakeoffService._check_mode(request.kind, request.quantity_mode)
  code = (request.work_item_code or "").strip() or None
  if code in tk.RESERVED_CODES:
    raise TraceException(f"{code} is measured from bar schedules or the model, not from a PDF drawing.", status_code=422, code="WORK_ITEM_RESERVED")
  try:
    geometry = tk.normalized_geometry(request.kind, request.geometry)
  except tk.TakeoffError as exc:
    raise svc_mod._fail(exc)

  use = cal if tk.needs_calibration(request.kind, request.quantity_mode) else None
  return TakeoffMeasurement(
    id=uid(cand.id, "measurement"), organization_id=ORG, project_id=PROJECT, sheet_id=sheet.id, calibration_id=use.id if use is not None else None, kind=request.kind,
    quantity_mode=request.quantity_mode, geometry=geometry, params=svc_mod.TakeoffService._params_json(request.params), work_item_code=code,
    level_id=request.level_id if request.level_id is not None else sheet.level_id, label=(request.label or "").strip() or None, tag=(request.tag or "").strip() or None,
    material_grade=(request.material_grade or "").strip() or None, recon_mode=request.recon_mode, source=request.source, status="DRAFT",
    geometry_hash=tk.geometry_hash(request.kind, geometry), computed=None)

def _fail_text(exc) -> tuple:
  return (getattr(exc, "code", None) or type(exc).__name__, getattr(exc, "message", None) or str(exc))

def accept_case(case: str, reads: list, profile, *, ready_only: bool = False, policy: dict | None = None) -> Accepted:
  policy = policy or (READY_POLICY if ready_only else ALL_POLICY)
  catalog = work_item_catalog()
  typed = {name: None for name in ES.ACCEPT_TYPED_FIELDS}
  out = Accepted(case=case)
  guard = AG.Guard()
  by_id: dict = {}
  sheet_of_cand: dict = {}
  cals: dict = {}

  wanted_all = {"ready_only": 0, "all": 0}
  for pdf_name, rows in reads:
    drawing_id = uid(case, "drawing", pdf_name)
    out.drawings[drawing_id] = pdf_name
    BM.choose_floor_sources(rows)
    level_ids, floor_of = _levels(case, drawing_id, rows)
    out.floor_of.update(floor_of)
    sheets, read_for_ready = {}, []

    for r in rows:
      sheet = _sheet_for(case, drawing_id, r, level_ids)
      sheets[r["page_no"]] = sheet
      out.sheets[sheet.id] = sheet
      cands = [_candidate(c, sheet, r["mm_per_pt"], level_ids) for c in r["candidates"]]
      for c in cands:
        by_id[str(c.id)] = c
        sheet_of_cand[c.id] = sheet
      out.candidates.extend(cands)
      if r.get("ratio") is None:
        out.problems.append({"pdf": pdf_name, "page": r["page_no"], "code": "SCALE_DEFAULTED", "message": "No scale could be measured on this sheet; it was read at 1:100."})
      cal = _calibration(case, sheet, float(r["ratio"]) if r.get("ratio") else 100.0)
      cals[sheet.id] = cal
      read_for_ready.append({"sheet_id": sheet.id, "page_no": r["page_no"], "title": r.get("title"), "stats": r.get("stats"), "candidates": cands, "schedule": r.get("schedule")})
    out.read[drawing_id] = read_for_ready
    gathered = drawing_facts.gather([{"page_no": r["page_no"], "label": None, "facts": r.get("facts")} for r in rows if r.get("facts") is not None])
    out.printed[drawing_id] = printed_params.from_items(gathered["items"])
    out.meta[drawing_id] = PrepService.floor_heights_from([SimpleNamespace(page_no=r["page_no"], label=None, prep_meta=r.get("meta") or {}) for r in rows])
    _apply_slab_openings(list(sheets.values()), read_for_ready)
    _apply_beam_sources(list(sheets.values()), read_for_ready)
  
  failed_ids: set = set()
  refused: dict = {}
  drafts: list = []

  for drawing_id, read in out.read.items():
    concrete_rules = (out.printed[drawing_id].get("grades") or {}).get("concrete") or []
    for rnd in range(MAX_ROUNDS):
      rd = RD.ready(read)
      if rnd == 0:
        wanted_all["ready_only"] += len(AP.pick(rd, **READY_POLICY, typed={}, exclude=failed_ids)["ids"])
        wanted_all["all"] += len(AP.pick(rd, **ALL_POLICY, typed={}, exclude=failed_ids)["ids"])
      chosen = AP.pick(rd, **policy, typed={}, exclude=failed_ids)
      take = chosen["ids"][:BATCH]
      if not take:
        out.tally.setdefault("skipped_by_reason", {})
        for k, v in chosen["skipped"].items():
          out.tally["skipped_by_reason"][k] = out.tally["skipped_by_reason"].get(k, 0) + v
        break
      progress = False
      for cid in take:
        cand = by_id[cid]
        sheet = sheet_of_cand[cand.id]
        plan, problem = ES.plan_accept(cand, given={}, typed=typed, catalog=catalog)
        if problem:
          failed_ids.add(cid)
          refused[problem[0]] = refused.get(problem[0], 0) + 1
          continue
        own_level = view_level_id(cand) or sheet.level_id
        stamp = ES.grade_stamp(cand, plan.code, concrete_rules)
        held_by = guard.clash(cand, own_level)
        if held_by is not None:
          failed_ids.add(cid)
          refused[AG.CODE] = refused.get(AG.CODE, 0) + 1
          continue
        try:
          request = ES.request_for(cand, plan, typed, stamp, own_level)
        except ValidationError:
          failed_ids.add(cid)
          refused["CANDIDATE_BAD_VALUES"] = refused.get("CANDIDATE_BAD_VALUES", 0) + 1
          continue
        try:
          m = _measurement(case, sheet, cand, request, cals[sheet.id])
        except TraceException as exc:
          failed_ids.add(cid)
          refused[exc.code] = refused.get(exc.code, 0) + 1
          continue

        cand.decision, cand.measurement_id = "ACCEPTED", m.id
        ES.apply_accepted(cand, plan, stamp, typed)
        guard.add(cand, own_level)
        drafts.append((m, sheet))
        progress = True
      if not progress:
        break

  profile_of = profile
  confirmed_failed: dict = {}
  twins: set = set()
  used_cals: dict = {}

  for m, sheet in drafts:
    cal = cals[sheet.id] if m.calibration_id else None
    try:
      svc_mod.confirm_precheck(m)
      wi = catalog.get(m.work_item_code)
      if wi is None:
        raise TraceException(f"Work item {m.work_item_code} was not found.", status_code=404, code="WORK_ITEM_NOT_FOUND")
      comp = svc_mod.confirm_computed(repo_mod.measurement_input(m), repo_mod.sheet_input(sheet), wi, cal,
        repo_mod.calibration_input(cal, repo_mod.sheet_user_unit(sheet)) if cal is not None else None, profile_of)
      twin = (m.sheet_id, m.geometry_hash, m.work_item_code, m.quantity_mode)

      if twin in twins:
        raise TraceException("The same extent is already confirmed for this work item on this sheet; confirming it again would count it twice.", status_code=422, code="DUPLICATE_MEASUREMENT")
      twins.add(twin)
    except TraceException as exc:
      confirmed_failed[exc.code] = confirmed_failed.get(exc.code, 0) + 1
      continue
    m.computed = svc_mod.computed_json(comp)
    m.status = "CONFIRMED"
    out.measurements.append(m)
    if cal is not None:
      used_cals[cal.id] = cal

  out.calibrations = [used_cals[k] for k in sorted(used_cals, key=str)]
  out.tally.update({"candidates": len(out.candidates), "ready_would_accept": wanted_all["ready_only"], "all_would_accept": wanted_all["all"], "accepted": len(drafts),
    "accept_refused": dict(sorted(refused.items())), "confirmed": len(out.measurements), "confirm_refused": dict(sorted(confirmed_failed.items())),
    "policy": "ready_only" if policy == READY_POLICY else "all"})
  return out

def _datums(acc: Accepted) -> dict:
  out: dict = {}
  for drawing_id, prepared in acc.meta.items():
    floors = Z.build_floors(prepared["heights"], prepared["floor_keys"])
    out[drawing_id] = (floors, Z.FootingLevel(Z.ngl_from_marks(floors, prepared["levels_mm"]), None, Z.MARK_NGL, Z.datum_of(floors)))
  return out

def build_inputs(acc: Accepted):
  ms = sorted(acc.measurements, key=lambda m: str(m.id))
  if not ms:
    return None

  sheets = {m.sheet_id: acc.sheets[m.sheet_id] for m in ms}
  cands = {c.measurement_id: c for c in acc.candidates if c.decision == "ACCEPTED" and c.measurement_id}
  mid = {m.id for m in ms}
  mem_by = {i: c for i, c in cands.items() if i in mid and c.category in repo_mod.MEMBER_CATEGORIES and next(m for m in ms if m.id == i).quantity_mode == "COUNT_X_VOLUME"}
  fw_by = repo_mod.formwork_candidates([c for i, c in cands.items() if i in mid and c.category in (*repo_mod.FORMWORK_CATEGORIES, "WALL", "SITE")

    and next(m for m in ms if m.id == i).quantity_mode in ("COUNT_X_VOLUME", "LENGTH_X_HEIGHT_X_THICKNESS")])
  present = set(repo_mod.member_element_ids(ms, sheets, mem_by)) | set(repo_mod.formwork_element_ids(ms, sheets, fw_by))     
  members = repo_mod.members_from(ms, sheets, mem_by, present) if mem_by else ()
  formwork = repo_mod.formwork_from(ms, sheets, fw_by, present) if fw_by else ()
  sp_by = {i: c for i, c in cands.items() if i in mid and c.category in SL.SPACE_CATEGORIES and next(m for m in ms if m.id == i).quantity_mode in SL.SPACE_MODES}
  space, floors = (), ()

  if sp_by:
    need = {sheets[m.sheet_id].id for m in ms if m.id in sp_by and (sp_by[m.id].facts or {}).get("derived_from") == "WALLS"}
    walls = {(c.sheet_id, c.ckey): c for c in acc.candidates if c.sheet_id in need and c.category == "WALL"}
    space, floors = SL.space_from(ms, sheets, sp_by, acc.floor_of, walls, _datums(acc))
  ranges = repo_mod.ranges_from([c for i, c in cands.items() if i in mid])
  return repo_mod.takeoff_inputs_from(sheets, acc.calibrations, ms, members, formwork, {}, space, floors, ranges)
