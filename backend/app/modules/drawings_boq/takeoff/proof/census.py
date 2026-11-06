from __future__ import annotations
import argparse
import json
import os
import sys
from collections import Counter
import yaml
from app.modules.drawings_boq.takeoff.profile import convention as CVN
from app.modules.drawings_boq.takeoff.profile import run as PRUN
from app.modules.drawings_boq.takeoff.proof import completeness_run as CR
from app.modules.drawings_boq.takeoff.proof.reading import sets as S

HERE = os.path.dirname(os.path.abspath(__file__))
CENSUS = os.path.join(HERE, "reading", "census.json")
SPLITS = os.path.join(HERE, "reading", "splits.yaml")
CONF_TOL = 0.011
SMALL_CENSUS = 15
SPLIT_KINDS = ("dev", "test", "first_sight")

def refs_by_case(cases_dir: str | None = None) -> dict:
  out: dict = {}
  for ref in S.find_sets(cases_dir):
    if not ref.link:
      out.setdefault(ref.case, []).append(ref)
  return out

def profile_of(case_refs: list, plains: list) -> dict:
  register = CR.page_rows(CR.merge(plains)) if plains else None
  facts: list = []
  
  for n, ref in enumerate(case_refs):
    facts.extend(PRUN.facts_of_pdf(ref.pdf_path, n * CR.SHEET_SHIFT))
  return CVN.build(facts, register)

def entry(case_refs: list, profile: dict) -> dict:
  return {"office": case_refs[0].office, "pdfs": {r.pdf: r.pdf_key for r in case_refs}, "pages": profile["pages"],
    "points": {k: {"value": v["value"], "confidence": v["confidence"]} for k, v in profile["points"].items()}}

def ranking(sets: dict) -> dict:
  out: dict = {}
  for point in CVN.POINTS:
    seen = [(c, e["office"], e["points"][point]["value"]) for c, e in sets.items()]
    shown = [x for x in seen if x[2] is not None]
    values = Counter(v for _c, _o, v in shown)
    out[point] = {"sets_showing": len(shown), "not_shown": len(seen) - len(shown),
      "values": [{"value": v, "sets": n, "share": round(n / len(shown), 3), "offices": len({o for _c, o, val in shown if val == v})} for v, n in values.most_common()]}
  return out

def build(cases_dir: str | None, reads: dict | None) -> dict:
  sets: dict = {}
  for case, refs in sorted(refs_by_case(cases_dir).items()):
    missing = [r.pdf for r in refs if not r.pdf_path]
    if missing:
      continue
    if reads is not None and not all(r.pdf_key in reads for r in refs):
      continue
    
    plains = [reads[r.pdf_key] for r in refs] if reads is not None else []
    sets[case] = entry(refs, profile_of(refs, plains))
  offices = sorted({e["office"] for e in sets.values()})
  return {"sets": sets, "offices": offices, "ranking": ranking(sets), "small": len(sets) < SMALL_CENSUS,
    "note": f"{len(sets)} sets from {len(offices)} offices: a first picture, not market shares" + ("; fewer than 15 sets" if len(sets) < SMALL_CENSUS else "")}

def load() -> dict | None:
  if not os.path.isfile(CENSUS):
    return None
  with open(CENSUS, encoding="utf-8") as fh:
    return json.load(fh)

