from __future__ import annotations
import dataclasses
import datetime
import enum
import hashlib
import json
import math
import os
import random
import shutil
import yaml
from app.modules.drawings_boq.takeoff.proof.reading import sets as S
from app.modules.drawings_boq.takeoff.proof.reading import formats as F
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.proof.reading import adapter as AD
from app.modules.drawings_boq.takeoff.proof import case as CASE
from app.modules.drawings_boq.takeoff.proof.reading import vocab as V
from app.modules.drawings_boq.takeoff.proof.reading import corpus as CP
from app.modules.drawings_boq.takeoff.proof.reading import profile as PR

SAMPLE_SHARE = 0.10
SAMPLE_MIN = 10
FIRST_SIGHT = "first_sight.json"
DEFAULT_TIER = "B"

class Refused(Exception):
  pass

def plain(v):
  if isinstance(v, enum.Enum):
    return v.value
  if dataclasses.is_dataclass(v) and not isinstance(v, type):
    return {k: plain(x) for k, x in ((f.name, getattr(v, f.name)) for f in dataclasses.fields(v))}
  if isinstance(v, dict):
    return {str(k): plain(x) for k, x in v.items()}
  if isinstance(v, (list, tuple, set)):
    return [plain(x) for x in v]
  if v is None or isinstance(v, (str, int, float, bool)):
    return v
  return str(v)

def digest_of(items: list) -> str:
  return hashlib.sha256(json.dumps(items, sort_keys=True).encode("utf-8")).hexdigest()

def existing(pdf_key: str, cases_dir: str | None, root: str) -> tuple:
  for ref in S.find_sets(cases_dir, root):
    if ref.pdf_key == pdf_key:
      try:
        alias = F.load_set(ref.truth_folder).document.alias
      except (OSError, ValueError, KeyError, TypeError):
        alias = ref.case
      return ref.case, alias
    
  for name in CIO.list_cases(root, audit=True):
    if os.path.isdir(os.path.join(root, name, S.READING, pdf_key)):
      return name, name
  return None, None

def _add_to_case(folder: str, pdf: str, sha: str, name: str, note: str | None) -> None:
  path = os.path.join(folder, "case.yaml")
  if os.path.isfile(path):
    with open(path, encoding="utf-8") as fh:
      text = fh.read()
    lead = [ln for ln in text.splitlines() if ln.startswith("#")]
    raw = yaml.safe_load(text) or {}
    
  else:
    os.makedirs(folder, exist_ok=True)
    lead, raw = [], {"name": name, "tier": DEFAULT_TIER, "pdfs": [], "sha256": {}, "note": note or "Taken in by proof.reading intake; held out; no QS bill."}
  raw.setdefault("pdfs", []).append(pdf)
  raw.setdefault("sha256", {})[pdf] = sha
  with open(path, "w", encoding="utf-8", newline="\n") as fh:
    if lead:
      fh.write("\n".join(lead) + "\n")
    yaml.safe_dump(raw, fh, sort_keys=False, allow_unicode=True, width=200)
  facts = os.path.join(folder, "facts.yaml")
  if not os.path.isfile(facts):
    with open(facts, "w", encoding="utf-8", newline="\n") as fh:
      fh.write("[]\n")

def _sample(items: list, key: str) -> list:
  if not items:
    return []
  n = min(len(items), max(SAMPLE_MIN, math.ceil(SAMPLE_SHARE * len(items))))
  pick = random.Random(key).sample(range(len(items)), n)
  return [items[i] for i in sorted(pick)]

def _eye_pages(prof: dict, read: AD.SetRead, per_page: dict) -> list:
  out = []
  for p in prof["pages"]:
    why = []
    if p["text_type"] != "TEXT":
      why.append(f"text type {p['text_type']}")
    if PR.damaged_fonts(p):
      why.append("damaged font")
    if not per_page.get(p["sheet"]):
      why.append("nothing read")
    info = read.pages.get(p["sheet"])
    if info is not None and info.mm_per_pt is None:
      why.append("no scale")
    out.append((p["sheet"], p["text_type"], per_page.get(p["sheet"], 0), why))
  return out

