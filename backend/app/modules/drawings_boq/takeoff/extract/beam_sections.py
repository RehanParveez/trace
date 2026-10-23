from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.prep.details import norm_mark

KIND_OF_ROLE = {"PLINTH": "PLINTH", "ROOF": "ROOF", "BAND": "TIE"}
ALSO_OFFERED = {"ROOF": ("BEAM",), "PLINTH": ("GRADE",)}

def _text(s: dict) -> str:
  size = f"{s['depth_mm'] / 25.4:g} in deep" if s.get("depth_mm") else "depth not read"
  return f"{s['mark']}: {size}" + (f", {s['steel_text']}" if s.get("steel_text") else "")

def options_for(role: str, sections: list) -> list:
  kind = KIND_OF_ROLE.get(role)
  kinds = (kind, *ALSO_OFFERED.get(role, ()))
  return [s for s in sections or [] if s.get("kind") in kinds and not s.get("disagree") and (s.get("depth_mm") or s.get("steel"))]

KINDS_OF_MARK = {"GB": ("GRADE",), "PB": ("PLINTH",), "RB": ("ROOF", "BEAM"), "B": ("BEAM", "ROOF"), "TB": ("TIE",)}

def options_for_mark(mark, sections: list) -> list:
  kinds = KINDS_OF_MARK.get(re.sub(r"[^A-Z]", "", norm_mark(str(mark or ""))))
  return [s for s in sections or [] if kinds and s.get("kind") in kinds and not s.get("disagree") and (s.get("depth_mm") or s.get("steel"))]

def option(s: dict) -> dict:
  return {"mark": s["mark"], "depth_mm": s.get("depth_mm"), "steel_text": s.get("steel_text"), "steel": s.get("steel")}

def list_for_strips(c, sections: list) -> bool:
  """A beam drawn as strips and marked GB-1 where no section is captioned GB-1: the sections printed for beams of that kind are listed to choose from, none is applied."""
  f = c.facts if c.facts is not None else {}
  opts = options_for_mark(c.tag, sections)
  if f.get("section_mark") or not opts:
    return False
  c.facts = f
  f["section_options"] = [option(s) for s in opts]
  note = C.note("BEAM_MARK_NO_SECTION")
  note["message"] += " Sections printed: " + "; ".join(_text(s) for s in opts) + "."
  c.notes.append(note)
  return True

def chosen(facts: dict | None, pick: str) -> tuple:
  """(section, None) for the section the user picked among the options listed on the beam, else (None, (code, message))."""
  s = next((o for o in (facts or {}).get("section_options") or [] if o.get("mark") == pick), None)
  if s is None:
    return None, ("BEAM_SECTION_NOT_LISTED", "The section chosen is not one of those listed for this beam. Choose again.")
  return s, None

def with_section(params: dict, section: dict) -> dict:
  """The beam's values with the chosen section's depth and bars; a section whose depth was not read leaves the depth to be typed."""
  out = dict(params or {})
  if section.get("depth_mm"):
    out["depth_mm"] = section["depth_mm"]
  if section.get("steel"):
    out["steel"] = dict(section["steel"])
  return out

def apply_marked(c, sections: list) -> bool:
  """A beam the plan marks (B2, GB4) takes the depth and bars of the section printed for that mark. A section that two details print differently (disagree), or that
  prints neither a depth nor bars, is not used. Returns whether a section was found."""
  mark = norm_mark(str(c.tag)) if c.tag else None
  
  if not mark:
    return False
  s = next((s for s in sections or [] if s.get("mark") and norm_mark(str(s["mark"])) == mark and not s.get("disagree") and (s.get("depth_mm") or s.get("steel"))), None)
  if s is None:
    return False
  if c.facts is None:
    c.facts = {}
  f = c.facts
  
  if s.get("depth_mm"):
    c.params["depth_mm"] = s["depth_mm"]
    c.missing = [m for m in (c.missing or []) if m != "depth_mm"]
    c.notes.append(C.note("BEAM_SECTION_FROM_MARK", mark=s["mark"], depth_mm=s["depth_mm"]))
  f["section_mark"] = s["mark"]
  f["section_pages"] = list(s.get("pages") or [])
  if s.get("steel"):
    c.params["steel"] = dict(s["steel"])
    f["steel_text"] = s.get("steel_text")
    f["steel_source"] = {"grade": "PRINTED", "text": f"beam section {s['mark']}"}
    c.notes.append(C.note("STEEL_FROM_DETAIL", text=s.get("steel_text")))
  return True

def apply(beams: list, sections: list) -> dict:
  """Put the depth and bars of the beam section on each wall-derived beam, or list the sections to pick from. Returns {"applied": n, "listed": n}."""
  stats = {"applied": 0, "listed": 0}
  for c in beams:
    f = c.facts or {}
    if f.get("derived_from") != "WALLS":
      continue
  
    opts = options_for(f.get("beam_role"), sections)
    if not opts:
      continue
    marked = next((o for o in opts if o.get("mark") == f.get("beam_mark")), None) if f.get("beam_mark") else None
    if f.get("beam_mark") and marked is None:
      c.notes.append(C.note("BEAM_MARK_SECTION_UNUSABLE", mark=f["beam_mark"]))
    chosen_one = marked if marked is not None and marked.get("depth_mm") else opts[0] if len(opts) == 1 and opts[0].get("depth_mm") else None
    if chosen_one is not None:
      s = chosen_one
      
      c.params["depth_mm"] = s["depth_mm"]
      c.missing = [m for m in c.missing if m != "depth_mm"]
      f["section_mark"] = s["mark"]
      f["section_pages"] = list(s.get("pages") or [])
      c.notes.append(C.note("BEAM_SECTION_FROM_MARK" if marked is not None and marked is s else "BEAM_SECTION_FROM_DETAIL", mark=s["mark"], depth_mm=s["depth_mm"]))
      if s.get("steel"):
        c.params["steel"] = dict(s["steel"])
        f["steel_text"] = s.get("steel_text")
        f["steel_source"] = {"grade": "PRINTED", "text": f"beam section {s['mark']}"}
        c.notes.append(C.note("STEEL_FROM_DETAIL", text=s.get("steel_text")))
      stats["applied"] += 1
    else:
      f["section_options"] = [option(s) for s in opts]
      note = C.note("BEAM_SECTIONS_LISTED", options=f["section_options"])
      note["message"] += " Sections printed: " + "; ".join(_text(s) for s in opts) + "."
      c.notes.append(note)
      stats["listed"] += 1
  return stats
