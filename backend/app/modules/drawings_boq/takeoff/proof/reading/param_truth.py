from __future__ import annotations
import argparse
import datetime
import json
import os
import re
import sys
from dataclasses import dataclass
import yaml
from app.modules.drawings_boq.takeoff.proof.reading import formats as F
from app.engine.catalogue import param_keys as PK
from app.modules.drawings_boq.takeoff.proof.reading import sets as S
from app.modules.drawings_boq.takeoff.run import vocab as V
from app.modules.drawings_boq.takeoff.proof import case_io as CIO

FILE = "param_truth.yaml"
STATES = ("PRINTED", "NOT_PRINTED")
DRAWN_AS = ("TEXT", "VECTOR")
FIELDS = ("key", "scope", "state", "value", "page", "drawn_as", "truth", "was")
RECALL_OFFICE, RECALL_UNSEEN, PRECISION, MIN_OFFICES = 0.80, 0.70, 0.95, 2
RATIO_SPACES = re.compile(r"\s+")

@dataclass
class ParamTruth:
  key: str
  scope: str
  state: str
  truth: F.TruthStamp
  value: object = None
  page: int | None = None
  drawn_as: str = "TEXT"
  was: dict | None = None

def norm_ratio(value) -> str | None:
  s = RATIO_SPACES.sub(" ", str(value or "").replace("½", " 1/2")).strip()
  s = re.sub(r"\s*:\s*", ":", s)
  s = re.sub(r"(\d) 1/2", r"\1.5", s)
  s = re.sub(r"(?<![\d.])0?\.5(?=:|$)", "0.5", s)
  return s if re.fullmatch(r"\d+(?:\.\d)?(?::\d+(?:\.\d)?){1,2}", s) else None

def same_value(shape: str, truth, read) -> bool:
  if truth is None or read is None:
    return False
  if shape == "MM":
    try:
      return abs(float(truth) - float(read)) <= PK.tolerance_mm()
    except (TypeError, ValueError):
      return False
  a, b = norm_ratio(truth), norm_ratio(read)
  return a is not None and a == b

def _value_problem(entry: dict, value) -> str | None:
  shape = entry["shape"]
  if shape == "MM":
    if isinstance(value, bool) or not isinstance(value, (int, float)):
      return "must be a number of millimetres"
    low, high = entry["range"]
    return None if low <= float(value) <= high else f"{value:g} mm is outside the plausible {low:g} to {high:g}"
  got = norm_ratio(value)
  parts = 2 if shape == "RATIO" else 3
  if got is None or got.count(":") + 1 != parts:
    return f"must be a ratio of {parts} parts written like {'1:4' if parts == 2 else '1:2:4'}"
  return None

