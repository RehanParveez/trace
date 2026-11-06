from __future__ import annotations
import argparse
import os
import sys
from app.engine.catalogue import conventions as CV
from app.engine.catalogue import loader as CL
from app.modules.drawings_boq.lab import aliases as AL
from app.modules.drawings_boq.takeoff.completeness import derived_rules as DR
from app.modules.drawings_boq.takeoff.proof import case_io as CIO

def ledger_families() -> dict:
  fams: dict = {}
  for k in sorted(set(AL.KEY_LABEL) | set(AL.SOFTWARE_UNIT)):
    fams.setdefault(k, "bill aliases")
  for case in CIO.list_cases(CIO.HERE):
    for row in CIO.load_case(os.path.join(CIO.HERE, case)).get("expected") or []:
      for f in [row.get("family"), *(row.get("families") or []), str(row.get("key") or "").split("/")[0]]:
        if f:
          fams.setdefault(f, f"expected lines of {case}")
          
  for k in AL.NOT_MEASURED:
    fams.pop(k, None)
  return fams

def derived_problems() -> list:
  out = []
  for it in CL.items():
    if not it.derived:
      continue
    name = it.derived.get("rule")
    rule = DR.RULES.get(name)
    if rule is None:
      out.append(f"{it.id}: derived rule {name} is not in the derived-rule registry")
    elif rule.get("input") and rule["input"] not in {i.name for i in it.inputs}:
      out.append(f"{it.id}: rule {name} needs input {rule['input']}, which the item does not have")
  return out

def problems() -> list:
  out = list(CL.problems())
  if out:
    return out
  out += CV.problems() + derived_problems()
  if out:
    return out
  fams = ledger_families()
  lines = CL.lines()
  for fam, where in sorted(fams.items()):
    if fam not in lines:
      out.append(f"ledger key {fam} ({where}) has no catalogue item")
  for line, ids in sorted(lines.items()):
    if line not in fams:
      out.append(f"{', '.join(ids)}: line {line} is not a ledger key")
  return out

def gate() -> tuple:
  bad = problems()
  if bad:
    return False, f"{len(bad)} problem(s)", bad
  its = CL.items()
  fams = ledger_families()
  billed = sum(1 for i in its if i.billing.PRIVATE_QS)
  return True, f"{len(its)} items load with 0 problems, each with an owner; {len(fams)} ledger keys map to {billed} items; {len(CV.conventions())} Pakistan conventions each with a source and a range, {len(CV.methods())} methods, {sum(1 for i in its if i.derived)} derived items with a known rule", []

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Validate the element catalogue and check that every current ledger key has a catalogue item.")
  ap.add_argument("--owners", action="store_true", help="also count the items by owner pack")
  args = ap.parse_args(argv)
  ok, note, lines = gate()
  print(f"{'ok  ' if ok else 'FAIL'}  catalogue: {note}")
  for ln in lines:
    print(f"      {ln}")
  if args.owners and ok:
    counts: dict = {}
    for i in CL.items():
      counts[i.owner_pack] = counts.get(i.owner_pack, 0) + 1
    for k in sorted(counts):
      print(f"      {k:<8} {counts[k]}")
  return 0 if ok else 1

if __name__ == "__main__":
  sys.exit(main())
