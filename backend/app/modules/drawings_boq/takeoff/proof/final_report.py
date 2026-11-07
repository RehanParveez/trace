from __future__ import annotations
import argparse
import collections
import json
import os
import sys
import yaml
from app.engine.measure import rule_registry as RR

HERE = os.path.dirname(os.path.abspath(__file__))
PACKS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "..", "..", "docs", "packs", "generality.yaml"))

def registry_summary(rules: list | None = None) -> dict:
  rules = RR.load() if rules is None else rules
  by_status = collections.Counter(r.get("status") for r in rules)
  by_default = collections.Counter(r.get("default") for r in rules)
  by_kind = collections.Counter(r.get("kind") for r in rules)
  ready = sorted(r["id"] for r in rules if r.get("status") == "CANDIDATE" and len(RR.offices_met(r)) >= RR.MIN_OFFICES)
  one = sorted(r["id"] for r in rules if r.get("status") == "CANDIDATE" and len(RR.offices_met(r)) == 1)
  none = sorted(r["id"] for r in rules if r.get("status") == "CANDIDATE" and not RR.offices_met(r))
  return {"rules": len(rules), "status": dict(by_status), "default": dict(by_default), "kind": dict(by_kind),
    "two_offices_met_still_candidate": ready, "one_office_met": one, "no_evidence_met": none}

def pack_summary(path: str = PACKS) -> dict:
  with open(path, encoding="utf-8") as fh:
    rows = yaml.safe_load(fh) or []
  recs = [r["generality"] for r in rows if isinstance(r, dict) and "generality" in r]
  first = [r["pack"] for r in recs if not str(r.get("first_sight", "")).lower().startswith("none")]
  return {"records": len(recs), "packs": [r["pack"] for r in recs], "with_first_sight": first, "without_first_sight": len(recs) - len(first)}

def score_summary(folder: str) -> dict:
  out: dict = {}
  for name in sorted(os.listdir(folder)):
    p = os.path.join(folder, name, "score.json")
    if not os.path.isfile(p):
      continue
    with open(p, encoding="utf-8") as fh:
      d = json.load(fh)
    s = d.get("summary") or {}
    sf = d.get("safe") or {}
    out[name] = {"status": d.get("status"), "lines": s.get("lines"), "with_a_number": s.get("with_a_number"), "within_10": s.get("within_10"),
      "within_5": s.get("within_5"), "line_status": s.get("status"), "safe_rows": sf.get("safe_rows"), "safe_precision_pct": sf.get("safe_precision_pct"),
      "safe_coverage_pct": sf.get("safe_coverage_pct"), "hash": str(d.get("hash", ""))[:16], "invariants_failing": sum(1 for i in d.get("invariants") or [] if i.get("status") != "PASS")}
  return out

def render(scores: dict | None, reg: dict, packs: dict) -> str:
  L = ["# Numbers (final_report.py)", ""]
  L += ["## Rule registry", "",
    f"- {reg['rules']} rules; status {json.dumps(reg['status'])}; default {json.dumps(reg['default'])}; kind {json.dumps(reg['kind'])}.",
    f"- Candidates whose evidence meets two offices: {', '.join(reg['two_offices_met_still_candidate']) or 'none'}.",
    f"- Candidates met on one office: {len(reg['one_office_met'])}; with no met evidence: {len(reg['no_evidence_met'])}.", ""]
  L += ["## Pack records", "", f"- {packs['records']} generality records; {packs['without_first_sight']} name no first-sight set; with a first-sight set: {', '.join(packs['with_first_sight']) or 'none'}.", ""]
  if scores:
    L += ["## Scored sets", "", "| set | lines | with a number | within 10% | within 5% | safe rows | safe precision % | invariants failing | hash |", "|---|---|---|---|---|---|---|---|---|"]
    for k, v in scores.items():
      L.append(f"| {k} | {v['lines']} | {v['with_a_number']} | {v['within_10']} | {v['within_5']} | {v['safe_rows']} | {v['safe_precision_pct']} | {v['invariants_failing']} | {v['hash']} |")
    L.append("")
  return "\n".join(L)

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="The numbers of the final report.")
  ap.add_argument("--score", help="the folder written by proof.score --out")
  ap.add_argument("--out", help="write the markdown here instead of printing it")
  a = ap.parse_args(argv)
  text = render(score_summary(a.score) if a.score else None, registry_summary(), pack_summary())
  if a.out:
    with open(a.out, "w", encoding="utf-8") as fh:
      fh.write(text)
  else:
    sys.stdout.write(text + "\n")
  return 0

if __name__ == "__main__":
  raise SystemExit(main())