def intake(pdf_path: str, case: str, consultant: str | None, cases_dir: str | None, root: str, alias: str | None = None, note: str | None = None, declared: dict | None = None) -> dict:
  if not os.path.isfile(pdf_path):
    raise Refused(f"{pdf_path} is not a file.")
  files_dir = CIO.cases_dir(cases_dir)
  if not files_dir:
    raise Refused("Give --cases-dir (or set TRACE_CASES_DIR): the PDF has to sit in the PDF folder.")
  sha = CASE.sha256_of(pdf_path)
  key = sha[:F.KEY_LEN]
  owner, known = existing(key, cases_dir, root)
  if owner:
    raise Refused(f"This PDF is already in the corpus: case {owner}, alias {known} (key {key}). Nothing was written.")
  name = os.path.basename(pdf_path)
  target = os.path.join(files_dir, name)
  if os.path.abspath(target) != os.path.abspath(pdf_path):
    if os.path.exists(target) and CASE.sha256_of(target) != sha:
      raise Refused(f"{target} exists with other content; rename the PDF.")
    if not os.path.exists(target):
      shutil.copy2(pdf_path, target)
      
  prof = PR.profile_pdf(target)
  folder = os.path.join(root, case)
  truth = os.path.join(folder, S.READING, key)
  _add_to_case(folder, name, sha, case, note)
  os.makedirs(truth)
  
  doc = {"alias": alias or case, "split": V.Split.HELDOUT.value.lower(), "case": case, "sha256": sha, "pages": len(prof["pages"]), "consultant": consultant, "producer": prof["producer"], "units": "UNKNOWN"}
  F.write_truth_files(truth, {"document.yaml": doc, **{fname: [] for fname in F.FILES[1:]}})
  loaded = CIO.load_case(folder)
  found, problems = CIO.find_files(loaded, files_dir)
  
  if problems:
    raise Refused("; ".join(problems))
  read = AD.items_of(AD.read_case(loaded, found)[name])
  today = datetime.date.today().isoformat()
  rows = PR.draft_rows(prof, {n: i.register for n, i in read.pages.items()}, today)
  PR.write_register(truth, rows)
  items = [plain(i) for i in read.items]
  kinds: dict = {}
  for p in prof["pages"]:
    kinds[p["text_type"]] = kinds.get(p["text_type"], 0) + 1
  per_page: dict = {}
  by_class: dict = {}
  by_status: dict = {}
  
  for i in items:
    per_page[i["sheet"]] = per_page.get(i["sheet"], 0) + 1
    by_class[i["cls"]] = by_class.get(i["cls"], 0) + 1
    by_status[i["status"]] = by_status.get(i["status"], 0) + 1
  first = {"pdf_key": key, "alias": doc["alias"], "case": case, "pdf": name, "sha256": sha, "consultant": consultant, "taken": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "profile": {"producer": prof["producer"], "pages": len(prof["pages"]), "text_types": kinds, "damaged_font_pages": [p["sheet"] for p in prof["pages"] if PR.damaged_fonts(p)]},
    "register_rows": len(rows), "items": {"count": len(items), "by_class": dict(sorted(by_class.items())), "by_status": dict(sorted(by_status.items())), "digest": digest_of(items)},
    "unmapped": dict(read.unmapped), "read": items}
  try:
    with open(os.path.join(truth, FIRST_SIGHT), "x", encoding="utf-8", newline="\n") as fh:
      json.dump(first, fh, indent=1, sort_keys=True)
  except FileExistsError:
    raise Refused(f"{FIRST_SIGHT} already exists in {truth}; it is never overwritten.")
  if declared:
    facts = CP.load_facts()
    facts[doc["alias"]] = {k: v for k, v in declared.items() if v}
    CP.save_facts(facts)
  CP.write(cases_dir, root)
  return {"truth": truth, "key": key, "alias": doc["alias"], "first": first, "eye": _eye_pages(prof, read, per_page), "sample": _sample(items, key)}

