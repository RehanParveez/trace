from __future__ import annotations
import argparse
import json
import pathlib
import sys

CHECK_CASES = ("plot1", "191c")
TOGGLE_CHECKS = (("plot1", "deduct_opening_plaster"),)    
CASES = pathlib.Path(__file__).resolve().parent / "cases"

def hash_file(case: str) -> pathlib.Path:
  return CASES / case / "engine_hash.txt"

def facts_file(case: str) -> pathlib.Path:
  return CASES / case / "facts_pass.txt"

def read_facts_pass(case: str) -> list:
  p = facts_file(case)
  if not p.is_file():
    return []
  return [ln for ln in p.read_text(encoding="utf8").splitlines() if ln.strip() and not ln.startswith("#")]

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
  ap.add_argument("--no-toggles", action="store_true", help="skip the convention toggle proofs (each reads its case twice)")
  ap.add_argument("--write-hashes", action="store_true", help="write the engine output of this run to proof/cases/<case>/engine_hash.txt instead of comparing")
  args = ap.parse_args(argv)
  from app.modules.drawings_boq.takeoff.proof import import_check as IC
  from app.modules.drawings_boq.takeoff.proof import score as SC
  from app.modules.drawings_boq.takeoff.proof import levels as LV

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
    if args.robust and not args.write_hashes:
      rb = doc.get("robust") or {}
      over = {name: v for name, v in (rb.get("variants") or {}).items() if v.get("error") or v.get("moved")}
      note = "; ".join(f"{name}: " + (v["error"] if v.get("error") else f"{v['moved']} line(s) over {rb.get('move_pct', 1.0):g}%, worst {v['worst_key']} {v['worst_pct']}%") for name, v in over.items())
      results.append((f"robustness {case}", not over and bool(rb), note or ("" if rb else "no robustness run in score.json")))
    if args.write_hashes:
      hash_file(case).write_text(got + "\n", encoding="utf8")
      passed = LV.facts_passed(doc.get("facts") or [])
      facts_file(case).write_text("# Printed facts that pass (their text), one per line. python scripts/check.py --write-hashes rewrites it; proof/check.py fails when one of them stops passing.\n" + "\n".join(passed) + ("\n" if passed else ""), encoding="utf8", newline="\n")
      results.append((f"engine output {case}", True, f"written: {got[:16]}, {len(passed)} passing fact(s)"))
      continue
  
    lv = doc.get("levels") or {}
    rs = lv.get("residuals") or {}
    dc, cr = lv.get("decisions") or {}, lv.get("corrections") or {}
    
    bad = []
    if not lv:
      bad.append("no levels in score.json")
    if rs.get("missing"):
      bad.append(f"over {rs['limit_pct']:g}% with no entry in residuals.yaml: {', '.join(rs['missing'])}")
    if rs.get("stale"):
      bad.append(f"stale entries (the line is within {rs['limit_pct']:g}% or not there): {', '.join(rs['stale'])}")
    if dc.get("unmatched"):
      bad.append("decisions that match nothing: " + ", ".join(x["id"] for x in dc["unmatched"]))
    if cr.get("problems"):
      bad.append("corrections that match nothing: " + "; ".join(cr["problems"]))
    results.append((f"residuals {case}", not bad, "; ".join(bad) if bad else f"{rs.get('over', 0)} line(s) over {rs.get('limit_pct', 5):g}%, all explained"))
    lost = LV.facts_regressions(doc.get("facts") or [], read_facts_pass(case))
    results.append((f"facts {case}", not lost, ("no longer pass: " + "; ".join(lost)) if lost else f"{len(read_facts_pass(case))} passing fact(s) still pass"))
    want = read_hash(case)
    
    if want is None:
      results.append((f"engine output {case}", False, f"{hash_file(case).name} is missing for {case}; this run gave {got[:16]} (write it with --write-hashes once it is right)"))
    elif not got.startswith(want[: min(len(want), len(got))]) or len(want) < 16:
      results.append((f"engine output {case}", False, f"this run gave {got[:16]}, {hash_file(case).name} has {want[:16]}"))
    else:
      results.append((f"engine output {case}", True, got[:16]))

  if not args.no_toggles:
    print("== convention toggles")
    from app.modules.drawings_boq.takeoff.proof import toggles as TG
    for case, key in TOGGLE_CHECKS:
      r = TG.prove(case, key, args.cases_dir)
      note = r.get("why") or ("moved only " + ", ".join(r["moved"]) + (f"; plaster by {r['plaster_delta_m2']:g} m2 = the openings taken off" if "plaster_delta_m2" in r else ""))
      if r.get("stray"):
        note = "also moved " + ", ".join(r["stray"])
      results.append((f"toggle {case} {key}", bool(r["ok"]), note))

  print("\n== result")
  for name, ok, note in results:
    print(f"{'ok  ' if ok else 'FAIL'}  {name}" + (f"   {note}" if note else ""))
  failed = [r for r in results if not r[1]]
  print("check passed" if not failed else f"check FAILED: {len(failed)} of {len(results)}")
  return 1 if failed else 0

if __name__ == "__main__":
  sys.exit(main())
