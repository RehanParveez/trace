from __future__ import annotations
import copy
import hashlib
import math
import re
from app.modules.drawings_boq.takeoff.extract import beam_bands as BBD
from app.modules.drawings_boq.takeoff.extract import beam_sections as BS
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.extract import note_scope as NS
from app.modules.drawings_boq.takeoff.prep.details import norm_mark

INCH_MM = 25.4
ZONES = ((0.0, 0.25, "END"), (0.25, 0.75, "MID"), (0.75, 1.0, "END"))
KINDS = {"THR": "THROUGH", "EXT": "EXTRA"}
BAR = re.compile(r"^(?P<n>\d{1,2})\s*-\s*#(?P<dia>\d{1,2})\s*(?P<kind>Thr|Ext)?\.?$", re.I)
STIRRUP = re.compile(r"^#(?P<dia>\d{1,2})\s*@\s*(?P<end>\d+(?:\.\d+)?)\s*[\"”]?(?:\s*/\s*(?P<mid>\d+(?:\.\d+)?)\s*[\"”]?)?\s*C\s*/?\s*C$", re.I)
SOURCE = "STRUCTURE_TABLE"

def parse_bar(text: str) -> dict | None:
  m = BAR.match(str(text or "").strip())
  if not m:
    return None
  return {"n": int(m.group("n")), "dia": int(m.group("dia")), "kind": KINDS.get((m.group("kind") or "").upper()[:3], "UNKNOWN"), "text": str(text).strip()}

def parse_stirrup(text: str) -> dict | None:
  m = STIRRUP.match(str(text or "").replace(" ", ""))
  if not m:
    return None
  end = float(m.group("end"))
  mid = float(m.group("mid") or end)
  return {"dia": int(m.group("dia")), "end_mm": round(end * INCH_MM, 1), "mid_mm": round(mid * INCH_MM, 1), "text": str(text).strip()}

def zones(stirrup: dict | None) -> list:
  if not stirrup:
    return []
  return [{"from": a, "to": b, "zone": z, "spacing_mm": stirrup["end_mm"] if z == "END" else stirrup["mid_mm"]} for a, b, z in ZONES]

def section_bars(sec: dict) -> dict:
  top = [parse_bar(t) for t in sec.get("top_bars") or []]
  bottom = [parse_bar(t) for t in sec.get("bottom_bars") or []]
  stirrup = parse_stirrup(sec.get("stirrup"))
  whole = all(top) and all(bottom) and bool(top) and bool(bottom) and stirrup is not None
  return {"top": [b for b in top if b], "bottom": [b for b in bottom if b], "stirrup": stirrup, "zones": zones(stirrup), "read": "WHOLE" if whole else "PARTIAL",
    "unparsed": [t for t, b in zip((sec.get("top_bars") or []) + (sec.get("bottom_bars") or []), top + bottom) if b is None] + ([sec["stirrup"]] if sec.get("stirrup") and stirrup is None else [])}

def table_sections(sheets: list, existing: list | None) -> list:
  have = {norm_mark(str(s.get("mark"))) for s in existing or []}
  out = list(existing or [])
  for sh in sheets:
    tab = ((getattr(sh, "prep_meta", None) or {}).get("structure_tables") or {}).get("beam_sections") or {}
    for sec in tab.get("sections") or []:
      mark = norm_mark(str(sec.get("mark") or ""))
      if not mark or mark in have or not sec.get("width_in") or not sec.get("depth_in"):
        continue
      have.add(mark)
      out.append({"mark": mark, "kind": "BEAM", "width_in": float(sec["width_in"]), "depth_mm": round(float(sec["depth_in"]) * INCH_MM, 1), "steel": None, "steel_text": None,
        "pages": [sh.page_no], "disagree": bool(sec.get("conflicts")), "upstand": False, "source": SOURCE})
  return out

def sections_of(row: dict, rows: list) -> dict:
  out: dict = {}
  for r in [row] + [x for x in rows if x is not row]:
    tab = (((r.get("meta") or {}).get("structure_tables") or {}).get("beam_sections") or {}).get("sections") or []
    for sec in tab:
      mark = norm_mark(str(sec.get("mark") or ""))
      if not mark or mark in out or not sec.get("width_in") or not sec.get("depth_in") or sec.get("conflicts"):
        continue
      out[mark] = {"mark": str(sec["mark"]), "width_mm": round(float(sec["width_in"]) * INCH_MM, 1), "depth_mm": round(float(sec["depth_in"]) * INCH_MM, 1), "bars": section_bars(sec), "page_no": r.get("page_no")}
  return out

def _key(*parts) -> str:
  return hashlib.sha1("|".join(str(p) for p in ("BM", *parts)).encode()).hexdigest()[:24]

def _columns(row: dict, mm_per_pt: float) -> list:
  out = []
  for p in ((row.get("meta") or {}).get("structure_joins") or {}).get("planted") or []:
    size = p.get("size_mm")
    if p.get("at") and size and mm_per_pt:
      out.append((float(p["at"][0]), float(p["at"][1]), float(size[0]) / mm_per_pt, float(size[1]) / mm_per_pt, p.get("mark")))
  return out

def _support(end: tuple, reach: float, cols: list) -> dict | None:
  for cx, cy, w, h, mark in cols:
    if abs(end[0] - cx) <= w / 2.0 + reach and abs(end[1] - cy) <= h / 2.0 + reach:
      return {"on": "COLUMN", "at": [round(cx, 3), round(cy, 3)], "mark": mark}
  return None