def load(folder: str, pages: int = 0) -> list:
  path = os.path.join(folder, FILE)
  if not os.path.isfile(path):
    return []
  p = F._Problems()
  with open(path, encoding="utf-8") as fh:
    try:
      doc = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
      p.add(FILE, "-", "-", f"not valid YAML: {str(exc).splitlines()[0]}")
      raise F.TruthFormatError(p.items)
  if doc is None:
    return []
  
  if not isinstance(doc, list):
    p.add(FILE, "-", "-", "must be a list")
    raise F.TruthFormatError(p.items)
  out, seen = [], {}
  for i, e in enumerate(doc, 1):
    if not isinstance(e, dict):
      p.add(FILE, i, "-", "must be a mapping")
      continue
    F._only(e, FIELDS, FILE, i, p)
    entry = PK.get(str(e.get("key")))
    if entry is None:
      p.add(FILE, i, "key", f"{e.get('key')!r} is not a parameter key; the keys are {', '.join(k['key'] for k in PK.keys())}")
      continue
    scope = str(e.get("scope") or "")
    if scope not in entry["scopes"]:
      p.add(FILE, i, "scope", f"{scope!r} is not a scope of {entry['key']}; the scopes are {', '.join(entry['scopes'])}")
      continue
    state = str(e.get("state") or "").upper()
    if state not in STATES:
      p.add(FILE, i, "state", f"must be one of {', '.join(STATES)}")
      continue
    drawn = str(e.get("drawn_as") or "TEXT").upper()
    if drawn not in DRAWN_AS:
      p.add(FILE, i, "drawn_as", f"must be one of {', '.join(DRAWN_AS)}")
      drawn = "TEXT"
    page = e.get("page")
    value = e.get("value")
    
    if state == "PRINTED":
      bad = _value_problem(entry, value)
      if bad:
        p.add(FILE, i, "value", bad)
      page = F._page(page, pages, FILE, i, "page", p)
    elif value is not None or page is not None:
      p.add(FILE, i, "state", "a NOT_PRINTED row has no value and no page")
    stamp = F._stamp(e.get("truth"), FILE, i, p, True)
    group = (entry["key"], scope)
    if group in seen and (seen[group] != state or state == "NOT_PRINTED"):
      p.add(FILE, i, "state", f"{entry['key']} {scope} has another row that says {seen[group]}" if seen[group] != state else f"{entry['key']} {scope} is listed twice as NOT_PRINTED")
    seen.setdefault(group, state)
    if stamp is not None and not any(x["row"] == i for x in p.items):
      out.append(ParamTruth(entry["key"], scope, state, stamp, value if state == "PRINTED" else None, page if state == "PRINTED" else None, drawn, F._was(e, FILE, i, p)))
  if p.items:
    raise F.TruthFormatError(p.items)
  return out

def found_from_items(items: list) -> list:
  out = []
  for it in items or []:
    key = PK.key_of(it.get("kind"))
    if key is None:
      continue
    value = it.get("value_mm") if PK.get(key)["shape"] == "MM" else it.get("value")
    for page in (it.get("pages") or [None]):
      out.append({"key": key, "scope": str(it.get("scope") or ""), "value": value, "page": page})
  return out

def score_set(rows: list, found: list) -> dict:
  by_key: dict = {}
  unchecked = 0
  for r in rows:
    if r.truth.checked is not True or F.is_draft(r.truth):
      unchecked += 1
      continue
    
    shape = PK.get(r.key)["shape"]
    mine = [f for f in found if f["key"] == r.key and f["scope"] == r.scope]
    k = by_key.setdefault(r.key, {"printed": 0, "hit": 0, "wrong": 0, "missed": 0, "vector": 0, "not_printed": 0, "clean": 0, "invented": 0, "misses": [], "invented_rows": []})
    if r.state == "PRINTED":
      if r.drawn_as == "VECTOR":
        k["vector"] += 1
        continue
      k["printed"] += 1
      right = [f for f in mine if same_value(shape, r.value, f["value"]) and (f["page"] is None or r.page is None or int(f["page"]) == int(r.page))]
      if right:
        k["hit"] += 1
      elif mine:
        k["wrong"] += 1
        k["misses"].append({"scope": r.scope, "page": r.page, "truth": r.value, "read": sorted({str(f["value"]) for f in mine})})
      else:
        k["missed"] += 1
        k["misses"].append({"scope": r.scope, "page": r.page, "truth": r.value, "read": []})
    else:
      k["not_printed"] += 1
      if mine:
        k["invented"] += 1
        k["invented_rows"].append({"scope": r.scope, "read": sorted({str(f["value"]) for f in mine})})
      else:
        k["clean"] += 1
        
  tot = {n: sum(v[n] for v in by_key.values()) for n in ("printed", "hit", "wrong", "missed", "vector", "not_printed", "clean", "invented")}
  return {"keys": by_key, "total": tot, "unchecked": unchecked, "recall": None if not tot["printed"] else tot["hit"] / tot["printed"],
    "precision": None if not tot["not_printed"] else tot["clean"] / tot["not_printed"]}