def cmd_intake(args) -> int:
  try:
    res = intake(args.pdf, args.case, args.consultant, args.cases_dir, args.root, args.alias, args.note, {"plot_size": args.plot_size, "storeys": args.storeys, "city": args.city, "companions": args.companions})
  except Refused as e:
    print(f"REFUSED  {e}")
    return 2
  f = res["first"]
  
  print(f"taken in: {res['alias']} (key {res['key']}), {f['profile']['pages']} pages, held out")
  print(f"  folder {res['truth']}")
  print(f"  register drafted: {f['register_rows']} rows, truth.by draft")
  print(f"  first sight stored: {FIRST_SIGHT} ({f['items']['count']} items, digest {f['items']['digest'][:16]}); it is never overwritten")
  print("  by class: " + ", ".join(f"{k} {v}" for k, v in f["items"]["by_class"].items()))
  print("\nPages for the eye check (sheet, text type, items read, why):")
  for sheet, tt, n, why in res["eye"]:
    print(f"  {sheet:>3}  {tt:9} {n:>4}  {'; '.join(why) if why else '-'}")
  print(f"\n{int(SAMPLE_SHARE * 100)}% sample of the items, for you to check on the drawing ({len(res['sample'])} of {f['items']['count']}):")
  for i in res["sample"]:
    print(f"  sheet {i['sheet']:>3}  {i['cls']:<22} {str(i['mark'] or '-'):<12} {i['status']}" + (f"  {','.join(i['reasons'])}" if i["reasons"] else ""))
  print("\nNext: write its truth in an inventory pack, then `proof.reading score --split heldout`. Do not tune the reader on this set before that score is recorded.")
  return 0

def _unmatched_reads(key: str, ts: F.TruthSet, read: AD.SetRead) -> list:
  from app.modules.drawings_boq.takeoff.proof.reading import match as M
  from app.modules.drawings_boq.takeoff.proof.reading import score as SCR
  outcomes = SCR.element_outcomes(key, ts, read, {})
  open_ids = {o["id"] for o in outcomes if o["side"] == "read" and o["outcome"] != SCR.TRUE}
  with_truth = {(r.sheet, r.cls.value) for r in ts.elements}
  scopes: dict = {}
  for item in read.items:
    scopes.setdefault((item.sheet, item.cls.value), []).append(item)
  picked = []
  for (sheet, cls), items in sorted(scopes.items()):
    for n, item in enumerate(items, 1):
      if (sheet, cls) not in with_truth or f"{key}:RD:{sheet}:{cls}:{M.group_key(item.mark) or '-'}:{n}" in open_ids:
        picked.append(item)
  return picked

def _draft_row(item, today: str) -> dict:
  row = {"sheet": item.sheet, "class": item.cls.value}
  if item.mark is not None:
    row["mark"] = str(item.mark)
  geom = plain(item.geom) if item.geom else None
  if geom:
    row["geom"] = geom
    if "point" in geom:
      row["at"] = {"page_xy": geom["point"]}
  attrs = plain(item.attrs) if item.attrs else None
  if attrs:
    row["attrs"] = attrs
  row["truth"] = {"by": V.TruthSource.DRAFT.value, "checked": False, "source": F.DRAFT_SOURCE, "date": today,
    "note": f"Trace's own read (status {item.status.value}), taken as a draft; not yet checked against the drawing"}
  return row

