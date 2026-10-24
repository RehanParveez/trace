from __future__ import annotations
from app.engine.measure import readings as QS

BEAM_BASES = ("ABOVE_PLINTH_BEAM", "BETWEEN_BEAMS")

HEIGHT = "wall_height_basis"
BAND = "tie_band_single_count"
NET = "brick_net_of_lintels"
OPENINGS = "opening_rules_basis"

def _opts(*rows) -> list:
  return [{"value": v, "label": label, "text": text, "param": p} for v, label, text, p in rows]

DECISIONS = [
  {"key": HEIGHT, "rule": "P43-1", "kind": "CHOICE", "title": "Height of a brick wall",
   "question": "Which height is a brick wall measured to? The sections print the floor-to-floor height and the plans do not say where the wall starts and stops.",
   "reads": "choice", "affects": "brick and plaster areas of every wall whose height comes from the sections",
   "options": _opts(
     ("FLOOR_TO_FLOOR", "Floor to floor", QS.CHOICE_OPTIONS[HEIGHT]["FLOOR_TO_FLOOR"], None),
     ("CLEAR", "Clear height", QS.CHOICE_OPTIONS[HEIGHT]["CLEAR"], None),
     ("ABOVE_PLINTH_BEAM", "Above the plinth beam", QS.CHOICE_OPTIONS[HEIGHT]["ABOVE_PLINTH_BEAM"], None),
     ("BETWEEN_BEAMS", "Between the beams", QS.CHOICE_OPTIONS[HEIGHT]["BETWEEN_BEAMS"], None))},
  {"key": BAND, "rule": "P44-1", "kind": "SWITCH", "title": "Tie band at lintel level",
   "question": "The drawing prints a tie band at lintel level and also a roof band. Is the tie band the same member as the roof band, or a second one?",
   "reads": "param", "affects": "the roof beam and band concrete listed on the floors that print a tie band",
   "options": _opts(
     ("ONE_BAND", "One band", "The tie band and the roof band over the same walls are one member, listed once (the QS's answer for the roof band).", 1.0),
     ("BAND_AND_BEAM", "Band and beam", "The tie band is listed as well as the roof beam, over the solid wall only (the lintels stand where the openings are).", 0.0))},
  {"key": NET, "rule": "P43-1", "kind": "SWITCH", "title": "Brick and the lintels over its openings",
   "question": "The lintel over a door or window is concrete cast in the wall. Is the brick measured net of it?",
   "reads": "param", "affects": "brick volume of every wall that has openings with a lintel",
   "options": _opts(
     ("NET", "Net of the lintels", "The lintels over the openings are taken off the brick, so the concrete is counted once, as lintels (IS 1200 and usual practice).", 1.0),
     ("GROSS", "Gross, lintels not taken off", "The brick is measured over the openings' lintels as if they were brick; the lintels are counted as concrete as well.", 0.0))},
  {"key": OPENINGS, "rule": "P57-1", "kind": "CHOICE", "title": "Which openings come off each work item",
   "question": "Does one rule decide which doors and windows come off, whatever the work item, or does each work item have its own (IS 1200)?",
   "reads": "choice", "affects": "brick and RCC wall volume, wall formwork, and the plaster and paint areas of every wall that has openings",
   "options": _opts(
     ("SHEET", "One rule, as the QS's sheet", QS.CHOICE_OPTIONS[OPENINGS]["SHEET"], None),
     ("IS1200", "A rule for each item (IS 1200)", QS.CHOICE_OPTIONS[OPENINGS]["IS1200"], None))},
]

def by_key(key: str) -> dict | None:
  return next((d for d in DECISIONS if d["key"] == key), None)

def default_value(d: dict) -> str:
  if d["reads"] == "choice":
    return str(QS.CHOICES[d["key"]])
  v = QS.PARAM_VALUES.get(d["key"])
  want = 1.0 if v is None else float(v)
  return next(o["value"] for o in d["options"] if float(o["param"]) == (1.0 if want >= 0.5 else 0.0))

def valid(d: dict, value: str) -> bool:
  return any(o["value"] == value for o in d["options"])

def to_override(d: dict, value: str):
  if d["reads"] == "choice":
    return value
  return next(float(o["param"]) for o in d["options"] if o["value"] == value)