def verdict(sets: list) -> dict:
  offices = {s["office"] for s in sets if s["score"]["recall"] is not None and s["score"]["recall"] >= RECALL_OFFICE and s["office"] != S.UNKNOWN_OFFICE}
  unseen = [s["set"] for s in sets if s["unseen"] and s["score"]["recall"] is not None and s["score"]["recall"] >= RECALL_UNSEEN]
  clean = sum(s["score"]["total"]["clean"] for s in sets)
  rows = sum(s["score"]["total"]["not_printed"] for s in sets)
  precision = None if not rows else clean / rows
  return {"recall_offices": sorted(offices), "recall_offices_met": len(offices) >= MIN_OFFICES, "recall_unseen_sets": unseen, "recall_unseen_met": bool(unseen),
    "precision": precision, "precision_met": precision is not None and precision >= PRECISION}

def read_pdf(path: str) -> list:
  import pypdfium2 as pdfium
  from app.engine.measure import rule_registry as RR
  from app.modules.drawings_boq.takeoff.prep import facts as FA
  rows: dict = {}
  doc = pdfium.PdfDocument(path)
  try:
    with RR.using({"PARAM_HEIGHTS": True, "PARAM_MIXES": True}):
      for n in range(len(doc)):
        page = doc[n]
        try:
          tp = page.get_textpage()
          try:
            text = tp.get_text_range() or ""
          finally:
            tp.close()
        finally:
          page.close()
        for ln in text.replace("\r", "").split("\n"):
          for it in FA.read_line(ln):
            if PK.key_of(it["kind"]):
              row = rows.setdefault((it["kind"], it.get("scope"), it.get("value"), it.get("value_mm")), {**it, "pages": []})
              if n + 1 not in row["pages"]:
                row["pages"].append(n + 1)
                
  finally:
    doc.close()
  return list(rows.values())

def _draft_row(f: dict) -> dict:
  return {"key": f["key"], "scope": f["scope"], "state": "PRINTED", "value": f["value"], "page": f["page"], "drawn_as": "TEXT",
    "truth": {"by": "DRAFT", "checked": False, "source": F.DRAFT_SOURCE, "date": datetime.date.today().isoformat(), "note": "read by Trace; a person checks it"}}

def _sets(args) -> list:
  out = []
  for ref in S.find_sets(args.cases_dir, args.root):
    if ref.link or not os.path.isdir(ref.truth_folder):
      continue
    out.append(ref)
  return out

def _pages_of(folder: str) -> int:
  try:
    with open(os.path.join(folder, "document.yaml"), encoding="utf-8") as fh:
      return int((yaml.safe_load(fh) or {}).get("pages") or 0)
  except (OSError, ValueError, yaml.YAMLError):
    return 0

def _split_of(folder: str) -> str:
  try:
    with open(os.path.join(folder, "document.yaml"), encoding="utf-8") as fh:
      return str((yaml.safe_load(fh) or {}).get("split") or "").upper()
  except (OSError, yaml.YAMLError):
    return ""

def cmd_validate(args) -> int:
  bad, n = [], 0
  for ref in _sets(args):
    try:
      n += len(load(ref.truth_folder, _pages_of(ref.truth_folder)))
    except F.TruthFormatError as exc:
      bad += [f"{ref.case}/{ref.pdf}: {p['file']}, {p['row']}, {p['field']}: {p['message']}" for p in exc.problems]
  print("\n".join(bad) if bad else f"{n} parameter truth rows, 0 problems")
  return 1 if bad else 0

