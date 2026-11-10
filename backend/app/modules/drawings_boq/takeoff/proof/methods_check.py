from __future__ import annotations
import argparse
import os
import sys
from app.engine.catalogue import methods_qs as MQ

def problems() -> list:
  out = list(MQ.problems())
  if out:
    return out
  
  from app.engine.measure import readings as QS
  from app.modules.drawings_boq import qs_method_service as SV
  from app.modules.drawings_boq import rule_book_service as RBS
  from app.core.exceptions import TraceException
  recorded = {r["id"]: r["answered_on"] for r in QS.READINGS}
  
  for p in MQ.profiles():
    for m in p["methods"]:
      src = m["source"]
      if src["kind"] == MQ.QS:
        when = recorded.get(src["reading"])
        if when is None:
          out.append(f"{m['id']}: reading {src['reading']} is not a recorded answer")
        elif when != src["date"]:
          out.append(f"{m['id']}: the source is dated {src['date']} but reading {src['reading']} was recorded on {when}")
          
    for rule in MQ.rules(p["id"]):
      if not SV.settable(rule["key"]):
        continue
      try:
        RBS.checked_value(rule["key"], rule["value"], rule["scope"])
      except TraceException as exc:
        out.append(f"{rule['id']}: the rule book refuses {rule['key']} = {rule['value']!r}: {exc.message if hasattr(exc, 'message') else exc}")
  for key in MQ.method_keys():
    if key in MQ.building_fact_keys() or key in MQ.choice_keys():
      out.append(f"{key} is a method and also a fact or a choice")
  return out


def case_rules_view() -> list:
  import yaml
  from app.engine.measure import rulebook as RB
  from app.modules.drawings_boq import qs_method_service as SV
  from app.modules.drawings_boq.takeoff.proof import case_io as CIO
  held = {MQ.rule_id(m): m["rule"]["value"] for p in MQ.profiles() for m in p["methods"]}
  out = []
  
  for name in CIO.list_cases():
    folder = os.path.join(CIO.HERE, name)
    with open(os.path.join(folder, "case.yaml"), encoding="utf-8") as fh:
      raw = yaml.safe_load(fh) or {}
    file = raw.get("company_rules")
    if not file or not os.path.isfile(os.path.join(folder, str(file))):
      continue
    rows, _problems = RB.load_rules(os.path.join(folder, str(file)))
    counts: dict = {}
    
    for r in rows:
      mine = MQ.rule_id({"rule": r})
      kind = MQ.kind_of(r["key"])
      if mine in held:
        what = "SAME" if SV.same_value(held[mine], r["value"]) else "DIFFERS"
      elif kind == MQ.FACT:
        what = "FACT"
      elif kind == MQ.CHOICE:
        what = "CHOICE"
      elif kind == MQ.METHOD:
        what = "METHOD"
      else:
        what = "UNKNOWN"
      counts[what] = counts.get(what, 0) + 1
    out.append({"case": name, "file": str(file), "rules": len(rows), "counts": counts})
  return out

def case_rules_text(view: list) -> str:
  return "; ".join(f"{v['case']} {v['rules']} rule(s) (" + ", ".join(f"{n} {k.lower()}" for k, n in sorted(v["counts"].items())) + ")" for v in view) or "no case has company rules"

def gate() -> tuple:
  bad = problems()
  if bad:
    return False, f"{len(bad)} problem(s)", bad
  view = case_rules_view()
  bad += [f"{v['case']}: {v['counts']['UNKNOWN']} rule(s) of {v['file']} have a key the QS method file does not class as a method, a fact or a choice" for v in view if v["counts"].get("UNKNOWN")]
  if bad:
    return False, f"{len(bad)} problem(s)", bad
  n = sum(len(MQ.rules(p["id"])) for p in MQ.profiles())
  return True, f"{len(MQ.profiles())} QS method profile(s) of {n} methods, each with a source that names a recorded answer of the same date or a cell of his workbook, each a rule the rule book accepts; {len(MQ.open_questions())} questions still to put to him; case rules: {case_rules_text(view)}", []

def main(argv: list | None = None) -> int:
  argparse.ArgumentParser(description="Check the QS method file against the recorded answers and the rule book.").parse_args(argv)
  ok, note, lines = gate()
  print(f"{'ok  ' if ok else 'FAIL'}  qs methods: {note}")
  for ln in lines:
    print(f"      {ln}")
  return 0 if ok else 1

if __name__ == "__main__":
  sys.exit(main())
