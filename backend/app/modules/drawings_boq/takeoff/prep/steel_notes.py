from __future__ import annotations
import math
import re
from app.engine.measure.steel_grammar import parse_callout, steel_text, to_steel
from app.modules.drawings_boq.takeoff.prep.details import norm_mark

MARK_IN = re.compile(r"(?<![A-Z0-9#.])(?P<mark>(?:COL|FTG|FT|BM|RB|GB|PB|LB|CB|C|F|B)\s*[-.]?\s*\d{1,2}[A-Z]?)(?![A-Z0-9\"'#])", re.I)
SLAB_WORD = re.compile(r"\b(?:R\.?C\.?C\.?\s+)?SLAB\b", re.I)
FAMILY = {"COLUMN": "COLUMN", "FOOTING": "FOOTING", "BEAM": "BEAM"}
REACH_PT = 170.0
AMBIGUOUS = 1.25
MAX_NOTES = 120

def _category(mark: str) -> str | None:
  from app.modules.drawings_boq.takeoff.extract import members as M
  return M.category_of(re.sub(r"\s", "", mark.upper()))

def _find_mark(text: str) -> tuple:
  """(normalised mark, text with the mark taken out) for the first member mark named in a line, or (None, text)."""
  for m in MARK_IN.finditer(text):
    raw = re.sub(r"\s+", "", m.group("mark")).upper()
    if _category(raw) in FAMILY:
      return norm_mark(raw), (text[:m.start()] + " " + text[m.end():]).strip(" :-")
  return None, text

def census(lines: list) -> list:
  """Every line of the sheet that reads as reinforcement, with where it is, the mark it names (if any) and what was read from it."""
  rows = []
  for i, ln in enumerate(lines):
    mark, rest = _find_mark(ln.text)
    call = parse_callout(rest)
    if call["grade"] != "PRINTED":
      continue
    x, y = ln.locate(0, len(ln.text))
    rows.append({"index": i, "text": ln.text.strip(), "x": round(x, 2), "y": round(y, 2), "angle": ln.angle, "mark": mark, "how": "SAME_LINE" if mark else None,
      "call": call, "slab": bool(SLAB_WORD.search(ln.text))})
  return rows

def _captions(lines: list, noted: set) -> list:
  out = []
  for i, ln in enumerate(lines):
    if i in noted:
      continue
    mark, _ = _find_mark(ln.text)
    if mark:
      x, y = ln.locate(0, len(ln.text))
      out.append({"index": i, "mark": mark, "x": x, "y": y, "angle": ln.angle})
  return out

def _tie(rows: list, lines: list) -> None:
  caps = _captions(lines, {r["index"] for r in rows if r["mark"]})
  caps += [{"index": r["index"], "mark": r["mark"], "x": r["x"], "y": r["y"], "angle": r["angle"]} for r in rows if r["mark"]]
  for r in rows:
    if r["mark"] or r["slab"]:
      r["group"] = r["index"] if r["mark"] else None
      continue
    near = sorted(((math.hypot(c["x"] - r["x"], c["y"] - r["y"]), c) for c in caps if c["angle"] == r["angle"]), key=lambda t: t[0])
    near = [t for t in near if t[0] <= REACH_PT]
    if not near:
      r["group"] = None
      continue
    if len(near) > 1 and near[1][1]["mark"] != near[0][1]["mark"] and near[1][0] < AMBIGUOUS * near[0][0]:
      r["how"] = "AMBIGUOUS"
      r["group"] = None
      continue
    r["mark"], r["how"], r["group"] = near[0][1]["mark"], "NEAR_CAPTION", near[0][1]["index"]

