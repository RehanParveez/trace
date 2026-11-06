from __future__ import annotations
import argparse
import collections
import datetime
import json
import os
import sys
from app.engine.measure import rule_registry as RR
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.proof.reading import sets as SETS

BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reading", "baseline_generality.json")
SUBSTRUCTURE = ("EXCAVATION", "FOOTING_LAYOUT")
CLASS_KEYS = ("MATCHED_OK", "MATCHED_WRONG_VALUE", "MISSED_SILENT", "MISSED_REPORTED", "INVENTED_FLAGGED", "INVENTED_SILENT")

def forced_all() -> dict:
  return {r["id"]: True for r in RR.load() if r["status"] != "RETIRED" and r["kind"] != "CONVENTION"}

def tally(rows: list) -> dict:
  t: collections.Counter = collections.Counter()
  
  for row in rows:
    for c in row.get("candidates") or []:
      f = c.facts or {}
      n = int(c.count or 1)
      sa = f.get("set_aside") or {}
      if "stack" in f:
        t["column_stack_members"] += n
        t["planted_column_members"] += n if f.get("planted") else 0
      if f.get("floor_all"):
        t["floor_all_columns"] += n
      if f.get("derived_from") == "FOOTING_SECTION" or "member_of" in f:
        t["footing_family_members"] += n
      if f.get("derived_from") == "BEAM_RUNS":
        t["beam_run_members"] += 1
        t["beam_runs_closed"] += 1 if (f.get("run") or {}).get("closed") else 0
      if sa.get("by") == "ROLE_UNEXPECTED" and sa.get("plan_kind") in SUBSTRUCTURE:
        t["held_on_substructure_layouts"] += n
    bb = (row.get("stats") or {}).get("beam_bands") or {}
    for v in bb.get("views") or []:
      for b in v.get("bands") or []:
        t["bands"] += 1
        t["bands_with_a_support"] += 1 if any(s for s in b.get("supports") or []) else 0
        
  return dict(sorted(t.items()))

def census(cases_dir: str | None, only: list | None = None, partial: str = os.devnull) -> dict:
  from app.modules.drawings_boq.takeoff.proof import benchmark as BM
  out: dict = {}
  
  for case in CIO.list_cases(CIO.HERE):
    if only and case not in only:
      continue
    spec = CIO.load_case(os.path.join(CIO.HERE, case))
    files, missing = CIO.find_files(spec, CIO.cases_dir(cases_dir))
    if missing:
      out[case] = {"office": SETS.office_of(case), "skipped": f"the PDFs are missing: {', '.join(missing)}"}
      continue
    
    blobs = []
    for n in spec["pdfs"]:
      with open(files[n], "rb") as fh:
        blobs.append((n, fh.read()))
    res = BM.read_set(blobs, storeys=spec.get("storeys"), sections=spec.get("sections"), rules=forced_all())
    out[case] = {"office": SETS.office_of(case), "pdfs": {n: tally(rows) for n, rows, _p in res}, "problems": sum(len(p) for _n, _r, p in res)}
    with open(partial, "w", encoding="utf-8") as fh:
      json.dump(out, fh, indent=1, sort_keys=True)
    print(f"{case}: office {SETS.office_of(case)}, {sum(len(r) for _n, r, _p in res)} pages, {json.dumps({n: tally(rows) for n, rows, _p in res})[:300]}", flush=True)
  return out

def class_rows(by_set: dict, alias: str) -> dict:
  out: dict = {}
  for key, v in sorted(by_set.items()):
    a, _, cls = key.partition("|")
    if a != alias:
      continue
    
    n = {k: int(v.get(k) or 0) for k in CLASS_KEYS}
    truth = n["MATCHED_OK"] + n["MATCHED_WRONG_VALUE"] + n["MISSED_SILENT"] + n["MISSED_REPORTED"]
    read = n["MATCHED_OK"] + n["MATCHED_WRONG_VALUE"] + n["INVENTED_FLAGGED"] + n["INVENTED_SILENT"]
    if not truth and not read:
      continue
    out[cls] = {**n, "truth": truth, "recall": round(n["MATCHED_OK"] / truth, 4) if truth else None, "precision": round((n["MATCHED_OK"] + n["MATCHED_WRONG_VALUE"]) / read, 4) if read else None}
  return out

def baseline(score_json: str, census_json: str, cases_dir: str | None = None) -> dict:
  with open(score_json, encoding="utf-8") as fh:
    score = json.load(fh)
  with open(census_json, encoding="utf-8") as fh:
    cen = json.load(fh)
  by_key = {r.pdf_key: r for r in SETS.find_sets(cases_dir)}
  by_set = score["metrics"]["by_set"]
  
  sets: dict = {}
  for s in score["sets"]:
    ref = by_key.get(s["key"])
    members = ((cen.get(ref.case) or {}).get("pdfs") or {}).get(ref.pdf) if ref else None
    sets[s["alias"]] = {"office": ref.office if ref else SETS.UNKNOWN_OFFICE, "reading_split": s["split"], "pages": s["pages"], "classes": class_rows(by_set, s["alias"]), "members_with_rules_on": members or {}}
  return {"pack": "GEN-1", "date": datetime.date.today().isoformat(), "reading_hash": score.get("hash"), "note": "Per-class recall and precision from proof.reading score; members from a read with every ST-1 to ST-5 rule forced on and no decision except the case's own storeys and sections. Offices are letters (proof/reading/sets.py).", "sets": sets}

def gate() -> tuple:
  if not os.path.isfile(BASELINE):
    return False, "proof/reading/baseline_generality.json is missing (write it with `proof.generality baseline`)", []
  with open(BASELINE, encoding="utf-8") as fh:
    doc = json.load(fh)
  missing = [a for a, s in (doc.get("sets") or {}).items() if s.get("office") in (None, "?")]
  return not missing, f"{len(doc.get('sets') or {})} set(s) with their office; {len(missing)} without one", [f"{a} has no office letter in proof/reading/sets.py" for a in missing]

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="The generality baseline: what the ST-1 to ST-5 readers do on every office, per class and per rule.")
  ap.add_argument("--cases-dir", help="the folder with the case PDFs (default: TRACE_CASES_DIR)")
  sub = ap.add_subparsers(dest="cmd", required=True)
  cp = sub.add_parser("census", help="read every case with every consulted rule forced on and count what each rule made")
  cp.add_argument("--out", default="census.json")
  cp.add_argument("--only", nargs="*")
  bp = sub.add_parser("baseline", help="merge a reading_score.json and a census into proof/reading/baseline_generality.json")
  bp.add_argument("--score", required=True)
  bp.add_argument("--census", required=True)
  bp.add_argument("--out", default=BASELINE)
  sub.add_parser("check", help="the baseline exists and every set in it has an office letter")
  args = ap.parse_args(argv)
  
  if args.cmd == "census":
    res = census(args.cases_dir, args.only, args.out)
    with open(args.out, "w", encoding="utf-8") as fh:
      json.dump(res, fh, indent=1, sort_keys=True)
    return 0
  if args.cmd == "baseline":
    doc = baseline(args.score, args.census, args.cases_dir)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
      json.dump(doc, fh, indent=1, sort_keys=True)
      fh.write("\n")
    print(f"{args.out}: {len(doc['sets'])} set(s)")
    return 0
  
  ok, note, lines = gate()
  print(f"{'ok  ' if ok else 'FAIL'}  {note}")
  for ln in lines:
    print(f"      {ln}")
  return 0 if ok else 1

if __name__ == "__main__":
  sys.exit(main())
