from __future__ import annotations
from app.engine.measure import rule_registry as RR

RULE = "SLAB_THICKNESS_ITEMS"
META_KEY = "slab_thickness_items"
MM_INCH = 25.4
KEY_NOTE = "SLAB_THICKNESS_STRUCTURAL"
KEY_LABEL = "SLAB_THICKNESS_SECTIONS"
LABEL_TIMES = 2
GENERAL_SCOPES = ("all slabs",)

def enabled() -> bool:
  return RR.on(RULE)

def facts_of(items: list) -> list:
  note: dict = {}
  label: dict = {}
  scoped = []
  
  for it in items:
    if it.get("kind") != "SLAB_THICKNESS" or not it.get("value_mm"):
      continue
    inches = round(float(it["value_mm"]) / MM_INCH, 2)
    scope = (it.get("scope") or "").lower()
    if scope in GENERAL_SCOPES:
      note[inches] = note.get(inches, 0) + int(it.get("count", 1))
    elif scope == "slab":
      label[inches] = label.get(inches, 0) + int(it.get("count", 1))
    else:
      scoped.append({"scope": scope, "inches": inches})
  out = [{"key": KEY_NOTE, "value": v, "unit": "in", "times": n, "source": "PLAN_NOTE"} for v, n in sorted(note.items())]
  out += [{"key": KEY_LABEL, "value": v, "unit": "in", "times": n, "source": "SECTION_LABEL"} for v, n in sorted(label.items()) if n >= LABEL_TIMES]
  return out + [{"key": None, "value": s["inches"], "unit": "in", "scope": s["scope"], "source": "SCOPED"} for s in scoped]

def apply(rows: list) -> int:
  made = 0
  for row in rows:
    meta = row.get("meta")
    if meta is None:
      continue
    
    meta.pop(META_KEY, None)
    if not enabled():
      continue
    facts = facts_of(((row.get("facts") or {}).get("items")) or [])
    if facts:
      meta[META_KEY] = {"facts": facts}
      made += sum(1 for f in facts if f["key"])
  return made