def read(lines: list) -> dict:
  """The census of a sheet's steel notes and what is tied to each mark: {"notes": [...], "marks": {mark: {"steel", "text", "problems", "details"}}, "slab": {...}}."""
  rows = census(lines)
  _tie(rows, lines)
  by_mark: dict = {}
  
  for r in rows:
    if r["mark"] and r.get("group") is not None:
      by_mark.setdefault(r["mark"], {}).setdefault(r["group"], []).append(r)
  marks: dict = {}
  for mark, groups in sorted(by_mark.items()):
    fam = FAMILY.get(_category(mark) or "")
    results = []
    problems: set = set()
    for _, notes in sorted(groups.items()):
      steel, probs = to_steel([n["call"] for n in notes], fam or "BEAM")
      problems.update(probs)
      if steel:
        results.append({"steel": steel, "text": "; ".join(n["text"] for n in notes), "positions": [[n["x"], n["y"]] for n in notes]})
    distinct = []
    
    for res in results:
      if all(res["steel"] != d["steel"] for d in distinct):
        distinct.append(res)
    entry = {"category": fam, "details": len(results), "problems": sorted(problems)}
    if len(distinct) == 1 and not problems:
      entry.update({"steel": distinct[0]["steel"], "text": distinct[0]["text"], "steel_text": steel_text(distinct[0]["steel"])})
    elif len(distinct) > 1:
      entry["problems"] = sorted({*problems, "DETAILS_DISAGREE"})
      entry["alternatives"] = [{"steel_text": steel_text(d["steel"]), "text": d["text"]} for d in distinct]
    marks[mark] = entry
  slab_rows = [r for r in rows if r["slab"] and not r["mark"]]
  slab: dict = {}
  
  if slab_rows:
    sets = []
    for r in slab_rows:
      steel, probs = to_steel([r["call"]], "SLAB")
      if steel:
        sets.append({"steel": steel, "text": r["text"]})
    distinct = []
    for s in sets:
      if all(s["steel"] != d["steel"] for d in distinct):
        distinct.append(s)
    if len(distinct) == 1:
      slab = {"steel": distinct[0]["steel"], "text": distinct[0]["text"], "steel_text": steel_text(distinct[0]["steel"])}
    elif len(distinct) > 1:
      slab = {"problems": ["DETAILS_DISAGREE"], "alternatives": [{"steel_text": steel_text(d["steel"]), "text": d["text"]} for d in distinct]}
  notes = [{"text": r["text"], "x": r["x"], "y": r["y"], "mark": r["mark"], "how": r["how"], "slab": r["slab"], "grade": r["call"]["grade"],
    "unread": r["call"]["unread"]} for r in rows][:MAX_NOTES]
  return {"notes": notes, "marks": marks, "slab": slab}

def attach(candidates: list, found: dict, note, imperial: bool = True) -> dict:
  """Put the steel read for a mark on the candidates that carry that mark, and say what could not be settled. note(code, **extra) builds a candidate note."""
  stats = {"read": 0, "attached": 0, "disagree": [], "not_read": 0}
  stats["read"] = len(found.get("notes") or [])
  marks = found.get("marks") or {}
  for c in candidates:
    if c.category not in ("COLUMN", "BEAM", "FOOTING", "SLAB"):
      continue
    entry = None
    
    if c.category == "SLAB":
      entry = found.get("slab") or None
    elif c.tag:
      entry = marks.get(norm_mark(c.tag))
    if entry is None:
      if c.category != "BEAM" or (c.facts or {}).get("derived_from") != "WALLS":
        c.notes.append(note("STEEL_NOT_PRINTED"))
      stats["not_read"] += 1
      continue
    if "DETAILS_DISAGREE" in (entry.get("problems") or []):
      c.notes.append(note("STEEL_DETAILS_DISAGREE", alternatives=entry.get("alternatives") or []))
      stats["disagree"].append(c.tag or c.category)
      continue
    if entry.get("problems") or not entry.get("steel"):
      c.notes.append(note("STEEL_NOT_PRINTED"))
      stats["not_read"] += 1
      continue
    c.params["steel"] = dict(entry["steel"])
    c.facts["steel_text"] = entry["steel_text"]
    c.facts["steel_source"] = {"grade": "PRINTED", "text": entry["text"]}
    c.notes.append(note("STEEL_FROM_DETAIL", text=entry["steel_text"]))
    stats["attached"] += 1
  return stats