def cmd_score(args) -> int:
  scored = []
  for ref in _sets(args):
    rows = load(ref.truth_folder, _pages_of(ref.truth_folder))
    if not rows:
      continue
    if ref.pdf_path is None:
      print(f"{ref.case}/{ref.pdf}: the PDF is not in the PDF folder; give --cases-dir.")
      return 1
    
    got = score_set(rows, found_from_items(read_pdf(ref.pdf_path)))
    scored.append({"set": f"{ref.case}/{ref.pdf}", "office": ref.office, "unseen": _split_of(ref.truth_folder) == V.Split.HELDOUT.value, "score": got})
  if not scored:
    print("No set has a param_truth.yaml yet. Write one (see `redraft`) and check its rows.")
    return 0
  
  for s in scored:
    t = s["score"]["total"]
    outlined = "" if not t["vector"] else ", " + str(t["vector"]) + " drawn as outlines (not scored)"
    where = "office " + str(s["office"]) + (" unseen" if s["unseen"] else "")
    print(f"{s['set']}  {where}: PRINTED {t['hit']}/{t['printed']} hit, {t['wrong']} wrong, {t['missed']} missed{outlined};  "
      f"NOT_PRINTED {t['clean']}/{t['not_printed']} clean, {t['invented']} invented;  {s['score']['unchecked']} unchecked rows not scored")
    for key, k in sorted(s["score"]["keys"].items()):
      for m in k["misses"]:
        print(f"    {key} {m['scope']} p{m['page']}: truth {m['truth']}, read {m['read'] or 'nothing'}")
      for m in k["invented_rows"]:
        print(f"    {key} {m['scope']}: not printed, but read {m['read']}")
        
  v = verdict(scored)
  print(f"\nrecall >= {RECALL_OFFICE:.0%} on {MIN_OFFICES} offices: {'met' if v['recall_offices_met'] else 'not met'} ({', '.join(v['recall_offices']) or 'none'})")
  print(f"recall >= {RECALL_UNSEEN:.0%} on an unseen set: {'met' if v['recall_unseen_met'] else 'not met'}")
  print(f"precision >= {PRECISION:.0%} on NOT_PRINTED rows: " + ("no NOT_PRINTED rows yet" if v["precision"] is None else f"{v['precision']:.1%}, {'met' if v['precision_met'] else 'not met'}"))
  if args.json:
    with open(args.json, "w", encoding="utf-8") as fh:
      json.dump({"sets": scored, "verdict": v}, fh, indent=1, default=str)
  return 0

def cmd_redraft(args) -> int:
  wrote = 0
  for ref in _sets(args):
    if ref.pdf_path is None:
      print(f"{ref.case}/{ref.pdf}: the PDF is not in the PDF folder; give --cases-dir.")
      return 1
    
    rows = load(ref.truth_folder, _pages_of(ref.truth_folder))
    have = {(r.key, r.scope, r.page) for r in rows if r.state == "PRINTED"} | {(r.key, r.scope, None) for r in rows if r.state == "NOT_PRINTED"}
    new = [_draft_row(f) for f in found_from_items(read_pdf(ref.pdf_path)) if (f["key"], f["scope"], f["page"]) not in have and (f["key"], f["scope"], None) not in have]
    print(f"{ref.case}/{ref.pdf}: {len(new)} new draft row(s)")
    if new and args.write:
      path = os.path.join(ref.truth_folder, FILE)
      held = []
      if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
          held = yaml.safe_load(fh) or []
      text = yaml.dump([*held, *new], Dumper=F._NoAlias, sort_keys=False, allow_unicode=True, width=200, default_flow_style=False)
      tmp = path + ".tmp"
      with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
      os.replace(tmp, path)
      wrote += len(new)
  print(f"wrote {wrote} draft row(s)" if args.write else "dry run; give --write to add the rows")
  return 0

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(prog="param_truth", description="truth, score and draft rows of the printed parameter keys")
  ap.add_argument("--cases-dir", help=f"the folder with the PDFs (default: {CIO.CASES_DIR_ENV})")
  ap.add_argument("--root", default=CIO.HERE, help="the folder of case folders")
  sub = ap.add_subparsers(dest="cmd", required=True)
  sub.add_parser("validate", help="check every param_truth.yaml; exit 1 on any problem")
  sp = sub.add_parser("score", help="read the PDFs that have param truth and score them: recall on PRINTED rows, precision on NOT_PRINTED rows, by set and office")
  sp.add_argument("--json", help="also write the result as JSON to this file")
  rd = sub.add_parser("redraft", help="add a draft row for every parameter Trace reads that no truth row covers")
  rd.add_argument("--write", action="store_true", help="write the rows (the default is a dry run)")
  args = ap.parse_args(argv)
  return {"validate": cmd_validate, "score": cmd_score, "redraft": cmd_redraft}[args.cmd](args)

if __name__ == "__main__":
  sys.exit(main())
