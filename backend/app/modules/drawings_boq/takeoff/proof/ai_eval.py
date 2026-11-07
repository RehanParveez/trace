from __future__ import annotations
import argparse
import os
import sys
import yaml
from app.modules.drawings_boq.takeoff.proof.reading import sets as S
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.ai_reader import cache as CACHE
from app.modules.drawings_boq.takeoff.ai_reader import compare as CMP
from app.modules.drawings_boq.takeoff.ai_reader import contract as C
from app.modules.drawings_boq.takeoff.ai_reader import cost as COST
from app.modules.drawings_boq.takeoff.proof.reading.formats import KEY_LEN

TRUTH_KEYS = ("discipline", "floor", "title", "sheet_no")

def truth_rows(folder: str) -> dict:
  path = os.path.join(folder, "register.yaml")
  if not os.path.isfile(path):
    return {}
  with open(path, encoding="utf-8") as fh:
    rows = yaml.safe_load(fh) or []
  return {int(r["sheet"]): {k: r.get(k) for k in TRUTH_KEYS} for r in rows if r.get("sheet") is not None}

def evaluate(cases_dir: str | None = None, root: str = CIO.HERE) -> dict:
  refs = {}
  for ref in S.find_sets(cases_dir, root):
    refs.setdefault(ref.pdf_key, ref)
  out: dict = {}
  for name in CIO.list_cases(root, audit=True):
    entries = CACHE.read_all(os.path.join(root, name))
    for e in entries:
      slot = out.setdefault((name, e["task"]), {"entries": [], "refs": set()})
      slot["entries"].append(e)
      slot["refs"].add(str(e["pdf_sha256"])[:KEY_LEN])
      
  report: dict = {}
  for (case, task), slot in sorted(out.items()):
    entries = slot["entries"]
    status = {"OK": 0, "INVALID": 0}
    shape_ok = 0
    check_total = check_pass = 0
    facts = {k: {a: 0 for a in CMP.AGREEMENTS} for k in C.KEYS}
    unmatched = 0
    
    for e in entries:
      status[e["status"]] = status.get(e["status"], 0) + 1
      clean, _problems = C.validate(e.get("answer"))
      shape_ok += 1 if clean is not None else 0
      for v in e.get("validators") or []:
        check_total += 1
        check_pass += 1 if v["passed"] else 0
      ref = refs.get(str(e["pdf_sha256"])[:KEY_LEN])
      truth = truth_rows(ref.truth_folder).get(int(e["page"])) if ref else None
      if truth is None or clean is None:
        unmatched += 1
        continue
      
      for rec in CMP.compare(truth, clean):
        facts[rec["fact_key"]][rec["agreement"]] += 1
    report[f"{case}/{task}"] = {"entries": len(entries), "status": status, "shape_ok": shape_ok, "checks": [check_pass, check_total], "unmatched": unmatched, "facts": facts,
      "cost": COST.summarise(entries), "models": sorted({e["model"] for e in entries})}
  return report

def lines(report: dict) -> list:
  out = []
  for key, r in report.items():
    out.append(f"{key}: {r['entries']} cached answer(s), models {', '.join(r['models'])}; {r['shape_ok']} with a valid shape, {r['status'].get('INVALID', 0)} unusable; evidence checks passed {r['checks'][0]} of {r['checks'][1]}; {r['unmatched']} without a truth row")
    for fact, a in r["facts"].items():
      n = sum(a.values())
      if n:
        out.append(f"    {fact}: {a['AGREE']} agree, {a['DISAGREE']} differ, {a['AI_ONLY']} AI only, {a['RULE_ONLY']} truth only (of {n})")
    c = r["cost"]
    out.append(f"    cost: {c['input_tokens']} input and {c['output_tokens']} output tokens, {c['seconds']} s, {c['usd']} USD, {c['pkr']} PKR" + (f"; no price set for {', '.join(c['unpriced_models'])}" if c["unpriced_models"] else ""))
  return out

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Score the cached AI answers of every case against its truth folder and report time and cost. It reads files only and never calls a model.")
  ap.add_argument("--cases-dir", default=None)
  args = ap.parse_args(argv)
  report = evaluate(args.cases_dir)
  if not report:
    print("No ai_cache folder holds an answer yet.")
    return 0
  for ln in lines(report):
    print(ln)
  return 0

if __name__ == "__main__":
  sys.exit(main())
