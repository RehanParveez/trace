from __future__ import annotations
import argparse
import hashlib
import json
import os
import sys
from app.engine.catalogue import confidence as CF
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.proof.reading import sets as S
from app.modules.drawings_boq.takeoff.proof.reading import score as SCORE
from app.modules.drawings_boq.takeoff.run import completeness as RC
from app.modules.drawings_boq.takeoff.completeness import self_check as SC
from app.modules.drawings_boq.takeoff.completeness import confidence as CONF

OUTCOMES = "_outcomes.json"
WRITE_AS = CF.PATH

def collect(cases_dir: str | None, cache: str | None = None, root: str = CIO.HERE) -> dict:
  if cache and os.path.isfile(os.path.join(cache, OUTCOMES)):
    with open(os.path.join(cache, OUTCOMES), encoding="utf-8") as fh:
      doc = json.load(fh)
    plains = {}
    for ref in S.find_sets(cases_dir, root):
      path = os.path.join(cache, ref.pdf_key + ".json")
      if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
          plains[ref.pdf_key] = json.load(fh)
    return {**doc, "plains": plains}
  
  plains: dict = {}
  def keep(ref, read):
    plains[ref.pdf_key] = RC.plain_read(read)
  doc = SCORE.run("all", cases_dir, None, root, on_read=keep)
  out = {"outcomes": doc["outcomes"], "sets": doc["sets"], "hash": doc["hash"], "plains": plains}
  if cache:
    os.makedirs(cache, exist_ok=True)
    for k, p in plains.items():
      with open(os.path.join(cache, k + ".json"), "w", encoding="utf-8") as fh:
        json.dump(p, fh, default=str)
    with open(os.path.join(cache, OUTCOMES), "w", encoding="utf-8") as fh:
      json.dump({"outcomes": out["outcomes"], "sets": out["sets"], "hash": out["hash"]}, fh, default=str)
  return out

def projects(cases_dir: str | None, plains: dict, root: str = CIO.HERE) -> dict:
  by_case: dict = {}
  for ref in S.find_sets(cases_dir, root):
    by_case.setdefault(ref.case, []).append(ref)
  out = {}
  for case, refs in by_case.items():
    got = [(n, r) for n, r in enumerate(refs) if r.pdf_key in plains]
    if not got:
      continue
    merged = RC.merge([plains[r.pdf_key] for _n, r in got])
    out[case] = {"plain": merged, "shift": {r.pdf_key: i * RC.SHEET_SHIFT for i, (_n, r) in enumerate(got)}}
  return out

def check_case(plain: dict) -> tuple:
  evidence = RC.evidence_of(plain, None)
  return evidence, SC.run([], evidence)

def keyed_conditions(evidence: dict, checks: list) -> dict:
  cond = CONF.member_conditions(checks)
  out: dict = {}
  for r in evidence.get("observed") or []:
    k = (r["sheet"], r["cls"], SC.norm_mark(r.get("mark")))
    c = cond.get(r["id"], CF.NO_CHECK)
    prev = out.get(k)
    if prev is None or CF.CONDITIONS.index(c) == 1 or (prev == CF.NO_CHECK and c == CF.CHECKS_PASS):
      out[k] = c
  return out

def truth_rows(doc: dict, proj: dict, ref_by_key: dict) -> tuple:
  conds, rows, invented = {}, [], {}
  for case, p in proj.items():
    ev, ch = check_case(p["plain"])
    conds[case] = keyed_conditions(ev, ch)
  alias_key = {s["alias"]: s["key"] for s in doc["sets"]}
  for o in doc["outcomes"]:
    if ":EL:" not in o["id"]:
      continue
    key = alias_key.get(o["set"])
    ref = ref_by_key.get(key)
    if ref is None or ref.case not in proj:
      continue
    if o["side"] == "read":
      if o["outcome"].startswith("INVENTED"):
        invented[o["class"]] = invented.get(o["class"], 0) + 1
      continue
    
    shifted = int(o["sheet"]) + proj[ref.case]["shift"].get(key, 0)
    cond = conds[ref.case].get((shifted, o["class"], SC.norm_mark(o.get("mark"))), CF.NO_CHECK)
    rows.append({"set": o["set"], "split": o["split"], "cls": o["class"], "cond": cond, "right": o["outcome"] == SCORE.OK, "outcome": o["outcome"]})
  return rows, invented

