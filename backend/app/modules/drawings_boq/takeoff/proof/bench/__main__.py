from __future__ import annotations
import argparse
import sys
from app.modules.drawings_boq.takeoff.proof.bench import ai_money as AM
from app.modules.drawings_boq.takeoff.proof.bench import report as RP

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Score every set against the catalogue's 263 items offline and print a ranked list of what to build next. Writes rows.jsonl, bench.md and failures.json to --out and appends one line per set and run to history.csv.")
  ap.add_argument("--out", default="bench_out")
  ap.add_argument("--cases-dir")
  ap.add_argument("--score", help="a score output folder (proof.score --out): its engine lines feed the proof run and the answers comparison")
  ap.add_argument("--product-score", help="a score output folder made with --seed-rules: its engine lines feed the product run")
  ap.add_argument("--only", nargs="*", help="case names")
  ap.add_argument("--reads-cache", help="a folder where the readings are kept so a second run does not read the PDFs again; delete it when the reader changes")
  ap.add_argument("--history", default=RP.HISTORY, help="the trend file the run appends to")
  ap.add_argument("--no-history", action="store_true")
  ap.add_argument("--failures-run", choices=(RP.PRODUCT, RP.PROOF), default=RP.PRODUCT)
  ap.add_argument("--top", type=int, default=20)
  ap.add_argument("--ai", metavar="TASK[:VARIANT]", help="read each set a second time with the accepted cached answers of the task (NOTE_FACT) as AI_READ inputs and write ai_money.json beside bench.md; VARIANT names the prompt variant whose answers are used, the latest answer of each page otherwise")
  a = ap.parse_args(argv)
  if a.ai:
    try:
      AM.parse(a.ai)
    except ValueError as exc:
      ap.error(str(exc))
    if not a.reads_cache:
      ap.error("--ai reads each set again with the answers on: give --reads-cache so that the PDFs are read once for each")
  return RP.run(a.out, a.cases_dir, a.score, a.product_score, a.only, a.reads_cache, None if a.no_history else a.history, a.failures_run, a.top, a.ai)

if __name__ == "__main__":
  sys.exit(main())
