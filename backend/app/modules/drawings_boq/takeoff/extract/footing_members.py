from __future__ import annotations
import copy
import hashlib
from app.modules.drawings_boq.takeoff.extract import foundation as FD
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.extract import floor_sources as FS
from app.modules.drawings_boq.takeoff.extract import note_scope as NS
from app.modules.drawings_boq.takeoff.extract import structure_joins as SJ

IN_MM = 25.4
FT_MM = 304.8
KINDS = ("STRIP", "PAD", "WALL_FOOTING", "PLINTH_BEAM")
DECIDED = "DECISION"
ITEM_TAG = {FD.PCC_PAD: "PCC-PAD", FD.PCC_STRIP: "PCC-STRIP", FD.TRENCH: "TRENCH", FD.EXCAVATION_AREA: "EXCAVATION", FD.BRICK_STEP: "BRICK-STEP"}

def _key(*parts) -> str:
  return hashlib.sha1("|".join(str(p) for p in ("FM", *parts)).encode()).hexdigest()[:24]

def _mm(inches) -> float | None:
  return None if inches in (None, "") else round(float(inches) * IN_MM, 1)

def record(e: dict) -> dict:
  size = e.get("size_in")
  out = {"mark": e["mark"], "kind": e["kind"], "source": DECIDED, "read": "DECIDED", "sheet": e.get("sheet"), "width_mm": _mm(e.get("width_in")), "depth_mm": _mm(e.get("depth_in")),
    "pcc_width_mm": _mm(e.get("pcc_width_in")), "pcc_mm": _mm(e.get("pcc_in")), "nsl_to_pcc_mm": _mm(e.get("nsl_to_pcc_in")), "wall_mm": _mm(e.get("wall_in")),
    "steps": [{"width_mm": _mm(s["width_in"]), "height_mm": _mm(s["height_in"])} for s in e.get("steps") or []], "bars": list(e.get("bars") or []),
    "plan_shape": e.get("plan_shape"), "size_mm": [_mm(size[0]), _mm(size[1])] if size else ([_mm(e["plinth_beam_in"][0]), _mm(e["plinth_beam_in"][1])] if e.get("plinth_beam_in") else None),
    "evidence": {"answered_by": e["answered_by"], "date": e["date"], "source": e["source"]}}
  if e.get("strip_length_ft") is not None:
    out["strip_length_mm"] = round(float(e["strip_length_ft"]) * FT_MM, 1)
    out["strip_length_evidence"] = {"answered_by": e["length_answered_by"], "date": e["date"], "source": e["length_source"]}
  return out

def inject(rows: list, sections: list | None) -> dict:
  seen = {"sections": 0, "pages": [], "missing": []}
  for e in sections or []:
    rec = record(e)
    target = None
    for row in rows:
      ident = (row.get("meta") or {}).get("identity") or {}
      if str((row.get("title") or {}).get("sheet_no") or ident.get("sheet_no") or "").upper() == str(e["sheet"]).upper():
        target = row
        break
      
    if target is None:
      seen["missing"].append(e["mark"])
      continue
    rec["page_no"] = target["page_no"]
    meta = target.setdefault("meta", {})
    meta["footing_sections"] = [r for r in meta.get("footing_sections") or [] if r.get("mark") != rec["mark"]] + [rec]
    seen["sections"] += 1
    if target["page_no"] not in seen["pages"]:
      seen["pages"].append(target["page_no"])
  return seen

def _live(c) -> bool:
  return c.decision != "REJECTED" and not (c.facts or {}).get("set_aside")

def _centre(points: list) -> list:
  pts = [p for p in points if isinstance(p, (list, tuple)) and len(p) >= 2]
  return [round(sum(p[0] for p in pts) / len(pts), 4), round(sum(p[1] for p in pts) / len(pts), 4)] if pts else [0.0, 0.0]

def _status(m) -> None:
  m.status = NS.status_of(m.notes)

