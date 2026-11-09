from __future__ import annotations
import argparse
import os
import sys
import yaml
from app.modules.drawings_boq.takeoff.proof.bench import offices as OFF

STORE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "..", "engine", "catalogue", "track_record.yaml")
STORE = os.path.normpath(STORE)
HEAD = "# Written by `python -m app.modules.drawings_boq.takeoff.proof.bench.track_record --write` from history.csv and offices.yaml. Do not edit by hand: the precommit gate recomputes it.\n"

def first_sight_sets(sets_doc: dict, offices_doc: dict) -> list:
  out = []
  for name, row in sorted((sets_doc.get("sets") or {}).items()):
    latest: dict = {}
    for e in offices_doc.get("set_log", {}).get(name) or []:
      latest[e["group"]] = e["split"]
    if any(s == OFF.FIRST_SIGHT for s in latest.values()):
      out.append({"set": name, "office": row.get("office")})
  return out

def _int(v):
  try:
    return int(float(v))
  except (TypeError, ValueError):
    return None

def compute(history: list, sets_doc: dict, offices_doc: dict) -> dict:
  entered = first_sight_sets(sets_doc, offices_doc)
  scored = []
  for s in entered:
    got = OFF.first_score(s["set"], history)
    if got is None:
      continue
    within, compared = _int(got.get("within_10")), _int(got.get("compared"))
    if within is None or not compared:
      continue
    
    scored.append({**s, "date": str(got.get("date") or ""), "commit": str(got.get("commit") or ""), "within_10": within, "compared": compared})
  offices = sorted({s["office"] for s in scored})
  dates = sorted({s["date"] for s in scored if s["date"]})
  return {"state": "MEASURED" if scored else "NOT_MEASURED", "history_lines": len(history), "first_sight_sets": len(entered), "scored_sets": len(scored),
    "unscored_sets": sorted(s["set"] for s in entered if s["set"] not in {x["set"] for x in scored}), "registered_offices": len(offices_doc.get("offices") or {}), "offices": len(offices),
    "within_10": sum(s["within_10"] for s in scored) if scored else None, "compared": sum(s["compared"] for s in scored) if scored else None, "dates": dates, "sets": scored}

def current() -> dict:
  return compute(OFF.history_rows(), OFF.read_sets(), OFF.load())

def render(doc: dict) -> str:
  return HEAD + yaml.safe_dump(doc, sort_keys=True, default_flow_style=False, allow_unicode=True, width=200)

def stored() -> dict | None:
  if not os.path.isfile(STORE):
    return None
  with open(STORE, encoding="utf-8") as fh:
    return yaml.safe_load(fh)

def gate() -> tuple:
  want, have = current(), stored()
  if have is None:
    return False, "engine/catalogue/track_record.yaml is missing; write it with --write", []
  if have != want:
    return False, "track_record.yaml is not what history.csv and offices.yaml give; write it again with --write", [f"stored {have.get('state')} with {have.get('scored_sets')} scored set(s); the benchmark gives {want['state']} with {want['scored_sets']}"]
  return True, f"{want['state'].lower().replace('_', ' ')}: {want['first_sight_sets']} first-sight set(s), {want['scored_sets']} scored, from {want['history_lines']} history line(s)", []

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Write or check the first-sight track record the client accuracy report shows.")
  ap.add_argument("--write", action="store_true")
  a = ap.parse_args(argv)
  if a.write:
    with open(STORE, "w", encoding="utf-8", newline="\n") as fh:
      fh.write(render(current()))
    print(f"wrote {STORE}")
  ok, note, lines = gate()
  print(f"{'ok  ' if ok else 'FAIL'}  track record: {note}")
  for ln in lines:
    print(f"      {ln}")
  return 0 if ok else 1

if __name__ == "__main__":
  sys.exit(main())
