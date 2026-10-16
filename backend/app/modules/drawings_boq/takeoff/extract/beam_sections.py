from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import config as C

KIND_OF_ROLE = {"PLINTH": "PLINTH", "ROOF": "ROOF"}

def _text(s: dict) -> str:
  size = f"{s['depth_mm'] / 25.4:g} in deep" if s.get("depth_mm") else "depth not read"
  return f"{s['mark']}: {size}" + (f", {s['steel_text']}" if s.get("steel_text") else "")

def options_for(role: str, sections: list) -> list:
  kind = KIND_OF_ROLE.get(role)
  return [s for s in sections or [] if s.get("kind") == kind and not s.get("disagree") and (s.get("depth_mm") or s.get("steel"))]

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
    if len(opts) == 1 and opts[0].get("depth_mm"):
      s = opts[0]
      c.params["depth_mm"] = s["depth_mm"]
      c.missing = [m for m in c.missing if m != "depth_mm"]
      f["section_mark"] = s["mark"]
      f["section_pages"] = list(s.get("pages") or [])
      c.notes.append(C.note("BEAM_SECTION_FROM_DETAIL", mark=s["mark"], depth_mm=s["depth_mm"]))
      
      if s.get("steel"):
        c.params["steel"] = dict(s["steel"])
        f["steel_text"] = s.get("steel_text")
        f["steel_source"] = {"grade": "PRINTED", "text": f"beam section {s['mark']}"}
        c.notes.append(C.note("STEEL_FROM_DETAIL", text=s.get("steel_text")))
      stats["applied"] += 1
    else:
      f["section_options"] = [{"mark": s["mark"], "depth_mm": s.get("depth_mm"), "steel_text": s.get("steel_text")} for s in opts]
      note = C.note("BEAM_SECTIONS_LISTED", options=f["section_options"])
      note["message"] += " Sections printed: " + "; ".join(_text(s) for s in opts) + "."
      c.notes.append(note)
      stats["listed"] += 1
  return stats