def redraft(ref_name: str, cases_dir: str | None, root: str, write: bool) -> dict:
  refs = [r for r in S.find_sets(cases_dir, root) if not r.link and (r.pdf_key.startswith(ref_name) or r.pdf_key == ref_name)]
  if not refs:
    for r in S.find_sets(cases_dir, root):
      if not r.link and F.load_set(r.truth_folder).document.alias == ref_name:
        refs.append(r)
  if len(refs) != 1:
    raise Refused(f"{ref_name} names {len(refs)} sets; give the PDF key or the alias of one set.")
  ref = refs[0]
  
  files_dir = CIO.cases_dir(cases_dir)
  ts = F.load_set(ref.truth_folder)
  case = CIO.load_case(os.path.join(root, ref.case))
  found, problems = CIO.find_files(case, files_dir)
  if problems:
    raise Refused("; ".join(problems))
  read = AD.items_of(AD.read_case(case, found)[ref.pdf])
  today = datetime.date.today().isoformat()
  items = _unmatched_reads(ref.pdf_key, ts, read)
  rows = [_draft_row(i, today) for i in sorted(items, key=lambda i: (i.sheet, i.cls.value, str(i.mark or "")))]
  
  by_class: dict = {}
  for r in rows:
    by_class[r["class"]] = by_class.get(r["class"], 0) + 1
  if write and rows:
    path = os.path.join(ref.truth_folder, "elements.yaml")
    with open(path, encoding="utf-8") as fh:
      old = fh.read().replace("\r\n", "\n").rstrip("\n")
    new = yaml.dump(rows, Dumper=F._NoAlias, sort_keys=False, allow_unicode=True, width=200, default_flow_style=False)
    text = new if old in ("", "[]") else old + "\n" + new
    logpath = os.path.join(ref.truth_folder, "truth_log.yaml")
    with open(logpath, encoding="utf-8") as fh:
      log = fh.read().replace("\r\n", "\n").rstrip("\n")
    entry = yaml.dump([{"date": today, "by": "draft", "pack": "RP-2", "note": f"redraft: {len(rows)} element row(s) added from Trace's own read, every one truth.by DRAFT and source draft; they do not score until checked. Classes: " + ", ".join(f"{k} {v}" for k, v in sorted(by_class.items())) + ". Existing rows were not changed."}], Dumper=F._NoAlias, sort_keys=False, allow_unicode=True, width=200, default_flow_style=False)
    F.write_truth_files(ref.truth_folder, {"elements.yaml": text, "truth_log.yaml": entry if log in ("", "[]") else log + "\n" + entry})
  return {"alias": ts.document.alias, "key": ref.pdf_key, "rows": rows, "by_class": by_class, "existing": len(ts.elements), "sample": _sample(rows, ref.pdf_key), "written": bool(write and rows)}

def cmd_redraft(args) -> int:
  try:
    res = redraft(args.set, args.cases_dir, args.root, args.write)
  except Refused as e:
    print(f"REFUSED  {e}")
    return 2
  
  print(f"{res['alias']} (key {res['key']}): {res['existing']} truth row(s) kept, {len(res['rows'])} draft row(s) " + ("written" if res["written"] else "not written (add --write)"))
  print("  by class: " + ", ".join(f"{k} {v}" for k, v in sorted(res["by_class"].items())))
  print(f"\n{int(SAMPLE_SHARE * 100)}% sample to check on the drawing, by page ({len(res['sample'])} of {len(res['rows'])}):")
  for r in sorted(res["sample"], key=lambda r: (r["sheet"], r["class"], str(r.get("mark") or ""))):
    print(f"  sheet {r['sheet']:>3}  {r['class']:<22} {str(r.get('mark') or '-'):<18} at {(r.get('at') or {}).get('page_xy') or '-'}  {r['truth']['note'].split('(')[1].split(')')[0]}")
  print("\nChecked rows: set truth.by REHAN, truth.checked true, truth.source checked. Draft rows do not score.")
  return 0

def cmd_first_sight_check(args) -> int:
  refs = [r for r in S.find_sets(args.cases_dir, args.root) if not r.link]
  files_dir = CIO.cases_dir(args.cases_dir)
  checked, moved = 0, 0
  cache: dict = {}
  
  for ref in refs:
    path = os.path.join(ref.truth_folder, FIRST_SIGHT)
    if not os.path.isfile(path):
      continue
    with open(path, encoding="utf-8") as fh:
      first = json.load(fh)
    case = CIO.load_case(os.path.join(args.root, ref.case))
    found, problems = CIO.find_files(case, files_dir)
    
    if problems:
      print("; ".join(problems))
      return 1
    if ref.case not in cache:
      cache[ref.case] = AD.read_case(case, found)
    now = digest_of([plain(i) for i in AD.items_of(cache[ref.case][ref.pdf]).items])
    same = now == first["items"]["digest"]
    checked += 1
    moved += 0 if same else 1
    print(f"{first['alias']:12} {'the engine reads it as at first sight' if same else 'THE ENGINE HAS MOVED since first sight: the held-out score is no longer the first-sight score'}  ({first['items']['digest'][:12]} -> {now[:12]})")
  print(f"{checked} set(s) checked, {moved} moved")
  
  return 0

def cmd_corpus(args) -> int:
  score_json = args.score_json or os.path.join("reading_out", "reading_score.json")
  print(CP.write(args.cases_dir, args.root, score_json))
  return 0
