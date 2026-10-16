from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract.pipeline import Candidate, _finish, _fmt_mm, _height_note, _key, _status, _with_floor_height
from app.modules.drawings_boq.takeoff.extract import kinds as KD
from app.modules.drawings_boq.takeoff.extract import column_census as CS
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.levels import level_spec
from uuid import UUID
from app.modules.drawings_boq.models import TakeoffCandidate
from decimal import Decimal
from datetime import datetime, timezone
from app.modules.drawings_boq.finish_schedule.common import work_item_catalog

def _now() -> datetime:
  return datetime.now(timezone.utc)

def _candidate(entry: dict, floor: dict, ext, heights: dict | None) -> Candidate:
  a, b = float(entry["a_mm"]), float(entry["b_mm"])
  work_item, mode, kind = C.SUGGESTIONS["COLUMN"]
  h = (heights or {}).get("COLUMN")
  seen = entry["count"] - int(entry.get("inferred") or 0)
  points = [list(p) for p in entry.get("points") or []]
  unplaced = max(0, entry["count"] - len(points))
  notes = [C.note("COLUMN_SHAPES_WITHOUT_MARK", drawn=seen, tags=entry.get("tags") or [], page=floor["page_no"])]
  if entry.get("inferred"):
    notes.append(C.note("COLUMN_FROM_FLOOR_ABOVE", inferred=entry["inferred"], floor=entry["inferred_from"]))
  if unplaced:
    notes.append(C.note("COLUMN_NOT_PLACED", unplaced=unplaced))
  if h:
    notes.append(_height_note(h))
  spec = level_spec(floor["level"])
  tag = entry.get("tag")
  
  label = f"{tag or 'Columns (no mark)'} ×{entry['count']} · {_fmt_mm(a)}×{_fmt_mm(b)} mm" + (f" · {spec[0]}" if spec else "")
  facts = {"tag": tag, "count": entry["count"], "size_drawn_mm": [a, b], "size_used_mm": [a, b], "from_shapes": True, "level_hint": floor["level"],
    "candidate_tags": entry.get("tags") or [], "shapes_drawn": seen, "matches_marks": bool(entry.get("matches_marks"))}
  if entry.get("inferred"):
    facts["inferred"], facts["inferred_from"] = entry["inferred"], entry["inferred_from"]
  cand = Candidate(key=_key("COLUMN", "SHAPES", floor["level"], round(a), round(b)), category="COLUMN", kind=kind, quantity_mode=mode, label=label, tag=tag,
    geometry={"points": points}, params={"length_mm": a, "width_mm": b, "dims_basis": "DRAWN", **({"depth_mm": h["mm"]} if h else {})},
    missing=[] if h else ["height_mm"], work_item=work_item, status="VALID", confidence=0.0, facts=facts, notes=notes, source="TAG_SCAN", count=entry["count"])
  ctx = {"cal_factor": 1.0, "content_factor": 1.0, "scale_unverified": bool(getattr(ext, "scale_unverified", False))}
  return _finish(cand, ctx, 0.55 if entry.get("inferred") or unplaced else 0.65)

def _read(sheets: list, exts: dict) -> tuple:
  """(floors, details): per floor, the census of its plan (the lowest page that has one) and the marks of its framing plan."""
  floors: dict = {}
  details: dict = {}
  
  for s in sorted(sheets, key=lambda x: x.page_no):
    st = (exts[s.id].stats or {}) if s.id in exts else {}
    shapes = st.get("column_shapes")
    if shapes and shapes.get("level_hint"):
      row = floors.setdefault(shapes["level_hint"], {"level": shapes["level_hint"], "marks": [], "shapes": None})
      if row["shapes"] is None:
        row["shapes"], row["sheet_id"], row["page_no"] = shapes, s.id, s.page_no
    for v in st.get("views") or []:
      if v.get("level_hint") and not v.get("foundation") and v.get("column_marks"):
        floors.setdefault(v["level_hint"], {"level": v["level_hint"], "marks": [], "shapes": None})["marks"] = v["column_marks"]
    details.update(st.get("column_details") or {})
  return list(floors.values()), details

