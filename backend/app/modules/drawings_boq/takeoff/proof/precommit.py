from __future__ import annotations
import argparse
import json
import os
import sys
import yaml
from app.modules.drawings_boq.takeoff.proof import case_io as CIO

KEY_LEN = 12
SHOWN = 12

def step_import() -> tuple:
  from app.modules.drawings_boq.takeoff.proof import import_check as IC
  return IC.main() == 0, "no module fails to import and no name is undefined", []

def step_files() -> tuple:
  bad, count = [], 0
  for folder, _dirs, names in os.walk(CIO.HERE):
    for name in sorted(names):
      if not name.endswith((".yaml", ".yml", ".json")):
        continue
      path = os.path.join(folder, name)
      count += 1
      try:
        with open(path, encoding="utf-8") as fh:
          json.load(fh) if name.endswith(".json") else yaml.safe_load(fh)
      except (yaml.YAMLError, ValueError) as e:
        bad.append(f"{os.path.relpath(path, CIO.HERE)}: {str(e).splitlines()[0]}")
        
  return not bad, f"{count} case file(s) parse" if not bad else f"{len(bad)} of {count} case file(s) do not parse", bad

def step_validate(cases_dir: str | None) -> tuple:
  import argparse as AP
  import contextlib
  import io
  from app.modules.drawings_boq.takeoff.proof.reading import __main__ as RM
  
  buf = io.StringIO()
  with contextlib.redirect_stdout(buf):
    code = RM.cmd_validate(AP.Namespace(cases_dir=cases_dir, root=CIO.HERE))
  lines = buf.getvalue().strip().splitlines()
  return code == 0, lines[-1] if lines else "no output", lines[:-1]

def step_keys() -> tuple:
  bad, count = [], 0
  for case in CIO.list_cases(CIO.HERE, audit=True):
    raw = CIO._yaml(os.path.join(CIO.HERE, case, "case.yaml")) or {}
    keys = {str(v)[:KEY_LEN] for v in (raw.get("sha256") or {}).values()}
    keys |= {str((raw.get("structure") or {}).get("sha256") or "")[:KEY_LEN]} - {""}
    base = os.path.join(CIO.HERE, case, "reading")
    if not os.path.isdir(base):
      continue
    
    for name in sorted(os.listdir(base)):
      if not os.path.isdir(os.path.join(base, name)):
        continue
      count += 1
      if name not in keys:
        bad.append(f"{case}/reading/{name} is not the sha256 prefix of any PDF of the case")
  return not bad, f"{count} truth folder(s) are named by their PDF's sha256" if not bad else f"{len(bad)} truth folder(s) misnamed", bad

def step_gate17() -> tuple:
  from app.modules.drawings_boq.takeoff.proof import gate17 as G17
  return G17.gate()

def step_catalogue() -> tuple:
  from app.modules.drawings_boq.takeoff.proof import catalogue_check as CC
  return CC.gate()

def step_gates(cases_dir: str | None, out: str, no_toggles: bool) -> tuple:
  from app.modules.drawings_boq.takeoff.proof import check as CK
  argv = ["--out", out] + (["--cases-dir", cases_dir] if cases_dir else []) + (["--no-toggles"] if no_toggles else [])
  return CK.main(argv) == 0, "score, engine hashes, residuals, gate 14, gate 15, gate 16", []

def step_baseline(cases_dir: str | None, out: str) -> tuple:
  from app.modules.drawings_boq.takeoff.proof import score as SC
  pins = SC.load_pins()
  todo = [k for k in sorted(pins) if not os.path.isfile(os.path.join(out, k, "score.json"))]
  
  if todo:
    SC.main([*todo, "--out", out, "--no-other"] + (["--cases-dir", cases_dir] if cases_dir else []))
  notes, ok = [], bool(pins)
  for k in sorted(pins):
    path = os.path.join(out, k, "score.json")
    if not os.path.isfile(path):
      ok = False
      notes.append(f"{k}: no score.json")
      continue
    
    with open(path, encoding="utf-8") as fh:
      status = SC.pin_status(k, json.load(fh), pins)
    ok = ok and status.startswith("unchanged")
    notes.append(f"{k} {status}")
  return ok, "; ".join(notes) if notes else "baseline_scores.json pins no case", []

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Run before every commit: import check, case files, reading validate, truth folder keys, the gates, then the pinned baseline. Stops at the first failure.")
  ap.add_argument("--cases-dir", help="the folder with the case PDFs (default: TRACE_CASES_DIR)")
  ap.add_argument("--out", default="score_out")
  ap.add_argument("--no-toggles", action="store_true", help="skip the convention toggle proofs inside the gates")
  args = ap.parse_args(argv)
  cases_dir = CIO.cases_dir(args.cases_dir)
  
  steps = [("import check", step_import), ("case files", step_files), ("reading validate", lambda: step_validate(cases_dir)), ("truth folder keys", step_keys),
    ("gate 17", step_gate17), ("catalogue", step_catalogue), ("gates", lambda: step_gates(cases_dir, args.out, args.no_toggles)), ("baseline", lambda: step_baseline(cases_dir, args.out))]
  for name, run in steps:
    ok, note, details = run()
    print(f"{'ok  ' if ok else 'FAIL'}  {name}: {note}")
    if not ok:
      for line in details[:SHOWN]:
        print(f"      {line}")
      if len(details) > SHOWN:
        print(f"      and {len(details) - SHOWN} more")
      print("precommit FAILED: do not commit")
      return 1
    
  print("precommit passed")
  return 0

if __name__ == "__main__":
  sys.exit(main())
