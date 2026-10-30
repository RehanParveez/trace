from __future__ import annotations
import argparse
import collections
import os
import sys

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="List the measurements the duplicate guard refuses.")
  ap.add_argument("cases", nargs="*")
  ap.add_argument("--cases-dir")
  args = ap.parse_args(argv)
  from app.modules.drawings_boq.takeoff.proof import offline_run as OR
  from app.modules.drawings_boq.takeoff.proof import case_io as CIO
  from app.engine.measure import rulebook as RB
  from app.modules.drawings_boq.takeoff.proof import offline_accept as OA
  from app.modules.drawings_boq.takeoff.proof import benchmark as BM
  
  profile, _rule_set = OR.seed_profile()
  bad = 0
  for name in args.cases or CIO.list_cases():
    case = CIO.load_case(os.path.join(CIO.HERE, name))
    files, problems = CIO.find_files(case, CIO.cases_dir(args.cases_dir))
    if problems:
      print(f"{name}: {' '.join(problems)}")
      continue
  
    rows, _p, _f = CIO.load_company_rules(case)
    whole = {n: (r, p) for n, r, p in BM.read_set([(n, open(files[n], "rb").read()) for n in case["pdfs"]])}
    with RB.using_case(rows):
      acc = OA.accept_case(name, [(n, whole[n][0]) for n in case["pdfs"]], profile, ready_only=False)
      
    groups = collections.Counter()
    for r in acc.refusals:
      a, b = r["refused"], r["held"]
      if r.get("role") != r.get("held_role"):
        bad += 1
      groups[(r["page"], r["work_item"], a.get("category"), a.get("tag"), a.get("foundation_item"), r.get("role"), b.get("category"), b.get("tag"), b.get("foundation_item"), r.get("held_role"))] += 1
    print(f"{name}: {len(acc.refusals)} refusal(s)")
    for k, n in sorted(groups.items(), key=str):
      print(f"  {n:>3} x page {k[0]} {k[1]}: {k[2]} {k[3]} {k[4] or ''} [{k[5]!r}] refused, held by {k[6]} {k[7]} {k[8] or ''} [{k[9]!r}]")
  print(f"{bad} refusal(s) between rows of different roles")
  return 1 if bad else 0

if __name__ == "__main__":
  sys.exit(main())
