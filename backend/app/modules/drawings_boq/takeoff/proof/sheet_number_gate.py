from __future__ import annotations
import argparse
import json
import os
import sys
import yaml
from app.modules.drawings_boq.takeoff.proof.reading import sets as S

HERE = os.path.dirname(os.path.abspath(__file__))
PINS = os.path.join(HERE, "reading", "sheet_numbers.json")

def _norm(value) -> str:
  return str(value or "").replace(" ", "").upper()

def truth_numbers(ref) -> dict:
  path = os.path.join(ref.truth_folder, "register.yaml") if ref.truth_folder else None
  if not path or not os.path.isfile(path):
    return {}
  with open(path, encoding="utf-8") as fh:
    rows = yaml.safe_load(fh) or []
  return {int(r["sheet"]): _norm(r.get("sheet_no")) for r in rows if r.get("sheet") is not None}

def score(ref, plain: dict) -> dict | None:
  truth = truth_numbers(ref)
  if not truth:
    return None
  
  read = {int(k): _norm(((v or {}).get("register") or {}).get("sheet_no")) for k, v in (plain.get("pages") or {}).items()}
  numbered = [s for s, n in truth.items() if n]
  right = sum(1 for s in numbered if read.get(s) == truth[s])
  wrong = sum(1 for s in numbered if read.get(s) and read.get(s) != truth[s])
  extra = sum(1 for s, n in truth.items() if not n and read.get(s))
  return {"numbered": len(numbered), "right": right, "wrong": wrong, "extra": extra}

def measure(collector, cases_dir: str | None = None) -> dict:
  out: dict = {}
  for ref in S.find_sets(cases_dir):
    if ref.link or ref.pdf_key not in collector.sets:
      continue
    got = score(ref, collector.sets[ref.pdf_key][1])
    if got:
      out[f"{ref.case}/{ref.pdf}"] = got
  return out

def load() -> dict | None:
  if not os.path.isfile(PINS):
    return None
  with open(PINS, encoding="utf-8") as fh:
    return json.load(fh)

def gate(collector, cases_dir: str | None = None) -> tuple:
  pins = load()
  if pins is None:
    return False, "proof/reading/sheet_numbers.json is missing; write it with `python -m app.modules.drawings_boq.takeoff.proof.sheet_number_gate --reads DIR --write`", []
  now = measure(collector, cases_dir)
  problems = []
  
  for key, pin in sorted(pins.items()):
    got = now.get(key)
    if got is None:
      problems.append(f"{key}: not read in this run")
    elif got["right"] < pin["right"] or got["wrong"] > pin["wrong"]:
      problems.append(f"{key}: {got['right']} of {got['numbered']} right and {got['wrong']} wrong, pinned {pin['right']} right and {pin['wrong']} wrong")
      
  right, numbered = sum(v["right"] for v in now.values()), sum(v["numbered"] for v in now.values())
  wrong, extra = sum(v["wrong"] for v in now.values()), sum(v["extra"] for v in now.values())
  note = f"{right} of {numbered} numbered sheets read with the right number in {len(now)} PDF(s); {wrong} wrong; {extra} given where the truth has none (the truth is an unchecked eye-read)"
  return (not problems), (note if not problems else f"{len(problems)} PDF(s) below their pin"), problems

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Pin the sheet numbers read per PDF, from a folder of reading dumps ({case}.json holding {pdf name: plain reading}).")
  ap.add_argument("--cases-dir")
  ap.add_argument("--reads", required=True)
  ap.add_argument("--write", action="store_true")
  args = ap.parse_args(argv)
  out: dict = {}
  
  for ref in S.find_sets(args.cases_dir):
    path = os.path.join(args.reads, f"{ref.case}.json")
    if ref.link or not os.path.isfile(path):
      continue
    with open(path, encoding="utf-8") as fh:
      dump = json.load(fh)
    if ref.pdf in dump:
      got = score(ref, dump[ref.pdf])
      if got:
        out[f"{ref.case}/{ref.pdf}"] = got
        
  for key, v in sorted(out.items()):
    print(f"{key}: {v['right']} of {v['numbered']} right, {v['wrong']} wrong, {v['extra']} given where the truth has none")
  if args.write:
    with open(PINS, "w", encoding="utf-8") as fh:
      json.dump(out, fh, indent=2, sort_keys=True)
      fh.write("\n")
  return 0

if __name__ == "__main__":
  sys.exit(main())