def _member(c, *, tag: str, category: str, item: str | None, label: str, params: dict, missing: list, notes: list, facts: dict, points: list, count: int, work_item: str | None = None, mode_given: str | None = None):
  from app.modules.drawings_boq.takeoff.extract.pipeline import Candidate
  work, mode, kind = C.SUGGESTIONS.get(category, (None, "COUNT_X_VOLUME", "COUNT"))
  if item:
    work, mode, kind = FD.WORK_ITEM[item], FD.MODE[item], "COUNT"
    tag = f"{ITEM_TAG[item]}-{tag}"
  mode, kind = (mode_given, "COUNT") if mode_given else (mode, kind)
  m = Candidate(key=_key(c.key, tag, item or category, label), category=category, kind=kind, quantity_mode=mode, label=label, tag=tag, geometry={"points": points}, params={**params, "dims_basis": "SPECIFIED"},
    missing=missing, work_item=work_item or work, status="VALID", confidence=0.6, facts={**facts, **({"foundation_item": item, "derived_from": "FOOTING_SECTION"} if item else {})}, notes=notes, source="TAG_SCAN", count=count)
  m.decision = "PENDING"
  _status(m)
  return m

def _size_label(*dims_mm) -> str:
  return " x ".join(f"{d / IN_MM:g}" for d in dims_mm) + " in"

def _evidence(sec: dict, length: bool = False) -> dict:
  return {"section": {"mark": sec["mark"], "page_no": sec.get("page_no"), "source": sec["source"], "evidence": sec["evidence"]},
    **({"strip_length": {"mm": sec["strip_length_mm"], "evidence": sec["strip_length_evidence"]}} if length and sec.get("strip_length_mm") else {})}

def _pad(c, sec: dict) -> list:
  n = int(c.count or 1)
  pts = (c.geometry or {}).get("points") or []
  w, d = sec["width_mm"], sec["depth_mm"]
  facts = {"mark": c.tag, "member_of": "PAD", "size_used_mm": [w, w], **_evidence(sec)}
  notes = [C.note("FOOTING_SECTION_DECIDED", mark=c.tag)]
  base = dict(tag=c.tag, facts=facts, points=copy.deepcopy(pts), count=n)
  out = [_member(c, category="FOOTING", item=None, label=f"{c.tag} pad x{n} · {_size_label(w, w, d)}", params={"length_mm": w, "width_mm": w, "depth_mm": d}, missing=[], notes=list(notes), **base)]
  pcc, t = sec.get("pcc_width_mm"), sec.get("pcc_mm")
  if pcc and t:
    out.append(_member(c, category="WALL", item=FD.PCC_PAD, label=f"{c.tag} PCC x{n} · {_size_label(pcc, pcc, t)}", params={"length_mm": pcc, "width_mm": pcc, "depth_mm": t}, missing=[], notes=list(notes), **base))
    if sec.get("nsl_to_pcc_mm"):
      out.append(_member(c, category="WALL", item=FD.EXCAVATION_AREA, label=f"{c.tag} excavation x{n} · {_size_label(pcc, pcc, sec['nsl_to_pcc_mm'])}", params={"length_mm": pcc, "width_mm": pcc, "depth_mm": sec["nsl_to_pcc_mm"]},
        missing=[], notes=list(notes) + [C.note("EXCAVATION_TO_PCC_OUTLINE")], **base))
  return out

