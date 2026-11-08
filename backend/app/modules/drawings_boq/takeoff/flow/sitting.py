from __future__ import annotations
import os
import yaml
from datetime import datetime

KEY = "sitting"
UPLOAD = "upload"
EXPORT = "export"

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "flow.yaml"), encoding="utf-8") as _fh:
  DATA = yaml.safe_load(_fh)

def mark(held: dict | None, event: str, now: datetime, detail: dict | None = None) -> dict:
  out = {"events": dict((held or {}).get("events") or {}), "exports": list((held or {}).get("exports") or [])}
  stamp = now.isoformat()
  
  if event == EXPORT:
    out["exports"].append({"at": stamp, **(detail or {})})
    out["events"].setdefault("first_export", stamp)
  elif event in DATA["events"]["once"]:
    out["events"].setdefault(event, stamp)
  return out

def seconds_between(first: str | None, second: str | None) -> float | None:
  if not first or not second:
    return None
  gap = (datetime.fromisoformat(second) - datetime.fromisoformat(first)).total_seconds()
  return round(gap, 1) if gap >= 0 else None

def summary(held: dict | None, uploaded_at: datetime | None, report: dict | None) -> dict:
  events = dict((held or {}).get("events") or {})
  if uploaded_at is not None:
    events[UPLOAD] = uploaded_at.isoformat()
    
  segments = [{"name": s["name"], "start": s["from"], "end": s["to"], "seconds": seconds_between(events.get(s["from"]), events.get(s["to"]))} for s in DATA["segments"]]
  stages = [{"name": s["name"], "seconds": s["seconds"], "status": s["status"]} for s in (report or {}).get("stages") or []]
  total = next((s["seconds"] for s in segments if s["name"] == "sitting"), None)
  return {"events": events, "segments": segments, "stages": stages, "reader_seconds": (report or {}).get("seconds"), "sitting_seconds": total, "complete": total is not None,
    "exports": list((held or {}).get("exports") or [])}
