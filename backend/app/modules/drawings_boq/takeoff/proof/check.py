from __future__ import annotations
import argparse
import json
import os
import pathlib
import sys

CHECK_CASES = ("plot1", "191c")
TOGGLE_CHECKS = (("plot1", "deduct_opening_plaster"), ("plot1", "formula.frame"))    
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

def stages_file(case: str) -> pathlib.Path:
  return CASES / case / "stages_pass.txt"

def read_stages_pass(case: str) -> list:
  p = stages_file(case)
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
  ap.add_argument("--no-parity", action="store_true", help="skip the parity step (it reads each case that has overrides once more, as the product does)")
  ap.add_argument("--parity-out", default="bench_out", help="the folder parity.md and parity.json are written to")
  ap.add_argument("--no-toggles", action="store_true", help="skip the convention toggle proofs (each reads its case twice)")
  ap.add_argument("--write-hashes", action="store_true", help="write the engine output of this run to proof/cases/<case>/engine_hash.txt instead of comparing")
  args = ap.parse_args(argv)
  from app.modules.drawings_boq.takeoff.proof import import_check as IC
  from app.modules.drawings_boq.takeoff.proof import score as SC
  from app.modules.drawings_boq.takeoff.proof import levels as LV

  results: list = []
  print("== import check")
  results.append(("import check", IC.main() == 0, ""))
  from app.modules.drawings_boq.takeoff.proof import gate17 as G17
  from app.modules.drawings_boq.takeoff.proof import generality as GEN
  print("== gate 17")
  ok17, note17, lines17 = G17.gate()
  results.append(("no case literal outside proof (gate 17)", ok17, note17 if ok17 else note17 + ": " + "; ".join(lines17[:4])))
  okg, noteg, _linesg = GEN.gate()
  results.append(("generality baseline", okg, noteg))
  from app.modules.drawings_boq.takeoff.proof import catalogue_check as CC
  okc, notec, linesc = CC.gate()
  results.append(("element catalogue", okc, notec if okc else notec + ": " + "; ".join(linesc[:4])))

  from app.modules.drawings_boq.takeoff.proof import case_io as CIO
  for case in CHECK_CASES:
    try:
      CIO.load_case(os.path.join(CIO.HERE, case))
      results.append((f"case files {case}", True, ""))
    except ValueError as e:
      results.append((f"case files {case}", False, str(e)))

  print("== score")
  score_args = [*CHECK_CASES, "--out", args.out, "--no-other"] + (["--cases-dir", args.cases_dir] if args.cases_dir else []) + (["--robust"] if args.robust else [])
  SC.main(score_args)
  if not args.no_parity and not args.write_hashes:
    from app.modules.drawings_boq.takeoff.proof import parity as PA
    print("== parity")
    ok_p, note_p = PA.step(args.out, args.cases_dir, args.parity_out, list(CHECK_CASES))
    results.append(("product and proof parity", ok_p, note_p))
  
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
      stages = LV.stages_passed(doc.get("stage_view"))
      stages_file(case).write_text("# Brick and plaster stages within 10% of the QS (line and stage), one per line. proof/check.py --write-hashes rewrites it; proof/check.py fails when the count drops. BRICK_WALLS/ROOF ALL \n" + "\n".join(stages) + ("\n" if stages else ""), encoding="utf8", newline="\n")
      results.append((f"engine output {case}", True, f"written: {got[:16]}, {len(passed)} passing fact(s), {len(stages)} stage(s) within 10%"))
      continue
  
    lv = doc.get("levels") or {}
    rs = lv.get("residuals") or {}
    dc, cr = lv.get("decisions") or {}, lv.get("corrections") or {}
    
    bad = []
    if not lv:
      bad.append("no levels in score.json")
    cv = lv.get("conventions") or {}
    if cv.get("problems"):
      bad.append("conventions: " + "; ".join(cv["problems"]))
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
    
    held = read_stages_pass(case)
    now = LV.stages_passed(doc.get("stage_view"))
    lost_stages = LV.stages_regressions(doc.get("stage_view"), held)
    results.append((f"floor stages {case}", len(now) >= len(held), (f"{len(now)} within 10% now, {len(held)} held; no longer within 10%: " + "; ".join(lost_stages)) if len(now) < len(held) else f"{len(now)} within 10%, {len(held)} held"))
    want = read_hash(case)
    
    if want is None:
      results.append((f"engine output {case}", False, f"{hash_file(case).name} is missing for {case}; this run gave {got[:16]} (write it with --write-hashes once it is right)"))
    elif not got.startswith(want[: min(len(want), len(got))]) or len(want) < 16:
      results.append((f"engine output {case}", False, f"this run gave {got[:16]}, {hash_file(case).name} has {want[:16]}"))
    else:
      results.append((f"engine output {case}", True, got[:16]))

  if not args.write_hashes:
    print("== reading no regression")
    from app.modules.drawings_boq.takeoff.proof.reading import score as RSC
    from app.modules.drawings_boq.takeoff.proof import gate16 as G16
    collected = G16.Collector()
    try:
       ok14, note14 = RSC.gate(args.cases_dir, args.out, on_read=collected)
    except (RuntimeError, ValueError) as e:
      ok14, note14 = False, str(e)
    results.append(("reading no regression (gate 14)", ok14, note14))
    print("== project completeness")
    ok16, note16, lines16 = G16.gate(collected, args.out)
    results.append(("project completeness (gate 16)", ok16, note16 if ok16 else note16 + ": " + "; ".join(lines16[:4])))
    print("== first-upload job")
    from app.modules.drawings_boq.takeoff.proof import gate18 as G18
    ok18, note18, lines18 = G18.gate(collected, args.out)
    results.append(("first-upload job (gate 18)", ok18, note18 if ok18 else note18 + ": " + "; ".join(lines18[:4])))
    print("== convention census")
    from app.modules.drawings_boq.takeoff.proof import census as CEN
    ok19, note19, lines19 = CEN.gate(collected, args.cases_dir)
    results.append(("convention census (gate 19)", ok19, note19 if ok19 else note19 + ": " + "; ".join(lines19[:4])))
    print("== sheet numbers")
    from app.modules.drawings_boq.takeoff.proof import sheet_number_gate as SNG
    ok20, note20, lines20 = SNG.gate(collected, args.cases_dir)
    results.append(("sheet numbers (gate 20)", ok20, note20 if ok20 else note20 + ": " + "; ".join(lines20[:4])))
    print("== bar schedule audit")
    from app.modules.drawings_boq.takeoff.proof import bbs_audit as BAU
    for name in BAU.audit_cases():
      ok15, note15 = BAU.gate_case(name, args.cases_dir)
      results.append((f"bbs audit {name} (gate 15)", ok15, note15))

  if not args.no_toggles:
    print("== convention toggles")
    from app.modules.drawings_boq.takeoff.proof import toggles as TG
    for case, key in TOGGLE_CHECKS:
      r = TG.prove(case, key, args.cases_dir)
      note = r.get("why") or ("moved only " + ", ".join(r["moved"]) + (f"; plaster by {r['plaster_delta_m2']:g} m2 = the openings taken off" if "plaster_delta_m2" in r else "")
        + (f"; {r['rows_named_rule']} accepted rows name the rule" if "rows_named_rule" in r else ""))
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
