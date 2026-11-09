from __future__ import annotations
import re

NOTE_FACT, SCHEDULE_ROW, LEGEND_ENTRY = "NOTE_FACT", "SCHEDULE_ROW", "LEGEND_ENTRY"
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?(?:\s*/\s*\d+)?")

def shape(value) -> str:
  text = _NUMBER.sub("#", str(value if value is not None else "")).upper()
  return re.sub(r"\s+", " ", text).strip()[:60]

def item_of(task: str, key: str, ai_value: dict | None) -> dict | None:
  parts = str(key).split(".")
  value = ai_value or {}
  
  try:
    if task == NOTE_FACT and len(parts) == 3:
      return {"facts": [value["facts"][int(parts[2])]]}
    if task == SCHEDULE_ROW and len(parts) == 4:
      for s in value.get("schedules") or []:
        if s.get("kind") == parts[2]:
          return {"schedules": [{"kind": s["kind"], "rows": [s["rows"][int(parts[3])]]}]}
    if task == LEGEND_ENTRY and len(parts) == 4 and parts[2] == "LEGEND":
      return {"rows": [value["rows"][int(parts[3])]]}
  except (KeyError, IndexError, ValueError, TypeError):
    return None
  return None

def subject_of(task: str, item: dict | None) -> tuple:
  if not item:
    return None, None
  if task == NOTE_FACT:
    f = item["facts"][0]
    return str(f.get("key")), f"{f.get('value'):g} {f.get('unit') or ''}".strip() if isinstance(f.get("value"), (int, float)) else str(f.get("value"))
  if task == SCHEDULE_ROW:
    s = item["schedules"][0]
    r = s["rows"][0]
    return str(s["kind"]), " ".join(str(r[f]) for f in ("mark", "floor", "size", "layer", "thickness") if r.get(f))
  if task == LEGEND_ENTRY:
    r = item["rows"][0]
    return "LEGEND", str(r.get("name") or "")
  return None, None

def kind_of(task: str, item: dict | None) -> str | None:
  subject, _ = subject_of(task, item)
  return subject if task in (NOTE_FACT, SCHEDULE_ROW) else None

def quote_of(task: str, item: dict | None) -> str:
  if not item:
    return ""
  if task == NOTE_FACT:
    return str(item["facts"][0].get("quote") or "")
  if task == SCHEDULE_ROW:
    return str(item["schedules"][0]["rows"][0].get("quote") or "")
  return str(item["rows"][0].get("quote") or "")
