from __future__ import annotations
import argparse
import os
import sys
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.proof.reading import sets as RS
from app.modules.drawings_boq.takeoff.ai_reader import cache as CACHE

STOP_ABOVE = 1 / 3

def accepted(e: dict) -> bool:
  return e.get("status") == "OK" and all(v.get("passed") for v in e.get("validators") or [])

def table(root: str = CIO.HERE) -> list:
  office_of = RS.offices()
  cells: dict = {}
  for name in sorted(os.listdir(root)) if os.path.isdir(root) else []:
    for e in CACHE.read_all(os.path.join(root, name)):
      slot = cells.setdefault((office_of.get(name, RS.UNKNOWN_OFFICE), str(e.get("task") or "-")), {"answers": 0, "passed": 0, "sets": set()})
      slot["answers"] += 1
      slot["passed"] += 1 if accepted(e) else 0
      slot["sets"].add(name)
      
  out = []
  for (office, task), v in sorted(cells.items()):
    failed = v["answers"] - v["passed"]
    share = failed / v["answers"]
    out.append({"office": office, "task": task, "sets": sorted(v["sets"]), "answers": v["answers"], "passed": v["passed"], "failed": failed, "failed_share": round(share, 4), "stop": share > STOP_ABOVE})
  return out

def render(rows: list) -> list:
  if not rows:
    return ["No ai_cache folder holds an answer yet."]
  out = ["| Office | Task | Sets | Answers | Passed every check | Failed | Failed share | |", "|---|---|---|---|---|---|---|---|"]
  out += [f"| {r['office']} | {r['task']} | {', '.join(r['sets'])} | {r['answers']} | {r['passed']} | {r['failed']} | {100.0 * r['failed_share']:.1f}% | {'STOP' if r['stop'] else 'ok'} |" for r in rows]
  hit = [f"{r['office']}/{r['task']}" for r in rows if r["stop"]]
  out += ["", ("STOP: more than a third of the answers fail their checks on " + ", ".join(hit) + ". The prompt or the crops are wrong; start AX-3 from the prompts, not the money.") if hit else "No office and task has more than a third of its answers failing: the run may go on."]
  return out

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="The stop rule of JX-2: for each office and task, the share of cached AI answers that fail a check; exit 1 when it is above a third anywhere. It reads files only.")
  ap.add_argument("--root", default=CIO.HERE, help="the folder of case folders")
  a = ap.parse_args(argv)
  rows = table(a.root)
  print("\n".join(render(rows)))
  return 1 if any(r["stop"] for r in rows) else 0

if __name__ == "__main__":
  sys.exit(main())
