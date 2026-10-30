from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.prep.details import norm_mark
from app.engine.measure import readings as QSR
from app.modules.drawings_boq.takeoff.model import rules as MR
from app.modules.drawings_boq.takeoff.extract import note_scope as NS
from app.modules.drawings_boq.takeoff.extract import slab_label as SL
from app.modules.drawings_boq.takeoff.extract import safe as SF

KIND_OF_ROLE = {"PLINTH": "PLINTH", "ROOF": "ROOF", "BAND": "TIE"}
ALSO_OFFERED = {"ROOF": ("BEAM",), "PLINTH": ("GRADE",)}

WEB_BELOW_SLAB, FULL_DEPTH = "WEB_BELOW_SLAB", "FULL_DEPTH"
FULL_DEPTH_ROLES = ("PLINTH", "BAND")
FULL_DEPTH_MARKS = ("GB", "PB", "TB")
BASIS_NOTES = {WEB_BELOW_SLAB: "BEAM_DEPTH_WEB_BELOW_SLAB", FULL_DEPTH: "BEAM_DEPTH_FULL"}

def depth_basis(c) -> str | None:
  """How the depth of this beam is counted (Pack 135): the overall depth under the QS convention beam_depth_includes_slab (the engine then gives the slab the part of the beam inside it and the
  beam keeps its web), or in full for a plinth, grade, tie or band beam, which has no slab over it. None for an upstand beam, which carries its own note (BEAM_UPSTAND)."""
  f = c.facts or {}
  return MR.depth_basis(f.get("beam_role"), norm_mark(str(c.tag or "")), bool(QSR.param("beam_depth_includes_slab")), bool(f.get("upstand")))

def basis_note(c) -> None:
  """Puts the note and the fact that say which basis the depth of the beam is counted on. Does nothing while the depth is not known."""
  if not (c.params or {}).get("depth_mm"):
    return
  basis = depth_basis(c)
  if basis is None:
    return
  note = C.note(BASIS_NOTES[basis])
  note["origin"] = QSR.CO.origin_of("beam_depth_includes_slab")
  c.notes = [n for n in c.notes or [] if n.get("code") not in BASIS_NOTES.values()] + [note]
  if c.facts is None:
    c.facts = {}
  c.facts["depth_basis"] = basis

def _text(s: dict) -> str:
  size = f"{s['depth_mm'] / 25.4:g} in deep" if s.get("depth_mm") else "depth not read"
  return f"{s['mark']}: {size}" + (f", {s['steel_text']}" if s.get("steel_text") else "")

def options_for(role: str, sections: list) -> list:
  kind = KIND_OF_ROLE.get(role)
  kinds = (kind, *ALSO_OFFERED.get(role, ()))
  return [s for s in sections or [] if s.get("kind") in kinds and not s.get("disagree") and not s.get("upstand") and (s.get("depth_mm") or s.get("steel"))]

KINDS_OF_MARK = {"GB": ("GRADE",), "PB": ("PLINTH",), "RB": ("ROOF", "BEAM"), "B": ("BEAM", "ROOF"), "TB": ("TIE",)}

def options_for_mark(mark, sections: list) -> list:
  kinds = KINDS_OF_MARK.get(re.sub(r"[^A-Z]", "", norm_mark(str(mark or ""))))
  return [s for s in sections or [] if kinds and s.get("kind") in kinds and not s.get("disagree") and not s.get("upstand") and (s.get("depth_mm") or s.get("steel"))]

def _number(mark) -> int:
  digits = re.sub(r"\D", "", str(mark or ""))
  return int(digits) if digits else 10 ** 6

def principal(role: str | None, opts: list) -> tuple:
  with_depth = [s for s in opts if s.get("depth_mm")]
  if role == "ROOF":
    general = sorted((s for s in with_depth if s.get("kind") == "BEAM"), key=lambda s: _number(s.get("mark")))
    if len(general) == 1:
      return general[0], "GENERAL"
    if general:
      return general[0], "FIRST_GENERAL"
  own = sorted((s for s in with_depth if s.get("kind") == KIND_OF_ROLE.get(role or "")), key=lambda s: _number(s.get("mark")))
  return (own[0], "FIRST") if own else (None, None)

