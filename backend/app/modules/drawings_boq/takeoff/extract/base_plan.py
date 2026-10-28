from __future__ import annotations

NOT_IN_CHOICE = ("OVERLAY", "FRAMING", "FOUNDATION")

def tier(plan_kind, dims: int) -> int | None:
  if plan_kind in NOT_IN_CHOICE:
    return None
  if plan_kind == "WORKING":
    return 0 if dims > 0 else 1
  if plan_kind == "FURNITURE":
    return 2
  return 3

def eligible(src: dict) -> bool:
  return src.get("read_as") in (None, "PLAN_ITEMS") and tier(src.get("plan_kind"), int(src.get("dims") or 0)) is not None

def key(src: dict) -> tuple:
  return (bool(src.get("from_plans")), tier(src.get("plan_kind"), int(src.get("dims") or 0)), src.get("advice") not in (None, "READ"), -int(src.get("dims") or 0),
    int(src.get("drawing_order") or 0), int(src.get("page_no") or 0))

def best(sources: list) -> dict | None:
  pool = [s for s in sources if eligible(s)]
  return min(pool, key=key) if pool else None

def across_drawings(sources: list) -> bool:
  return len({s.get("drawing_id") for s in sources if eligible(s)} - {None}) > 1

def reason(src: dict, base: dict) -> str:
  t = tier(base.get("plan_kind"), int(base.get("dims") or 0))
  words = {0: "a working drawing with dimension strings", 1: "a working drawing", 2: "the furniture plan, and no working drawing was found", 3: "a plan whose kind is not known, and no working drawing was found"}
  return f"Page {base.get('page_no')}" + (f" of {base.get('drawing_name')}" if base.get("drawing_name") else "") + f" is {words.get(t, 'a plan')}" + (f" ({base.get('dims')} dimension strings)" if t == 0 else "") + "."

SERVICES = ("SITE",)            

def is_services(c) -> bool:
  f = c.facts or {}
  return c.category in SERVICES or bool(f.get("electrical")) or bool(f.get("drainage"))

def is_electrical(c) -> bool:
  return bool((c.facts or {}).get("electrical"))

def drawing_of(src: dict) -> tuple:
  return (src.get("drawing_id"), int(src.get("drawing_order") or 0))

def keeps_services(src: dict, keep: dict, pool: list) -> bool:
  if drawing_of(src) == drawing_of(keep):
    return False
  mine = [s for s in pool if drawing_of(s) == drawing_of(src) and eligible(s)]
  return bool(mine) and best(mine) is src