def cells(rows: list) -> dict:
  out: dict = {}
  for r in rows:
    c = out.setdefault(r["cls"], {}).setdefault(r["cond"], {"items": 0, "right": 0, "_sets": set()})
    c["items"] += 1
    c["right"] += 1 if r["right"] else 0
    c["_sets"].add(r["set"])
  return {cls: {cond: {"items": c["items"], "right": c["right"], "sets": len(c["_sets"])} for cond, c in sorted(cs.items())} for cls, cs in sorted(out.items())}

def table_of(rows: list, base: dict) -> dict:
  return {**base, "classes": cells(rows)}

def pooled(rows: list, base: dict, out_of_sample: bool) -> dict:
  sets = sorted({r["set"] for r in rows})
  full = table_of(rows, base)
  bands = {b: {"items": 0, "right": 0} for b in CF.ORDER}
  
  for s in sets:
    table = table_of([r for r in rows if r["set"] != s], base) if out_of_sample else full
    for r in (x for x in rows if x["set"] == s):
      b, _why = CF.band(r["cls"], r["cond"], table)
      bands[b]["items"] += 1
      bands[b]["right"] += 1 if r["right"] else 0
  for b in bands.values():
    b["share"] = None if not b["items"] else round(b["right"] / b["items"], 4)
  return bands

def calibrate(doc: dict, cases_dir: str | None, root: str = CIO.HERE) -> dict:
  base = {k: v for k, v in CF.doc().items() if k in ("thresholds", "min_cell")}
  refs = {r.pdf_key: r for r in S.find_sets(cases_dir, root)}
  proj = projects(cases_dir, doc["plains"], root)
  rows, invented = truth_rows(doc, proj, refs)
  state = {}
  per_case = {}
  
  for case, p in proj.items():
    ev, ch = check_case(p["plain"])
    per_case[case] = {r["check"]: r["result"] for r in ch}
    for r in ch:
      state.setdefault(r["check"], {SC.PASS: 0, SC.FAIL: 0, SC.NOT_CHECKABLE: 0})[r["result"]] += 1
  by_set = {}
  for r in rows:
    x = by_set.setdefault(r["set"], {"split": r["split"], "items": 0, "right": 0})
    x["items"] += 1
    x["right"] += 1 if r["right"] else 0
  digest = hashlib.sha256("\n".join(sorted(f"{o['id']}|{o['outcome']}" for o in doc["outcomes"])).encode()).hexdigest()[:16]
  return {"by_set": by_set, "all_sets": sorted(s["alias"] for s in doc["sets"]), "reading_hash": digest, "rows": rows, "invented": invented, "in_sample": pooled(rows, base, False), "out_of_sample": pooled(rows, base, True), "table": cells(rows), "checks": state, "per_case": per_case,
    "sets": sorted({r["set"] for r in rows}), "projects": len(proj), "base": base}

def decide(result: dict, d: dict) -> dict:
  hi = result["out_of_sample"][CF.HIGH]
  cal = {"sets": len(result["sets"]), "items": len(result["rows"]), "reading_hash": result["reading_hash"], "high_items": hi["items"], "high_right_out_of_sample": hi["share"],
    "high_right_in_sample": result["in_sample"][CF.HIGH]["share"], "medium_right_out_of_sample": result["out_of_sample"][CF.MEDIUM]["share"], "low_right_out_of_sample": result["out_of_sample"][CF.LOW]["share"]}
  new = {**d, "classes": result["table"], "calibrated": cal}
  new["shown"] = CF.shown_by_numbers(new)
  return new

def _pct(x) -> str:
  return "-" if x is None else f"{x * 100:.1f}%"