def _strip(c, sec: dict) -> list:
  pts = (c.geometry or {}).get("points") or []
  at = [_centre(pts)]
  length = sec.get("strip_length_mm")
  w, d = sec["width_mm"], sec["depth_mm"]
  facts = {"mark": c.tag, "member_of": "STRIP", "size_used_mm": [length or 0.0, w], "sightings": int(c.count or 1), **_evidence(sec, True)}
  notes = [C.note("FOOTING_SECTION_DECIDED", mark=c.tag), C.note("STRIP_LENGTH_DECIDED" if length else "STRIP_LENGTH_MISSING", mark=c.tag)]
  missing = [] if length else ["length"]
  base = dict(tag=c.tag, facts=facts, points=at, count=1)
  def line(category, item, name, width, depth, extra=None, **kw):
    params = {"width_mm": width, "depth_mm": depth, **({"length_mm": length} if length else {})}
    label = f"{c.tag} {name} · " + (f"{length / FT_MM:g} ft x " if length else "length not known x ") + _size_label(width, depth)
    return _member(c, category=category, item=item, label=label, params=params, missing=list(missing), notes=list(notes) + list(extra or []), **{**base, **kw})
  out = [line("FOOTING", None, "strip", w, d)]
  if sec.get("pcc_width_mm") and sec.get("pcc_mm"):
    out.append(line("WALL", FD.PCC_STRIP, "PCC", sec["pcc_width_mm"], sec["pcc_mm"]))
    if sec.get("nsl_to_pcc_mm"):
      out.append(line("WALL", FD.TRENCH, "excavation", sec["pcc_width_mm"], sec["nsl_to_pcc_mm"], [C.note("EXCAVATION_TO_PCC_OUTLINE")]))
  for i, s in enumerate(sec.get("steps") or [], 1):
    out.append(line("WALL", FD.BRICK_STEP, f"brick step {i}", s["width_mm"], s["height_mm"], points=[list(pts[(i - 1) % len(pts)])] if pts else at, tag=f"{c.tag}-{i}"))
  return out

def _plinth(c, strip: dict, beam: dict) -> list:
  length = strip.get("strip_length_mm")
  w, d = beam["size_mm"]
  facts = {"mark": "PLINTH-BEAM", "member_of": "PLINTH_BEAM", "beam_role": "PLINTH", "from_section": True, "follows": strip["mark"], **_evidence(beam), "strip_length": {"mm": length, "evidence": strip.get("strip_length_evidence")}}
  notes = [C.note("FOOTING_SECTION_DECIDED", mark="PLINTH-BEAM"), C.note("STRIP_LENGTH_DECIDED" if length else "STRIP_LENGTH_MISSING", mark=strip["mark"])]
  params = {"width_mm": w, "depth_mm": d, **({"length_mm": length} if length else {})}
  label = "Plinth beam · " + (f"{length / FT_MM:g} ft x " if length else "length not known x ") + _size_label(w, d)
  return [_member(c, tag="PLINTH-BEAM", category="BEAM", item=None, label=label, params=params, missing=[] if length else ["length"], notes=notes, facts=facts, points=[_centre(((c.geometry or {}).get("points") or []))], count=1, work_item="CON-RCC", mode_given="COUNT_X_VOLUME")]

def apply(rows: list) -> dict:
  seen = {"pads": 0, "strips": 0, "members": 0, "held": 0, "wall_footings": 0, "sightings": 0}
  index = SJ.footing_section_index(rows)
  beam = next((h["rec"] for h in index.values() if h["rec"].get("kind") == "PLINTH_BEAM" and h["rec"].get("size_mm")), None)
  for row in rows:
    made: list = []
    
    strip_of = None
    for c in list(row.get("candidates") or []):
      if c.category != "FOOTING" or not _live(c) or not c.tag:
        continue
      j = (c.facts or {}).get("footing_section_join") or {}
      held = index.get(SJ.norm(c.tag))
      if j.get("status") != SJ.JOINED or held is None or held["rec"].get("source") != DECIDED:
        continue
      sec = held["rec"]
      if sec["kind"] == "PAD":
        made += _pad(c, sec)
        seen["pads"] += int(c.count or 1)
      elif sec["kind"] == "STRIP":
        made += _strip(c, sec)
        strip_of = strip_of or (c, sec)
        seen["strips"] += 1
        seen["sightings"] += int(c.count or 1)
        
      else:
        continue
      
      c.facts = {**(c.facts or {}), "set_aside": {"by": FS.FAMILY_BY, "mark": c.tag, "kind": sec["kind"]}}
    if strip_of is not None and beam is not None:
      made += _plinth(strip_of[0], strip_of[1], beam)
    if made:
      row["candidates"] = list(row["candidates"]) + made
      seen["members"] += len(made)
      seen["held"] += sum(1 for m in made if m.missing)
      
  seen["wall_footings"] = sum(1 for h in index.values() if h["rec"].get("kind") == "WALL_FOOTING")
  return seen
