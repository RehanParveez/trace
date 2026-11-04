from __future__ import annotations
from app.modules.drawings_boq.rebar.member_source import FLOOR_RANK
from app.modules.drawings_boq.rebar.bbs_audited import check_steel_source
from app.modules.drawings_boq.rebar.bbs_expect_decisions import EXPECT_KEYS

MAX_GROUPS = 600
MAX_ELEMENTS = 20

def check_floor_map(value) -> dict:
  if not isinstance(value, dict) or len(value) > MAX_GROUPS:
    raise ValueError("the floor map is a table of sheet names to floors")
  out: dict = {}
  for name, floors in value.items():
    if not isinstance(name, str) or not name.strip() or len(name) > 300:
      raise ValueError("a sheet name in the floor map is empty or too long")
    items = floors if isinstance(floors, list) else [floors]
    if not items or any(f not in FLOOR_RANK for f in items):
      raise ValueError(f"the floors of {name} must be among {', '.join(FLOOR_RANK)}")
    out[name] = list(dict.fromkeys(items))
  return out

def check_member_map(value) -> dict:
  if not isinstance(value, dict) or len(value) > MAX_GROUPS:
    raise ValueError("the member map is a table of schedule members to drawing members")
  out: dict = {}
  for group, entry in value.items():
    els = (entry or {}).get("elements") if isinstance(entry, dict) else None
    if not isinstance(group, str) or not isinstance(els, list) or len(els) > MAX_ELEMENTS:
      raise ValueError("a member map entry needs a group and a list of drawing members")
  
    clean = []
    for e in els:
      if not isinstance(e, dict) or not str(e.get("class") or "").strip():
        raise ValueError("a drawing member in the member map needs a class")
      clean.append({"pdf_key": e.get("pdf_key"), "sheet": e.get("sheet"), "class": str(e["class"])[:20], "mark": (str(e["mark"])[:60] if e.get("mark") else None), "floor": e.get("floor")})
    out[group] = {"elements": clean, "note": str(entry.get("note") or "")[:500], "by": entry.get("by")}
  return out

KEYS = {"bbs_floor_map": check_floor_map, "bbs_member_map": check_member_map, "steel_source": check_steel_source, **EXPECT_KEYS}

def clean(key: str, value):
  if key not in KEYS:
    raise ValueError(f"{key} is not a decision of the bar schedule audit")
  return KEYS[key](value)