def markdown(result: dict, new: dict) -> str:
  cal, s = new["calibrated"], new["show_when"]
  lines = ["# Confidence calibration", "",
    f"{cal['items']} truth items of the elements, over {cal['sets']} of the {len(result['all_sets'])} sets (the others have no element truth), in {result['projects']} projects (reading score hash {cal['reading_hash']}). A truth item is right when Trace read it with the right value; a missed item counts as not right.",
    f"Thresholds are fixed, not tuned: High at {_pct(new['thresholds']['high'])}, Low under {_pct(new['thresholds']['low'])}.", "",
    "## Out of sample (each set banded by a table made without it)", "", "| Band | Items | Right | Share right |", "| --- | ---: | ---: | ---: |"]
  for b in reversed(CF.ORDER):
    x = result["out_of_sample"][b]
    lines.append(f"| {b} | {x['items']} | {x['right']} | {_pct(x['share'])} |")
  lines += ["", "In sample (the table judged on the sets it was made from):", "", "| Band | Items | Right | Share right |", "| --- | ---: | ---: | ---: |"]
  
  for b in reversed(CF.ORDER):
    x = result["in_sample"][b]
    lines.append(f"| {b} | {x['items']} | {x['right']} | {_pct(x['share'])} |")
  verdict = "SHOWN" if new["shown"] else "NOT SHOWN"
  kill = cal["high_right_out_of_sample"] is not None and cal["high_right_out_of_sample"] < new["kill"]["high_right"]
  lines += ["", f"## Decision: confidence is {verdict}", "",
    f"High was right {_pct(cal['high_right_out_of_sample'])} of the time out of sample on {cal['high_items']} items; the target is {_pct(s['high_right'])} on at least {s['min_items']} items.",
    ("High was right less often than the kill figure " + _pct(new["kill"]["high_right"]) + ": confidence is not to be shown to clients.") if kill else ("Confidence stays hidden until High reaches the target." if not new["shown"] else "The target is reached."), "",
    "## What the checks did", "", "| Check | Pass | Fail | Cannot check |", "| --- | ---: | ---: | ---: |"]
  
  for cid, c in result["checks"].items():
    lines.append(f"| {cid} | {c[SC.PASS]} | {c[SC.FAIL]} | {c[SC.NOT_CHECKABLE]} |")
  lines += ["", "## Sets", "", "| Set | Split | Truth items | Right | Share right |", "| --- | --- | ---: | ---: | ---: |"]
  for alias in result["all_sets"]:
    x = result["by_set"].get(alias)
    lines.append(f"| {alias} | {x['split']} | {x['items']} | {x['right']} | {_pct(x['right'] / x['items'])} |" if x else f"| {alias} | - | 0 | 0 | no element truth |")
  lines += ["", "## Share right by class and condition", "", "| Class | Condition | Items | Right | Share | Sets |", "| --- | --- | ---: | ---: | ---: | ---: |"]
  for cls, cs in result["table"].items():
    for cond, c in cs.items():
      lines.append(f"| {cls} | {cond} | {c['items']} | {c['right']} | {_pct(c['right'] / c['items'])} | {c['sets']} |")
  if result["invented"]:
    lines += ["", "## Readings with no truth item (invented), not counted above", "", ", ".join(f"{k} {v}" for k, v in sorted(result["invented"].items()))]
  lines += ["", "This is calibrated on readings against the reading truth. A priced line is not yet calibrated against the QS's quantities: that needs the QS to confirm answers (IX-2), and until then the line's confidence is the lowest of its readings'."]
  return "\n".join(lines) + "\n"

def dump_yaml(new: dict) -> str:
  import yaml
  head = open(WRITE_AS, encoding="utf-8").read().split("\nthresholds:")[0]
  keep = {k: new[k] for k in ("thresholds", "show_when", "kill", "min_cell", "shown", "calibrated", "classes", "text")}
  return head + "\n" + yaml.safe_dump(keep, sort_keys=False, default_flow_style=None, width=1000)

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Calibrate the confidence of a reading against the truth sets: writes calibration.md to --out and, with --write, engine/catalogue/confidence.yaml.")
  ap.add_argument("--out", default="bench_out")
  ap.add_argument("--cases-dir")
  ap.add_argument("--cache", help="a folder where the readings and the reading score are kept so a second run does not read the PDFs again; delete it when the reader changes")
  ap.add_argument("--write", action="store_true", help="write the calibration into confidence.yaml")
  a = ap.parse_args(argv)
  
  doc = collect(a.cases_dir, a.cache)
  result = calibrate(doc, a.cases_dir)
  new = decide(result, CF.doc())
  os.makedirs(a.out, exist_ok=True)
  with open(os.path.join(a.out, "calibration.md"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write(markdown(result, new))
  if a.write:
    with open(WRITE_AS, "w", encoding="utf-8", newline="\n") as fh:
      fh.write(dump_yaml(new))
  cal = new["calibrated"]
  print(f"calibrated on {cal['items']} truth items over {cal['sets']} sets: High right {_pct(cal['high_right_out_of_sample'])} out of sample on {cal['high_items']} items; confidence {'SHOWN' if new['shown'] else 'NOT SHOWN'}; wrote {os.path.join(a.out, 'calibration.md')}" + ("; wrote confidence.yaml" if a.write else ""))
  return 0

if __name__ == "__main__":
  sys.exit(main())
