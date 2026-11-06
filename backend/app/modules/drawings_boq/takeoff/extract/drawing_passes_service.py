from __future__ import annotations
import copy
import json
from datetime import datetime, timezone
from app.modules.drawings_boq.takeoff.extract.pipeline import Candidate
from app.modules.drawings_boq.models import TakeoffCandidate
from app.modules.drawings_boq.takeoff.extract import stair_rise as SRS
from app.modules.drawings_boq.takeoff.extract import wall_steel as WST
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.extract import electrical as EL
from app.modules.drawings_boq.takeoff.extract import tank_record as TR
from decimal import Decimal
from uuid import UUID
from app.modules.drawings_boq.takeoff.extract import floor_sources as FS
from app.modules.drawings_boq.takeoff.extract import member_passes as MP

META_KEY = "takeoff_passes"
PROBLEMS_KEY = "structure_problems"
FIELDS = ("label", "tag", "geometry", "params", "missing", "status", "facts", "notes")

def _now() -> datetime:
  return datetime.now(timezone.utc)

def to_candidate(row: TakeoffCandidate) -> Candidate:
  c = Candidate(key=row.ckey, category=row.category, kind=row.kind, quantity_mode=row.quantity_mode, label=row.label, tag=row.tag, geometry=copy.deepcopy(row.geometry or {}),
    params=copy.deepcopy(row.params or {}), missing=list(row.missing or []), work_item=row.suggested_work_item, status=row.status, confidence=float(row.confidence),
    facts=copy.deepcopy(row.facts or {}), notes=copy.deepcopy(row.notes or []), source=row.source, count=row.count)
  c.decision = row.decision
  return c

def snapshot(c: Candidate) -> str:
  return json.dumps([getattr(c, k) for k in FIELDS], sort_keys=True, default=str)

def deduplicated(notes: list) -> list:
  seen: set = set()
  out: list = []
  for n in notes or []:
    key = json.dumps(n, sort_keys=True, default=str)
    if key not in seen:
      seen.add(key)
      out.append(n)
  return out

STEEL_BY_PASS = "bar strings of the RCC wall sections"
STEEL_NOTES = ("WALL_STEEL_FROM_SECTIONS", "WALL_STEEL_ZONES_AVERAGED")

def undo_wall_steel(c: Candidate) -> None:
  if not str(((c.facts or {}).get("steel_source") or {}).get("text") or "").startswith(STEEL_BY_PASS):
    return
  c.params = {k: v for k, v in c.params.items() if k != "steel"}
  c.facts = {k: v for k, v in c.facts.items() if k not in ("steel_text", "steel_source", "wall_steel")}
  c.notes = [n for n in c.notes if n.get("code") not in STEEL_NOTES]

TANK_NOTES = ("TANK_RECORD_BUILT", "TANK_DEPTH_BY_RULE", "TANK_WALL_BY_RULE", "TANK_PLAN_FROM_WALLS", "TANK_SIZE_DEFAULTED")

def undo_tank_notes(c: Candidate) -> None:
  if c.category == "SITE" and (c.facts or {}).get("tank_kind") in TR.KINDS:
    c.notes = [n for n in c.notes if n.get("code") not in TANK_NOTES]

def usable(row: TakeoffCandidate) -> bool:
  if row.decision == "ACCEPTED":
    return False
  return row.decision == "NEW" or bool((row.facts or {}).get(FS.SET_ASIDE))

def sheet_dict(sheet, ext, cands: list) -> dict:
  meta = copy.deepcopy(sheet.prep_meta or {})
  return {"sheet_id": sheet.id, "page_no": sheet.page_no, "title": meta.get("title") or {}, "meta": meta, "stats": (ext.stats if ext is not None else None) or {},
    "mm_per_pt": float(ext.mm_per_pt) if ext is not None and ext.mm_per_pt else None, "candidates": cands}

def typed_tank_decisions(meta: dict | None) -> dict:
  raw = (meta or {}).get("takeoff_decisions") or {}
  return {k: str(v.get("value")) for k, v in raw.items() if k.startswith(TR.DECISION_PREFIX) and isinstance(v, dict)}