def option(s: dict) -> dict:
  return {"mark": s["mark"], "depth_mm": s.get("depth_mm"), "steel_text": s.get("steel_text"), "steel": s.get("steel")}

def list_for_strips(c, sections: list) -> bool:
  """A beam drawn as strips and marked GB-1 where no section is captioned GB-1: the sections printed for beams of that kind are listed to choose from, none is applied."""
  f = c.facts if c.facts is not None else {}
  opts = options_for_mark(c.tag, sections)
  if f.get("section_mark") or not opts:
    return False
  c.facts = f
  if len(opts) == 1 and opts[0].get("depth_mm"):
    s = opts[0]
    c.params["depth_mm"] = s["depth_mm"]
    c.missing = [m for m in (c.missing or []) if m != "depth_mm"]
    f["section_mark"], f["section_pages"], f["section_assumed"] = s["mark"], list(s.get("pages") or []), True
    f["section_options"] = [option(s)]
    basis_note(c)
    c.notes.append(C.note("BEAM_SECTION_FROM_DETAIL", mark=s["mark"], depth_mm=s["depth_mm"]))
    if s.get("steel"):
      c.params["steel"] = dict(s["steel"])
      f["steel_text"] = s.get("steel_text")
      f["steel_source"] = {"grade": "ASSUMED", "text": f"beam section {s['mark']}"}
      c.notes.append(C.note("STEEL_FROM_DETAIL", text=s.get("steel_text")))
    return True

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
  if s.get("upstand"):
    f["upstand"] = True
    c.notes.append(C.note("BEAM_UPSTAND", mark=s["mark"]))
  if s.get("steel"):
    c.params["steel"] = dict(s["steel"])
    f["steel_text"] = s.get("steel_text")
    f["steel_source"] = {"grade": "PRINTED", "text": f"beam section {s['mark']}"}
    c.notes.append(C.note("STEEL_FROM_DETAIL", text=s.get("steel_text")))
  basis_note(c)
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
    how = None
    if chosen_one is None and not f.get("beam_mark") and len(opts) > 1 and f.get("level_hint"):      
      chosen_one, how = principal(f.get("beam_role"), opts)
    if chosen_one is not None:
      s = chosen_one
      
      c.params["depth_mm"] = s["depth_mm"]
      c.missing = [m for m in c.missing if m != "depth_mm"]
      f["section_mark"] = s["mark"]
      f["section_pages"] = list(s.get("pages") or [])
      if how:
        f["section_assumed"] = True
        f["section_options"] = [option(o) for o in opts]
        note = C.note("BEAM_SECTION_PRINCIPAL", mark=s["mark"], depth_mm=s["depth_mm"])
        note["message"] += " Printed: " + "; ".join(_text(o) for o in opts) + "."
        c.notes.append(note)
        stats["assumed"] = stats.get("assumed", 0) + 1
      else:
        c.notes.append(C.note("BEAM_SECTION_FROM_MARK" if marked is not None and marked is s else "BEAM_SECTION_FROM_DETAIL", mark=s["mark"], depth_mm=s["depth_mm"]))
      if s.get("steel"):
        c.params["steel"] = dict(s["steel"])
        f["steel_text"] = s.get("steel_text")
        f["steel_source"] = {"grade": "ASSUMED" if how else "PRINTED", "text": f"beam section {s['mark']}"}
        c.notes.append(C.note("STEEL_FROM_DETAIL", text=s.get("steel_text")))
      basis_note(c)
      stats["applied"] += 1
    else:
      f["section_options"] = [option(s) for s in opts]
      note = C.note("BEAM_SECTIONS_LISTED", options=f["section_options"])
      note["message"] += " Sections printed: " + "; ".join(_text(s) for s in opts) + "."
      c.notes.append(note)
      stats["listed"] += 1
  return stats
