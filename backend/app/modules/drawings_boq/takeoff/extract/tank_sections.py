from __future__ import annotations
from collections import Counter
from app.modules.drawings_boq.takeoff.extract import config as C

MM_PER_IN = 25.4

def _drawings(kind: str | None, details: list) -> list:
  """The tank drawings that belong to a tank of this kind; a tank whose kind is only 'TANK' gets all of them."""
  if not kind or kind == "TANK":
    return list(details or [])
  return [d for d in details or [] if d.get("kind") == kind]

def _line(d: dict) -> str:
  sizes = ", ".join(f"{x['text']} ({'written in the PDF' if x.get('source') == 'TEXT' else 'read ' + str(x['votes']) + 'x from the picture'})" for x in sorted(d.get("lengths") or [], key=lambda x: -x["inches"]))
  bars = "; ".join(d.get("bar_notes") or [])
  return f"{d['view'].lower()}: {sizes or 'no size read'}" + (f" ({bars})" if bars else "")

def describe(kind: str | None, details: list) -> dict | None:
  """What the tank drawings of this kind print: {"drawings": [{view, page_no, sizes, bar_notes}], "message": the sentence listing them}; None when there are none."""
  mine = _drawings(kind, details)
  if not mine:
    return None
  return {"drawings": [{"view": d["view"], "page_no": d.get("page_no"), "sizes": [x["text"] for x in d.get("lengths") or []], "bar_notes": list(d.get("bar_notes") or []),
    "lengths": [{"text": x["text"], "inches": x["inches"], "votes": x.get("votes", 0)} for x in d.get("lengths") or []]} for d in mine],
    "message": " | ".join(_line(d) for d in mine)}

def _ft(inches: float) -> str:
  return f"{int(inches // 12)}'-{inches - 12 * int(inches // 12):g}\""

def derive(kind: str | None, details: list) -> dict | None:
  mine = _drawings(kind, details)
  if not mine:
    return None
  plans = [d for d in mine if d.get("view") == "PLAN"]
  sections = [d for d in mine if d.get("view") == "SECTION"]
  votes: Counter = Counter()
  for d in mine:
    for x in d.get("lengths") or []:
      votes[x["inches"]] += x.get("votes", 0)
  small = {i: v for i, v in votes.items() if 4 <= i <= 12}
  if not small:
    return None

  t = max(small, key=lambda i: (small[i], -i))
  feet = lambda ds: {x["inches"] for d in ds for x in d.get("lengths") or [] if "'" in x["text"] and x["inches"] >= 24}
  sizes, basis = {"thickness_mm": t * MM_PER_IN}, {}
  basis["thickness_mm"] = f"{t}\" is the length of 4 to 12 in read most often on the tank drawings ({small[t]} readings)"
  slabs = None
  
  if any(x["inches"] == t for d in sections for x in d.get("lengths") or []):
    slabs = {"top_mm": t * MM_PER_IN, "bottom_mm": t * MM_PER_IN}
  plan_big, section_big = feet(plans), feet(sections)
  common = plan_big & section_big
  width = None
  if len(common) == 1:
    width = next(iter(common))
    sizes["width_mm"] = (width + 2 * t) * MM_PER_IN
    basis["width_mm"] = f"{_ft(width)} is printed on both the plan and the section (the inside width); {t}\" of wall on each side is added"
  longer = [i for i in plan_big if width is not None and i > width and i <= 240]
  if len(longer) == 1:
    sizes["length_mm"] = (longer[0] + 2 * t) * MM_PER_IN
    basis["length_mm"] = f"{_ft(longer[0])} is the one longer length the plan prints (the inside length); {t}\" of wall on each side is added"
  clear = [i for i in section_big if 36 <= i <= 72 and i != width]
  whole = [i for i in section_big if 72 < i <= 120 and i != width]
  if len(clear) == 1:
    sizes["height_mm"] = (clear[0] + 2 * t) * MM_PER_IN
    basis["height_mm"] = f"{_ft(clear[0])} is the one length of 3 to 6 ft the section prints besides the width (the clear height); the two slabs of {t}\" are added"
  elif not clear and len(whole) == 1:
    sizes["height_mm"] = whole[0] * MM_PER_IN
    basis["height_mm"] = f"{_ft(whole[0])} is the one length of 6 to 10 ft the section prints (the whole height, slabs included)"
  left = [name for token, name in (("length_mm", "outside length"), ("width_mm", "outside width"), ("height_mm", "outside height")) if token not in sizes]
  return {"sizes_mm": sizes, "slabs_mm": slabs, "basis": basis, "left": left}

def apply(walls: list, details: list) -> int:
  """List the tank drawings on every tank wall. Returns the number of walls that got a list."""
  n = 0
  for c in walls:
    f = c.facts or {}
    if f.get("enclosure") != "TANK":
      continue
    listed = describe(f.get("tank_kind"), details)
    if listed is None:
      continue
    f["tank_drawings"] = listed["drawings"]
    note = C.note("TANK_SECTIONS_LISTED", kind=f.get("tank_kind"))
    note["message"] += " Printed: " + listed["message"] + "."
    c.notes.append(note)
    n += 1
  return n
