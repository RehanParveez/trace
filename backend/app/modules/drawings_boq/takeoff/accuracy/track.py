from __future__ import annotations
import os
import yaml

STORE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "engine", "catalogue", "track_record.yaml"))

def stored() -> dict | None:
  if not os.path.isfile(STORE):
    return None
  with open(STORE, encoding="utf-8") as fh:
    return yaml.safe_load(fh)

def record(data: dict | None, text: dict) -> dict:
  if not data or data.get("state") != "MEASURED":
    base = data or {}
    
    return {"state": "NOT_MEASURED", "first_sight_sets": base.get("first_sight_sets", 0), "scored_sets": 0, "unscored_sets": list(base.get("unscored_sets") or []), "registered_offices": base.get("registered_offices", 0),
      "sets": [], "offices": 0, "within_10": None, "compared": None, "dates": [], "rule": text["track_never_dev"],
      "text": text["track_none"] + ("" if data else " The benchmark's record could not be found.")}
  dates = list(data.get("dates") or [])
  when = dates[0] if len(dates) == 1 else f"{dates[0]} to {dates[-1]}" if dates else "an unrecorded date"
  return {**{k: data[k] for k in ("state", "first_sight_sets", "scored_sets", "unscored_sets", "registered_offices", "sets", "offices", "within_10", "compared", "dates")}, "rule": text["track_never_dev"],
    "text": text["track_some"].format(sets=data["scored_sets"], offices=data["offices"], when=when, within=data["within_10"], compared=data["compared"])}

def current(text: dict) -> dict:
  try:
    return record(stored(), text)
  except (OSError, ValueError, KeyError, TypeError) as exc:
    return record(None, text) | {"text": f"{text['track_none']} The benchmark's record could not be read ({type(exc).__name__})."}
