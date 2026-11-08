from __future__ import annotations
import argparse
import json
import os
import sys
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.engine.measure import rule_registry as RR

START_OVERRIDES = 28
LINE_MOVE_PCT = 0.5
REPORT = "parity"
OUT_DIR = "bench_out"

def entries(root: str = CIO.HERE) -> list:
  out = []
  for name in CIO.list_cases(root):
    for e in CIO.load_override_entries(os.path.join(root, name)):
      rule = RR.get(str(e["rule"]))
      out.append({"case": name, "rule": rule["id"], "status": rule["status"], "class": rule.get("class"), "reason": str(e["reason"]), "until": str(e["until"]), "date": str(e["date"])})
  return out

def summary(root: str = CIO.HERE) -> dict:
  held = entries(root)
  rules = RR.rules()
  return {"left": len(held), "start": START_OVERRIDES, "redundant": sum(1 for e in held if e["status"] == "GENERAL"), "general": sum(1 for r in rules if r["status"] == "GENERAL"), "rules": len(rules)}

def bench_line() -> str:
  s = summary()
  return f"Proof overrides left: {s['left']} of {s['start']} at the start of H; rules GENERAL: {s['general']} of {s['rules']}."

def problems(root: str = CIO.HERE) -> list:
  out = []
  try:
    held = entries(root)
  except (ValueError, KeyError) as e:
    return [str(e)]
  out += [f"{e['case']}: the override for {e['rule']} is not needed, the rule is GENERAL and on" for e in held if e["status"] == "GENERAL"]
  out += RR.problems(RR.rules())
  return out

def qs_rows(proof_dir: str, product_dir: str, cases: list) -> list:
  out = []
  for case in cases:
    docs = []
    
    for folder in (proof_dir, product_dir):
      path = os.path.join(folder, case, "score.json")
      if not os.path.isfile(path):
        break
      with open(path, encoding="utf-8") as fh:
        docs.append(json.load(fh))
    if len(docs) != 2:
      continue
    proof, product = docs
    
    by_key = {ln["key"]: ln for ln in product.get("lines") or []}
    moved = []
    
    for ln in proof.get("lines") or []:
      other = by_key.get(ln["key"])
      a, b = ln.get("trace"), (other or {}).get("trace")
      if a is None and b is None:
        continue
      if other is None or a is None or b is None:
        moved.append({"key": ln["key"], "proof": a, "product": b, "pct": None})
        continue
      base = max(abs(a), abs(b))
      pct = 0.0 if base == 0 else abs(a - b) / base * 100.0
      if pct > LINE_MOVE_PCT:
        moved.append({"key": ln["key"], "proof": a, "product": b, "pct": round(pct, 2)})
    out.append({"case": case, "hash_proof": proof["hash"][:16], "hash_product": product["hash"][:16], "lines": len(proof.get("lines") or []),
      "matched_proof": sum(1 for ln in proof.get("lines") or [] if ln.get("status") == "MATCH"), "matched_product": sum(1 for ln in product.get("lines") or [] if ln.get("status") == "MATCH"),
      "moved": sorted(moved, key=lambda m: -(m["pct"] or 1e9))})
  return out

def reading_rows(cases_dir: str | None = None, root: str = CIO.HERE) -> list:
  from app.modules.drawings_boq.takeoff.proof.reading import evidence as EV, formats as F, score as SCR, sets as S
  from app.modules.drawings_boq.takeoff.run import reading_adapter as AD
  rows = []
  
  for ref in S.find_sets(cases_dir, root):
    if ref.link:
      continue
    if CIO.is_audit_case(os.path.join(root, ref.case)):
      continue
    case = CIO.load_case(os.path.join(root, ref.case))
    if not case.get("overrides"):
      continue
    
    found, _problems = CIO.find_files(case, CIO.cases_dir(cases_dir))
    truth = F.load_set(ref.truth_folder)
    counts = {}
    for mode, overrides in (("proof", case["overrides"]), ("product", None)):
      read_rows = AD.read_case({**case, "overrides": overrides}, found)
      with RR.using(overrides):
        read = AD.items_of(read_rows[ref.pdf])
      for o in SCR.element_outcomes("k", truth, read, {}):
        slot = counts.setdefault(o["class"], {"truth": 0, "proof": 0, "product": 0})
        if mode == "proof" and o["outcome"] in EV.TRUTH:
          slot["truth"] += 1
        if o["outcome"] in EV.MATCHED:
          slot[mode] += 1
          
    rows += [{"case": ref.case, "class": cls, **slot} for cls, slot in sorted(counts.items()) if slot["truth"]]
  return rows