def run_passes(read: list, heights: dict | None, decisions: dict | None = None) -> dict:
  SRS.apply(read, heights)
  steel = WST.apply(read, C.note)
  coverage = EL.coverage(read)
  tanks = TR.pair(read, decisions or {})
  return {"wall_steel": steel, "electrical": coverage, "tanks": tanks}

def plain(value):
  return json.loads(json.dumps(value, default=str))

async def reconcile_drawing_passes(svc, org: UUID, drawing_id: UUID) -> set:
  sheets = await svc.core.repo.sheets(org, drawing_id)
  if not sheets:
    return set()
  exts = {e.sheet_id: e for e in await svc.repo.extractions(org, [s.id for s in sheets])}
  rows_all = await svc.repo.candidates(org, [s.id for s in sheets if s.id in exts])
  
  by_sheet: dict = {}
  for row in rows_all:
    if usable(row):
      by_sheet.setdefault(row.sheet_id, []).append(row)
  drawing = await svc.core._pdf_drawing(org, drawing_id)
  heights = (await svc.prep.drawing_floor_heights(org, drawing_id)).get("heights")
  read, rows_of, before = [], {}, {}
  for s in sorted(sheets, key=lambda x: x.page_no):
    if s.id not in exts:
      continue
  
    cands = []
    for row in by_sheet.get(s.id, []):
      c = to_candidate(row)
      rows_of[(s.id, c.key)] = row
      before[(s.id, c.key)] = snapshot(c)
      undo_wall_steel(c)
      undo_tank_notes(c)
      cands.append(c)
    read.append(sheet_dict(s, exts[s.id], cands))
    
  gone = MP.reset(read)
  made_before = {(row["sheet_id"], c.key) for row, c in gone}
  held = {(r.sheet_id, r.ckey) for r in rows_all if not usable(r)}
  bundle = await svc.prep.fact_bundle(org, drawing)
  problems = MP.run(read, svc.prep._floor_keys(sheets), bundle["facts"]["storey_heights"], **MP.inputs_of(drawing.ingestion_meta))
  for sh in read:
    sh["candidates"] = [c for c in sh["candidates"] if not (MP.generated(c) and (sh["sheet_id"], c.key) in held)]
  result = run_passes(read, heights, typed_tank_decisions(drawing.ingestion_meta))
  
  touched: set = set()
  for sh in read:
    sid = sh["sheet_id"]
    sheet = next(x for x in sheets if x.id == sid)
    
    for c in sh["candidates"]:
      c.notes = deduplicated(c.notes)
      row = rows_of.get((sid, c.key))
      if row is None:
        new = TakeoffCandidate(organization_id=org, project_id=sheet.project_id, sheet_id=sid, ckey=c.key, decision="NEW", category=c.category, kind=c.kind, quantity_mode=c.quantity_mode,
          label=c.label[:200], tag=c.tag, geometry=c.geometry, params=c.params, missing=c.missing, suggested_work_item=c.work_item, count=c.count, status=c.status,
          confidence=Decimal(str(c.confidence)), facts=c.facts, notes=c.notes, source=c.source, extract_version=C.EXTRACT_VERSION, mm_per_pt=exts[sid].mm_per_pt)
        if FS.is_set_aside(c):
          new.decision, new.decided_at = "REJECTED", _now()
        svc.session.add(new)
        touched.add(sid)
        continue
      if snapshot(c) == before[(sid, c.key)]:
        continue
    
      row.label, row.tag, row.geometry, row.params, row.missing = c.label[:200], c.tag, c.geometry, c.params, c.missing
      row.status, row.facts, row.notes = c.status, c.facts, c.notes
      aside = FS.is_set_aside(c)
      if aside and row.decision == "NEW":
        row.decision, row.decided_at = "REJECTED", _now()
      elif not aside and row.decision == "REJECTED":
        row.decision, row.decided_at = "NEW", None
      touched.add(sid)
      
  made_now = {(sh["sheet_id"], c.key) for sh in read for c in sh["candidates"]}
  for key in made_before - made_now:
    row = rows_of.get(key)
    if row is not None and row.decision == "NEW":
      row.decision, row.decided_at = "REJECTED", _now()
      touched.add(key[0])
      
  drawing.ingestion_meta = {**(drawing.ingestion_meta or {}), META_KEY: plain(result), PROBLEMS_KEY: plain(problems)}
  await svc.session.flush()
  return touched
