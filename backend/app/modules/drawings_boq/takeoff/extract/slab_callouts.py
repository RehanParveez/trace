from __future__ import annotations
import re
from app.engine.measure import rule_registry as RR
from app.modules.drawings_boq.takeoff.extract import slab_panels as SP

RULE = "SLAB_CALLOUT_ITEMS"
META_KEY = "slab_callout_items"
SOURCE_KEY = "slab_callouts"
CALLOUT = re.compile(r"^#\s*(?P<bar>\d{1,2})\s*[\"”″]?\s*@\s*(?P<s>\d{1,2}(?:\.\d)?)\s*[\"”″]?\s*(?P<alt>/\s*\d{1,2}(?:\.\d)?\s*[\"”″]?)?\s*(?:C\s*/\s*C)?\s*$", re.I)
PLAN_KINDS = ("STRUCT_PLAN", "PLAN")
PLAN_WORD = "REINFORCEMENT"
NOT_SLAB = ("FOUNDATION", "FOOTING", "COLUMN", "BEAM", "LINTEL", "STAIR", "TANK", "SEPTIC")

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
    if kind in PLAN_KINDS and PLAN_WORD in title and not any(n in title for n in NOT_SLAB):
      return key
  return None

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
    key = plan_view(meta) if got else None
    if not got or key is None or not got.get("callouts"):
      continue
    meta[META_KEY] = {"view": key, "callouts": got["callouts"], "alternate": len(got.get("alternate") or [])}
    made += len(got["callouts"])
  return made