def write(doc: dict) -> None:
  with open(CENSUS, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(doc, fh, indent=1, sort_keys=True)
    fh.write("\n")

def splits() -> dict:
  with open(SPLITS, encoding="utf-8") as fh:
    return yaml.safe_load(fh) or {}

def split_problems(cases: dict, doc: dict) -> tuple:
  problems: list = []
  
  groups = doc.get("groups") or {}
  offices = {e["office"] for e in cases.values()}
  if S.UNKNOWN_OFFICE in offices:
    problems.append("a set has no office letter in proof/reading/sets.py")
  first_sets: set = set()
  
  for name, g in groups.items():
    seen: Counter = Counter()
    for kind in SPLIT_KINDS:
      for o in g.get(kind) or []:
        seen[o] += 1
    for o in sorted(offices):
      if seen[o] > 1:
        problems.append(f"{name}: office {o} is in more than one split")
    for o in g.get("first_sight") or []:
      if o in (g.get("dev") or []):
        problems.append(f"{name}: office {o} is both first sight and dev")
    first_sets |= {c for c, e in cases.items() if e["office"] in (g.get("first_sight") or [])}
    
  need = int(doc.get("needed_first_sight") or 0)
  note = None if len(first_sets) >= need else f"{len(first_sets)} first-sight set(s) from offices not in dev against {need} wanted: the corpus holds {len(offices)} offices, so more offices are needed"
  return problems, sorted(first_sets), note

def drift(stored: dict, fresh: dict) -> list:
  out = []
  
  for case, e in fresh["sets"].items():
    old = (stored.get("sets") or {}).get(case)
    if old is None:
      out.append(f"{case} is not in the census")
      continue
    
    for point in CVN.POINTS:
      a, b = old["points"].get(point), e["points"][point]
      if a is None or a["value"] != b["value"] or abs(a["confidence"] - b["confidence"]) > CONF_TOL:
        out.append(f"{case}: {point} was {a and a['value']} ({a and a['confidence']}) and is {b['value']} ({b['confidence']})")
        
  for case in (stored.get("sets") or {}):
    if case not in fresh["sets"]:
      out.append(f"{case} is in the census and was not profiled")
  return out

def table(doc: dict) -> str:
  head = ["set", "office"] + list(CVN.POINTS)
  rows = [head]
  
  for case, e in sorted(doc["sets"].items()):
    rows.append([case, e["office"]] + [f"{(e['points'][p]['value'] or '-')}" for p in CVN.POINTS])
  widths = [max(len(r[i]) for r in rows) for i in range(len(head))]
  lines = ["  ".join(c.ljust(widths[i]) for i, c in enumerate(r)) for r in rows]
  rank = [f"{p}: " + ", ".join(f"{v['value']} {v['sets']} set(s) in {v['offices']} office(s)" for v in r["values"]) + (f"; not shown on {r['not_shown']}" if r["not_shown"] else "") for p, r in doc["ranking"].items()]
  return "\n".join(lines + ["", *rank, "", doc["note"]])

def gate(collector, cases_dir: str | None = None) -> tuple:
  stored = load()
  if stored is None:
    return False, "proof/reading/census.json is missing; write it with `python -m app.modules.drawings_boq.takeoff.proof.census --write`", []
  by_key = {k: plain for k, (_c, plain) in collector.sets.items()}
  problems: list = []
  
  fresh = build(cases_dir, by_key)
  problems += drift(stored, fresh)
  bad, first, note = split_problems(fresh["sets"], splits())
  problems += bad
  if problems:
    return False, f"{len(problems)} census problem(s)", problems
  return True, f"{len(fresh['sets'])} sets from {len(fresh['offices'])} offices profiled on all {len(CVN.POINTS)} points and equal to the stored census; splits keep each office whole; {len(first)} first-sight set(s)" + (f"; {note}" if note else ""), []

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="The convention census: every set profiled on the ten points, ranked, and checked against the splits.")
  ap.add_argument("--cases-dir")
  ap.add_argument("--reads", help="a folder of reading dumps ({case}.json holding {pdf name: plain reading}) to take the register from")
  ap.add_argument("--write", action="store_true")
  args = ap.parse_args(argv)
  reads: dict = {}
  
  if args.reads:
    for case, refs in refs_by_case(args.cases_dir).items():
      path = os.path.join(args.reads, f"{case}.json")
      if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
          dump = json.load(fh)
        for r in refs:
          if r.pdf in dump:
            reads[r.pdf_key] = dump[r.pdf]
            
  doc = build(args.cases_dir, reads if args.reads else None)
  print(table(doc))
  bad, first, note = split_problems(doc["sets"], splits())
  for b in bad:
    print("SPLIT PROBLEM:", b)
  print(f"first-sight sets: {', '.join(first) or 'none'}" + (f" ({note})" if note else ""))
  if args.write:
    write(doc)
    print(f"wrote {CENSUS}")
  return 1 if bad else 0

if __name__ == "__main__":
  sys.exit(main())
