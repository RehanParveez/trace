from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import config as C

def _drawings(kind: str | None, details: list) -> list:
  """The tank drawings that belong to a tank of this kind; a tank whose kind is only 'TANK' gets all of them."""
  if not kind or kind == "TANK":
    return list(details or [])
  return [d for d in details or [] if d.get("kind") == kind]

def _line(d: dict) -> str:
  sizes = ", ".join(f"{x['text']} ({'written in the PDF' if x.get('source') == 'TEXT' else 'read ' + str(x['votes']) + 'x from the picture'})" for x in sorted(d.get("lengths") or [], key=lambda x: -x["inches"]))
  bars = "; ".join(d.get("bar_notes") or [])
  return f"{d['view'].lower()}: {sizes or 'no size read'}" + (f" ({bars})" if bars else "")

def apply(walls: list, details: list) -> int:
  """List the tank drawings on every tank wall. Returns the number of walls that got a list."""
  n = 0
  for c in walls:
    f = c.facts or {}
    if f.get("enclosure") != "TANK":
      continue
  
    mine = _drawings(f.get("tank_kind"), details)
    if not mine:
      continue
    f["tank_drawings"] = [{"view": d["view"], "page_no": d.get("page_no"), "sizes": [x["text"] for x in d.get("lengths") or []], "bar_notes": list(d.get("bar_notes") or [])} for d in mine]
    note = C.note("TANK_SECTIONS_LISTED", kind=f.get("tank_kind"))
    note["message"] += " Printed: " + " | ".join(_line(d) for d in mine) + "."
    c.notes.append(note)
    n += 1
  return n