def _view_facts(row: dict, view_key: str | None) -> dict:
  for c in row.get("candidates") or []:
    v = (c.facts or {}).get("view")
    if v and v.get("key") == view_key:
      return copy.deepcopy(v)
  return {}

def _member(row: dict, view: dict, band: dict, sec: dict, mark: str, seen: dict, cols: list, mm_per_pt: float):
  from app.modules.drawings_boq.takeoff.extract.pipeline import Candidate
  poly = band["polyline"]
  length = float(band["length_mm"])
  width_in = float(band["width_in"])
  sup = list(band.get("supports") or [None, None])
  reach = width_in * INCH_MM / mm_per_pt if mm_per_pt else 0.0
  for i, end in enumerate(poly):
    if sup[i] is None:
      sup[i] = _support((end[0], end[1]), reach, cols)

  closed = all(s is not None for s in sup)
  notes = [C.note("BEAM_RUN_FROM_BANDS", mark=mark)]
  if not closed:
    notes.append(C.note("BEAM_RUN_NOT_CLOSED", mark=mark, open_ends=[i for i, s in enumerate(sup) if s is None]))
  if "CONFLICT_IN_DRAWING" in (band.get("reasons") or []) or abs(width_in - sec["width_mm"] / INCH_MM) > BBD.WIDTH_CONFLICT_IN:
    notes.append(C.note("BEAM_RUN_WIDTH_CONFLICT", mark=mark, band_width_in=round(width_in, 2), section_width_in=round(sec["width_mm"] / INCH_MM, 2)))

  names = []
  for m in band.get("marks") or []:
    if m["mark"] not in names:
      names.append(m["mark"])
  if len(names) > 1:
    notes.append(C.note("BEAM_RUN_MARKS_DIFFER", mark=mark, marks=names))
  run_count = seen["runs"].get(norm_mark(mark), 0)
  labels = seen["labels"].get(norm_mark(mark))

  if labels is not None and labels != run_count:
    notes.append(C.note("BEAM_RUN_COUNT_DIFFERS", mark=mark, labels=labels, runs=run_count))
  facts = {"mark": mark, "from_runs": True, "derived_from": "BEAM_RUNS", "beam_role": "FLOOR", "level_hint": view.get("level_hint"), "view": _view_facts(row, view.get("key")),
    "run": {"axis": band["axis"], "polyline": [list(p) for p in poly], "length_mm": length, "width_in": width_in, "source": band.get("source"), "ink": band.get("ink"), "supports": sup, "closed": closed, "marks_near": names},
    "section": {"mark": sec["mark"], "page_no": sec["page_no"], "width_mm": sec["width_mm"], "depth_mm": sec["depth_mm"]}, "bars": sec["bars"], "length_m": round(length / 1000.0, 3),
    "labels_seen": labels, "runs_found": run_count}
  label = f"{mark} run · {length / 1000.0:.2f} m x {sec['width_mm'] / INCH_MM:g} x {sec['depth_mm'] / INCH_MM:g} in" + ("" if closed else " · open end")
  m = Candidate(key=_key(row["page_no"], view.get("key"), mark, poly), category="BEAM", kind="COUNT", quantity_mode="COUNT_X_VOLUME", label=label, tag=f"BEAM-{mark}", geometry={"points": [[round((poly[0][0] + poly[1][0]) / 2.0, 3), round((poly[0][1] + poly[1][1]) / 2.0, 3)]]},
    params={"length_mm": length, "width_mm": sec["width_mm"], "depth_mm": sec["depth_mm"], "dims_basis": "SPECIFIED"}, missing=[], work_item="CON-RCC", status="VALID", confidence=0.6, facts=facts, notes=notes,
    source="VECTOR_SNAP", count=1)
  m.decision = "PENDING"
  BS.basis_note(m)
  m.status = NS.status_of(m.notes)
  return m

def apply(rows: list) -> dict:
  seen = {"views": 0, "bands": 0, "members": 0, "unmarked": 0, "no_section": 0, "open": 0, "closed": 0, "marks": {}}
  for row in rows:
    bb = (row.get("stats") or {}).get("beam_bands") or {}
    mm_per_pt = float(row.get("mm_per_pt") or bb.get("mm_per_pt") or 0.0)
    if not bb.get("views") or not mm_per_pt:
      continue
    secs = sections_of(row, rows)
    cols = _columns(row, mm_per_pt)
    labels = {norm_mark(k): int(v) for k, v in (((row.get("meta") or {}).get("mark_evidence") or {}).get("seen") or {}).items()}

    for view in bb["views"]:
      seen["views"] += 1
      runs: dict = {}
      marked = []
      for b in view.get("bands") or []:
        seen["bands"] += 1
        if not b.get("marks"):
          seen["unmarked"] += 1
          continue
        sec = secs.get(norm_mark(b["marks"][0]["mark"]))
        if sec is None:
          seen["no_section"] += 1
          continue

        runs[norm_mark(sec["mark"])] = runs.get(norm_mark(sec["mark"]), 0) + 1
        marked.append((b, sec, sec["mark"]))
      made = [_member(row, view, b, sec, mark, {"runs": runs, "labels": labels}, cols, mm_per_pt) for b, sec, mark in marked]
      row["candidates"].extend(made)
      for m in made:
        seen["members"] += 1
        seen["closed" if m.facts["run"]["closed"] else "open"] += 1
        k = norm_mark(m.facts["mark"])
        seen["marks"][k] = seen["marks"].get(k, 0) + 1
      stats = row.setdefault("stats", {})
      stats["beam_members"] = {"members": len(made), "bands": len(view.get("bands") or []), "unmarked": sum(1 for b in view.get("bands") or [] if not b.get("marks"))}
  return seen
