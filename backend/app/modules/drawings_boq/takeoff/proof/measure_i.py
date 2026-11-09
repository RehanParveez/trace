from __future__ import annotations
import argparse
import os
import sys
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.proof import check as CK
from app.modules.drawings_boq.takeoff.proof import i_result as IR
from app.modules.drawings_boq.takeoff.proof import measure as MS
from app.modules.drawings_boq.takeoff.proof import score as SC
from app.modules.drawings_boq.takeoff.proof.bench import report as RP
from app.modules.drawings_boq.takeoff.proof.reading import __main__ as RDM

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Prints Build File I's before and after with one command: check, product score, reading score, benchmark, then docs/packs/I_RESULT.md.")
  ap.add_argument("--cases-dir", help=f"the folder with the case PDFs (default: {CIO.CASES_DIR_ENV})")
  ap.add_argument("--before", help="a folder with score_out, bench_out and reading_out recorded at the IX-1 commit; without it proof/before_i.yaml is used")
  ap.add_argument("--work", default="i_out", help="the folder the steps write into")
  ap.add_argument("--fresh", action="store_true", help="run every step again even where its output is there")
  ap.add_argument("--no-toggles", action="store_true", help="skip the convention toggle proofs inside the check")
  ap.add_argument("--reads-cache", help="a folder where the benchmark keeps its readings")
  ap.add_argument("--out", help="write the report here instead of docs/packs/I_RESULT.md")
  a = ap.parse_args(argv)
  cfg = IR.load()
  where = MS.phases(a.work, cfg)
  cases = ["--cases-dir", a.cases_dir] if a.cases_dir else []
  if MS.needs(os.path.join(where["score"], "check.json"), a.fresh):
    print("== check", flush=True)
    CK.main(["--out", where["score"], *cases, *(["--no-toggles"] if a.no_toggles else [])])
  if MS.needs(os.path.join(where["product_score"], CK.CHECK_CASES[0], "score.json"), a.fresh):
    print("== product score", flush=True)
    SC.main([*CK.CHECK_CASES, "--out", where["product_score"], "--no-other", "--seed-rules", *cases])
  if MS.needs(os.path.join(where["reading"], "reading_score.json"), a.fresh):
    print("== reading score", flush=True)
    RDM.main([*cases, "score", "--split", "all", "--score-dir", where["score"], "--out", where["reading"]])
  if MS.needs(os.path.join(where["bench"], "rows.jsonl"), a.fresh):
    print("== benchmark", flush=True)
    RP.run(where["bench"], a.cases_dir, where["score"], where["product_score"], None, a.reads_cache, None, cfg["failures_run"], cfg["top_groups"])
  print("== report", flush=True)
  report = ["--score", where["score"], "--bench", where["bench"], "--reading", where["reading"], "--require-gates", *(["--before", a.before] if a.before else [])]
  return IR.main([*report, "--out", a.out] if a.out else [*report, "--publish"])

if __name__ == "__main__":
  sys.exit(main())
