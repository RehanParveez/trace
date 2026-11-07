from __future__ import annotations
import json
import os
import yaml
from app.engine.catalogue import conventions as CV
from app.modules.drawings_boq.takeoff.completeness import facts as F
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.run import completeness as RC

def storeys_of(case: str, root: str = CIO.HERE) -> list:
  path = os.path.join(root, case, "storeys.yaml")
  if not os.path.isfile(path):
    return []
  with open(path, encoding="utf-8") as fh:
    raw = yaml.safe_load(fh) or []
  return [str(r["floor"]).upper() for r in raw if isinstance(r, dict) and r.get("floor")]

def lines_of(score_dir: str | None, case: str) -> list:
  if not score_dir:
    return []
  
  path = os.path.join(score_dir, case, "score.json")
  if not os.path.isfile(path):
    return []
  
  with open(path, encoding="utf-8") as fh:
    doc = json.load(fh)
    
  out = []
  for ln in doc.get("lines") or []:
    parts = str(ln.get("key") or "").split("/")
    floor = parts[1].split("@")[0].upper() if len(parts) > 1 else None
    if ln.get("trace") is not None and parts[0]:
      out.append({"family": parts[0], "floor": floor if floor in F.FLOOR_ORDER else None, "value": ln["trace"], "unit": ln.get("unit")})
  return out

def show(result: dict, name: str = "") -> str:
  v = F.values(result["facts"])
  head = f"{name}: type {v['type']}, structure {v['structure']}, floors {','.join(v['floors']) or '-'}, basement {v['basement']}, sets {','.join(v['sets_present']) or '-'}, scope {result['scope']}"
  s = result["summary"]
  return head + "\n  " + ", ".join(f"{k} {n}" for k, n in s["by_state"].items()) + "\n  reasons: " + ", ".join(f"{k} {n}" for k, n in s["by_reason"].items())

def main(argv: list | None = None) -> int:
  import argparse
  ap = argparse.ArgumentParser(description="Print the project facts and the five-state completeness ledger for one project: the reading dumps (JSON) of its PDFs.")
  ap.add_argument("dumps", nargs="+")
  ap.add_argument("--storeys", help="a case folder name whose storeys.yaml gives the floors")
  ap.add_argument("--full", action="store_true", help="print every ledger entry")
  ap.add_argument("--conventions", action="store_true", help="switch every Pakistan convention on, as a company can")
  ap.add_argument("--method", action="append", default=[], help="a decided method, name=OPTION")
  args = ap.parse_args(argv)
  
  plains = []
  for path in args.dumps:
    with open(path, encoding="utf-8") as fh:
      plains += list(json.load(fh).values())
  on = CV.ids() if args.conventions else []
  res = RC.run_set(RC.merge(plains), storeys_of(args.storeys) if args.storeys else None, conventions=on, methods=dict(m.split("=", 1) for m in args.method))
  print(show(res, ", ".join(os.path.basename(p) for p in args.dumps)))
  if args.full:
    for e in res["ledger"]:
      print(f"  {e['element']:6} {e['floor']:9} {e['state']:15} {','.join(e['reasons'])}")
  return 0

if __name__ == "__main__":
  raise SystemExit(main())
