from __future__ import annotations
import re
from app.engine.measure import readings as RD
from app.engine.measure import rule_registry as RR
from app.modules.drawings_boq.takeoff.extract import slab_panels as SP

RULE = "SLAB_CALLOUT_ITEMS"
META_KEY = "slab_callout_items"
SOURCE_KEY = "slab_callouts"
INCH_MARK = r"(?:[\"”″]|'')?"
CALLOUT = re.compile(rf"^#\s*(?P<bar>\d{{1,2}})\s*{INCH_MARK}\s*@\s*(?P<s>\d{{1,2}}(?:\.\d)?)\s*{INCH_MARK}\s*(?P<alt>/\s*\d{{1,2}}(?:\.\d)?\s*{INCH_MARK})?\s*(?:C\s*/\s*C)?\s*$", re.I)
PLAN_KINDS = ("STRUCT_PLAN", "PLAN")
PLAN_WORDS = ("REINFORCEMENT", "SLAB")
NOT_SLAB = ("FOUNDATION", "FOOTING", "COLUMN", "STAIR", "TANK", "SEPTIC")
NOT_SLAB_UNLESS_SLAB = ("BEAM", "LINTEL")

def enabled() -> bool:
  return RR.on(RULE)

def strings_of(words: list) -> dict:
  one, alt = [], []
  
  for w in words:
    m = CALLOUT.match((w.text or "").strip())
    if m is None:
      continue
    
    bar, spacing = int(m.group("bar")), float(m.group("s"))
    if not (SP.BAR_NUMBERS[0] <= bar <= SP.BAR_NUMBERS[1] and SP.SPACING_IN[0] <= spacing <= SP.SPACING_IN[1]):
      continue
    rec = {"text": w.text.strip(), "bar": bar, "spacing_in": spacing, "at": [round((w.x0 + w.x1) / 2, 2), round((w.y0 + w.y1) / 2, 2)], "axis": "X" if round(float(w.angle) / 90.0) % 2 == 0 else "Y"}
    (alt if m.group("alt") else one).append(rec)
  return {"callouts": one, "alternate": alt}

def read(raw) -> dict | None:
  if not enabled() or not raw.words:
    return None
  got = strings_of(raw.words)
  return got if got["callouts"] or got["alternate"] else None

def plan_view(meta: dict) -> str | None:
  for view in meta.get("views") or []:
    key = (view.get("key") if isinstance(view, dict) else None) or ""
    kind, _, rest = key.partition(":")
    title = rest.partition(":")[2].upper()
    if kind in PLAN_KINDS and any(w in title for w in PLAN_WORDS) and not any(n in title for n in NOT_SLAB):
      if "REINFORCEMENT" in title or "SLAB" in title or not any(n in title for n in NOT_SLAB_UNLESS_SLAB):
        return key
  return None

def captionless_plan(meta: dict, got: dict) -> bool:
  if len(got.get("callouts") or []) < RD.SLAB_PLAN_MIN_CALLOUTS:
    return False
  for view in meta.get("views") or []:
    key = (view.get("key") if isinstance(view, dict) else None) or ""
    if any(n in key.upper() for n in NOT_SLAB):
      return False
  return True

def apply(rows: list) -> int:
  made = 0
  for row in rows:
    meta = row.get("meta")
    if meta is None:
      continue
    
    meta.pop(META_KEY, None)
    if not enabled():
      continue
    
    got = (meta.get("structure_tables") or {}).get(SOURCE_KEY)
    if not got or not got.get("callouts"):
      continue
    key = plan_view(meta)
    if key is None and not captionless_plan(meta, got):
      continue
    meta[META_KEY] = {"view": key, "callouts": got["callouts"], "alternate": len(got.get("alternate") or [])}
    made += len(got["callouts"])
  return made