def _flag_short_marks(rows: list, planned: list) -> set:
  short = {(r["level"], CS.norm_mark(s["tag"]) if s.get("tag") else ""): (s, r) for r in planned for s in r["result"]["short"]}
  
  changed: set = set()
  for row in rows:
    f = row.facts or {}
    if row.category != "COLUMN" or f.get("from_shapes") or f.get("neck_of") or row.decision == "ACCEPTED" or not row.tag:
      continue
    level = (f.get("view") or {}).get("level_hint")
    hit = short.get((level, CS.norm_mark(row.tag)))
    notes = [n for n in (row.notes or []) if n.get("code") != "COLUMN_MARKS_EXCEED_SHAPES"]
    if hit and hit[0]["count"] == row.count:
      notes.append(C.note("COLUMN_MARKS_EXCEED_SHAPES", marks=hit[0]["count"], shapes=hit[0]["shapes"], page=hit[1]["page_no"]))
    if notes != (row.notes or []):
      row.notes = notes
      row.status = _status(notes)
      changed.add(row.sheet_id)
  return changed

async def reconcile_columns(svc, org: UUID, drawing_id: UUID) -> set:
  """Brings the shape columns of every floor plan of the drawing up to date. Returns the ids of the sheets whose items changed."""
  sheets = await svc.core.repo.sheets(org, drawing_id)
  exts = {e.sheet_id: e for e in await svc.repo.extractions(org, [s.id for s in sheets])}
  floors, details = _read(sheets, exts)
  planned = CS.plan(floors, details)
  by_sheet = {s.id: s for s in sheets}
  holders = {r["sheet_id"] for r in planned}
  
  old: dict = {}
  rows_all = await svc.repo.candidates(org, [s.id for s in sheets if s.id in exts])
  for row in rows_all:
    if (row.facts or {}).get("from_shapes"):
      old[(row.sheet_id, row.ckey)] = row
  floor_heights = await svc.prep.drawing_storey_heights(org, drawing_id) if planned else {}
  wanted: dict = {}
  for r in planned:
    heights = _with_floor_height({}, floor_heights, r["level"])
    for e in r["result"]["extra"]:
      c = _candidate(e, r, exts[r["sheet_id"]], heights)
      wanted[(r["sheet_id"], c.key)] = c
  catalog = {}
  
  codes = {c.work_item for c in wanted.values() if c.work_item}
  if codes:
    catalog = await work_item_catalog(svc.session, org, codes)
  KD.drop_unknown_codes(list(wanted.values()), catalog)
  changed: set = set()
  for (sheet_id, key), c in wanted.items():
    row = old.get((sheet_id, key))
    if row is not None and row.decision == "ACCEPTED":
      continue
  
    ext = exts[sheet_id]
    if row is None:
      row = TakeoffCandidate(organization_id=org, project_id=by_sheet[sheet_id].project_id, sheet_id=sheet_id, ckey=key, decision="NEW")
      svc.session.add(row)
    row.category, row.kind, row.quantity_mode, row.label, row.tag = c.category, c.kind, c.quantity_mode, c.label[:200], c.tag
    row.geometry, row.params, row.missing = c.geometry, c.params, c.missing
    row.suggested_work_item, row.count, row.status = c.work_item, c.count, c.status
    row.confidence, row.facts, row.notes, row.source = Decimal(str(c.confidence)), c.facts, c.notes, c.source
    row.extract_version, row.mm_per_pt = C.EXTRACT_VERSION, ext.mm_per_pt
    changed.add(sheet_id)
    
  changed |= _flag_short_marks(rows_all, planned)
  gone = [row.id for k, row in old.items() if k not in wanted and row.decision != "ACCEPTED"]
  if gone:
    changed.update(row.sheet_id for k, row in old.items() if k not in wanted and row.decision != "ACCEPTED")
    await svc.repo.delete_candidates(org, gone)
  await svc.session.flush()
  return changed
