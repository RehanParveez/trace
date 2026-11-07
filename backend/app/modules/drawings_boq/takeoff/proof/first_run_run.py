from __future__ import annotations
import argparse
import json
import os
import sys
from app.engine.catalogue import conventions as CV
from app.modules.drawings_boq.takeoff.first_run import report as RP
from app.modules.drawings_boq.takeoff.proof import completeness_run as CR
from app.modules.drawings_boq.takeoff.run import first_run_bindings as RB

def corpus(cases_dir: str | None, scores: str | None, only: list | None, out_dir: str | None) -> int:
  from app.modules.drawings_boq.takeoff.proof import case_io as CIO
  total, bad = 0.0, 0
  rows = []
  for name in only or CIO.list_cases():
    case = CIO.load_case(os.path.join(CIO.HERE, name))
    if not case.get("pdfs"):
      continue
    found, problems = CIO.find_files(case, CIO.cases_dir(cases_dir))
    if problems:
      print(f"{name}: {'; '.join(problems)}")
      bad += 1
      continue
    
    state, out, rep, _b = RB.run_project(pdfs=[found[n] for n in case["pdfs"]], lines=CR.lines_of(scores, name) if scores else None, storeys=CR.storeys_of(name))
    total += out["seconds"]
    print(RP.render(rep, name))
    rows.append({"case": name, "report": rep})
    bad += bool(rep["failed"])
  if out_dir:
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "first_run.json"), "w", encoding="utf-8") as fh:
      json.dump(rows, fh, indent=1, default=str)
  print(f"{len(rows)} project(s), {total:.1f}s, {bad} with a failed stage")
  return 1 if bad else 0

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Run the first-upload job on PDFs with the offline reader and print the report. With --corpus, on every case folder's PDFs.")
  ap.add_argument("pdfs", nargs="*")
  ap.add_argument("--corpus", action="store_true")
  ap.add_argument("--cases-dir")
  ap.add_argument("--scores", help="a score output folder whose engine lines feed the quantities stage")
  ap.add_argument("--only", nargs="*")
  ap.add_argument("--out")
  ap.add_argument("--conventions", action="store_true", help="switch every Pakistan convention on")
  args = ap.parse_args(argv)
  if args.corpus:
    return corpus(args.cases_dir, args.scores, args.only, args.out)
  state, out, rep, _b = RB.run_project(pdfs=args.pdfs, conventions=CV.ids() if args.conventions else None)
  print(RP.render(rep))
  return 1 if rep["failed"] else 0

if __name__ == "__main__":
  sys.exit(main())
