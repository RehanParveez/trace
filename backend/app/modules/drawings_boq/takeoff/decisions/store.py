from __future__ import annotations
from app.modules.drawings_boq.takeoff.decisions import catalog
from datetime import datetime, timezone

def made(meta: dict | None) -> dict:
  raw = (meta or {}).get("takeoff_decisions") or {}
  out = {}
  for d in catalog.DECISIONS:
    row = raw.get(d["key"])
    if isinstance(row, dict) and catalog.valid(d, str(row.get("value"))):
      out[d["key"]] = row
  return out

def effective(meta: dict | None) -> dict:
  m = made(meta)
  return {d["key"]: (m[d["key"]]["value"] if d["key"] in m else catalog.default_value(d)) for d in catalog.DECISIONS}

def overrides(meta: dict | None) -> dict:
  eff = effective(meta)
  return {d["key"]: catalog.to_override(d, eff[d["key"]]) for d in catalog.DECISIONS if eff[d["key"]] != catalog.default_value(d)}

def stamp_of(stats: dict | None) -> dict:
  return dict((stats or {}).get("decisions") or {})

def stale(stats: dict | None, eff: dict) -> list:
  was = stamp_of(stats)
  return [k for k, v in eff.items() if was.get(k, catalog.default_value(catalog.by_key(k))) != v]

def put(meta: dict | None, key: str, value: str | None, user_id) -> dict:
  m = dict((meta or {}).get("takeoff_decisions") or {})
  if value is None:
    m.pop(key, None)
  else:
    m[key] = {"value": value, "by": str(user_id), "at": datetime.now(timezone.utc).isoformat()}
  return {**(meta or {}), "takeoff_decisions": m}

META_REVIEW = "takeoff_review"
REVIEW_ACTIONS = ("accept", "correct", "reject")

def review_held(meta: dict | None) -> dict:
  raw = (meta or {}).get(META_REVIEW) or {}
  return {k: dict(v) for k, v in raw.items() if isinstance(v, dict) and v.get("action") in REVIEW_ACTIONS}

def review_merge(metas: list) -> dict:
  out: dict = {}
  for meta in metas:
    for k, v in review_held(meta).items():
      if k not in out or str(v.get("at") or "") >= str(out[k].get("at") or ""):
        out[k] = v
  return out

def review_put(meta: dict | None, key: str, action: str | None, value: str | None, user_id) -> dict:
  held = dict((meta or {}).get(META_REVIEW) or {})
  if action is None:
    held.pop(key, None)
  else:
    held[key] = {"action": action, "value": value, "by": str(user_id), "at": datetime.now(timezone.utc).isoformat()}
  return {**(meta or {}), META_REVIEW: held}

