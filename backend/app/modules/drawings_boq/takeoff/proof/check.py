from __future__ import annotations
import argparse
import json
import pathlib
import sys

CHECK_CASES = ("plot1", "191c")
CASES = pathlib.Path(__file__).resolve().parent / "cases"

def hash_file(case: str) -> pathlib.Path:
  return CASES / case / "engine_hash.txt"

def read_hash(case: str) -> str | None:
  p = hash_file(case)
  if not p.is_file():
    return None
  lines = [ln.strip() for ln in p.read_text(encoding="utf8").splitlines() if ln.strip() and not ln.startswith("#")]
  return lines[0].lower() if lines else None

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Import check, structure scan and the offline score with its engine hashes: the gate before a pack is committed.")
  ap.add_argument("--cases-dir", help="the folder with the case PDFs (default: TRACE_CASES_DIR)")
  ap.add_argument("--out", default="score_out")
  ap.add_argument("--robust", action="store_true")
  ap.add_argument("--write-hashes", action="store_true", help="write the engine output of this run to proof/cases/<case>/engine_hash.txt instead of comparing")
  args = ap.parse_args(argv)
  from app.modules.drawings_boq.takeoff.proof import import_check as IC
  from app.modules.drawings_boq.takeoff.proof import score as SC

  results: list = []
  print("== import check")
  results.append(("import check", IC.main() == 0, ""))

  print("== score")
  score_args = [*CHECK_CASES, "--out", args.out, "--no-other"] + (["--cases-dir", args.cases_dir] if args.cases_dir else []) + (["--robust"] if args.robust else [])
  SC.main(score_args)
  
  for case in CHECK_CASES:
    path = pathlib.Path(args.out) / case / "score.json"
    if not path.is_file():
      results.append((f"score {case}", False, "no score.json: the PDFs were not found (set TRACE_CASES_DIR or --cases-dir) or the case is bad"))
      continue
    doc = json.loads(path.read_text(encoding="utf8"))
    got = str(doc.get("engine_digest") or "")
    if doc.get("engine_errors"):
      results.append((f"score {case}", False, f"the engine reported {len(doc['engine_errors'])} error(s)"))
      continue
  
    if args.write_hashes:
      hash_file(case).write_text(got + "\n", encoding="utf8")
      results.append((f"engine output {case}", True, f"written: {got[:16]}"))
      continue
    want = read_hash(case)
    if want is None:
      results.append((f"engine output {case}", False, f"{hash_file(case).name} is missing for {case}; this run gave {got[:16]} (write it with --write-hashes once it is right)"))
    elif not got.startswith(want[: min(len(want), len(got))]) or len(want) < 16:
      results.append((f"engine output {case}", False, f"this run gave {got[:16]}, {hash_file(case).name} has {want[:16]}"))
    else:
      results.append((f"engine output {case}", True, got[:16]))

  print("\n== result")
  for name, ok, note in results:
    print(f"{'ok  ' if ok else 'FAIL'}  {name}" + (f"   {note}" if note else ""))
  failed = [r for r in results if not r[1]]
  print("check passed" if not failed else f"check FAILED: {len(failed)} of {len(results)}")
  return 1 if failed else 0

if __name__ == "__main__":
  sys.exit(main())