def render(held: list, qs: list, reading: list) -> str:
  s = summary()
  L = ["# Parity of the product and the proof", "", f"Overrides left: {s['left']} of {s['start']} at the start of H. Rules GENERAL: {s['general']} of {s['rules']}. Overrides of a GENERAL rule: {s['redundant']}.", "",
    "An override that moves a line of the QS is a measurement the product does not make. The cases below say which lines move.", "", "## Overrides left", "",
    "| Case | Rule | Status | Class | Until | Why |", "|---|---|---|---|---|---|"]
  L += [f"| {e['case']} | {e['rule']} | {e['status']} | {e['class'] or '-'} | {e['until']} | {e['reason']} |" for e in held]
  L += ["", "## Quantities, case by case", "", "| Case | Hash proof | Hash product | Lines | Matching the QS, proof | Matching the QS, product | Lines moved |", "|---|---|---|---|---|---|---|"]
  L += [f"| {r['case']} | {r['hash_proof']} | {r['hash_product']} | {r['lines']} | {r['matched_proof']} | {r['matched_product']} | {len(r['moved'])} |" for r in qs]
  
  for r in qs:
    for m in r["moved"][:12]:
      L.append(f"- {r['case']}: {m['key']} proof {m['proof']} product {m['product']}" + ("" if m["pct"] is None else f" ({m['pct']}%)"))
  L += ["", "## Reading, class by class", "", "| Case | Class | Truth items | Matched, proof | Matched, product | Difference | Rules forced on by the case |", "|---|---|---|---|---|---|---|"]
  for r in reading:
    forced = sorted({e["rule"] for e in held if e["case"] == r["case"] and e["class"] == r["class"]})
    L.append(f"| {r['case']} | {r['class']} | {r['truth']} | {r['proof']} | {r['product']} | {r['proof'] - r['product']} | {', '.join(forced) or '-'} |")
  L.append("")
  return "\n".join(L)

def write(out_dir: str, held: list, qs: list, reading: list) -> str:
  os.makedirs(out_dir, exist_ok=True)
  path = os.path.join(out_dir, REPORT + ".md")
  with open(path, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(render(held, qs, reading))
  with open(os.path.join(out_dir, REPORT + ".json"), "w", encoding="utf-8", newline="\n") as fh:
    json.dump({"overrides": held, "quantities": qs, "reading": reading}, fh, indent=1, sort_keys=True)
  return path

def step(score_dir: str, cases_dir: str | None, out_dir: str, cases: list) -> tuple:
  from app.modules.drawings_boq.takeoff.proof import score as SC
  held = entries()
  with_overrides = [c for c in cases if any(e["case"] == c for e in held)]
  product_dir = os.path.join(score_dir, "product")
  if with_overrides:
    SC.main([*with_overrides, "--out", product_dir, "--no-other", "--product"] + (["--cases-dir", cases_dir] if cases_dir else []))
  qs = qs_rows(score_dir, product_dir, with_overrides)
  path = write(out_dir, held, qs, [])
  bad = problems()
  
  moved = sum(len(r["moved"]) for r in qs)
  note = f"{len(held)} override(s) left, {moved} line(s) move between the proof and the product, report {path}"
  return not bad, note if not bad else note + ": " + "; ".join(bad[:4])

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Set the product beside the proof: overrides left, quantities and reading, case by case.")
  ap.add_argument("--proof-score", help="a score folder made as the proof reads (the default)")
  ap.add_argument("--product-score", help="a score folder made with --product")
  ap.add_argument("--reading", action="store_true", help="also score each class both ways (reads every case with overrides twice)")
  ap.add_argument("--cases-dir")
  ap.add_argument("--out", default=OUT_DIR)
  args = ap.parse_args(argv)
  held = entries()
  
  cases = sorted({e["case"] for e in held})
  qs = qs_rows(args.proof_score, args.product_score, cases) if args.proof_score and args.product_score else []
  reading = reading_rows(args.cases_dir) if args.reading else []
  print(write(args.out, held, qs, reading))
  bad = problems()
  for line in bad:
    print(line)
  return 1 if bad else 0

if __name__ == "__main__":
  sys.exit(main())
