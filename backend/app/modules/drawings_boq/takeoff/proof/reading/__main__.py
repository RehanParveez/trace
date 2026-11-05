from __future__ import annotations
import argparse
import json
import os
import sys
import yaml
from app.modules.drawings_boq.takeoff.proof.reading import adapter as AD
from app.modules.drawings_boq.takeoff.proof.reading import formats as F
from app.modules.drawings_boq.takeoff.proof.reading import intake as IN
from app.modules.drawings_boq.takeoff.proof.reading import profile as PR
from app.modules.drawings_boq.takeoff.proof.reading import report as RP
from app.modules.drawings_boq.takeoff.proof.reading import score as SCR
from app.modules.drawings_boq.takeoff.proof.reading import sets as S
from app.modules.drawings_boq.takeoff.proof import case as CASE
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.proof.reading import vocab as V

def _pdf_facts(path: str) -> tuple:
  import pypdfium2 as pdfium
  doc = pdfium.PdfDocument(path)
  try:
    meta = doc.get_metadata_dict()
    return len(doc), (meta.get("Producer") or meta.get("Creator") or None)
  finally:
    doc.close()

def _counts(ts: F.TruthSet) -> dict:
  return {"register": len(ts.register), "elements": len(ts.elements), "joins": len(ts.joins), "params": len(ts.params)}

def cmd_list(args) -> int:
  refs = S.find_sets(args.cases_dir, args.root)
  rows, pages, by_split = [], 0, {}
  for ref in refs:
    if ref.link:
      rows.append((ref.case, ref.pdf_key, "link to " + ref.owner, "-", "-", "-", "-", "-"))
      continue
    try:
      ts = F.load_set(ref.truth_folder)
    except F.TruthFormatError as exc:
      rows.append((ref.case, ref.pdf_key, "INVALID", "-", "-", "-", "-", "-"))
      print(exc, file=sys.stderr)
      continue
  
    c = _counts(ts)
    rows.append((ts.document.alias, ref.pdf_key, ts.document.split.value.lower(), ts.document.pages, c["register"], c["elements"], c["joins"], c["params"]))
    pages += ts.document.pages
    by_split.setdefault(ts.document.split.value.lower(), [0, 0])
    by_split[ts.document.split.value.lower()][0] += 1
    by_split[ts.document.split.value.lower()][1] += ts.document.pages
    
  head = ("alias", "key", "split", "pages", "register", "elements", "joins", "params")
  widths = [max(len(str(r[i])) for r in [head, *rows]) for i in range(len(head))]
  for r in [head, *rows]:
    print("  ".join(str(v).ljust(widths[i]) for i, v in enumerate(r)))
  own = [r for r in refs if not r.link]
  print(f"\n{len(own)} PDFs, {pages} pages (" + ", ".join(f"{k} {v[0]} PDFs {v[1]} pages" for k, v in sorted(by_split.items())) + ")")
  return 0

def cmd_validate(args) -> int:
  refs = S.find_sets(args.cases_dir, args.root)
  problems, seen = [], set()
  for ref in refs:
    where = f"{ref.case}/{ref.pdf}"
    if ref.link:
      owner_folder = os.path.join(args.root, ref.owner, S.READING, ref.pdf_key)
      lp = S.link_path(ref, args.root)
      if not os.path.isfile(lp):
        problems.append(f"{where}: the PDF is also in case {ref.owner}; {lp} must say so.")
      elif not os.path.isdir(owner_folder):
        problems.append(f"{where}: {owner_folder} does not exist.")
      continue
  
    seen.add(os.path.normpath(ref.truth_folder))
    if not os.path.isdir(ref.truth_folder):
      problems.append(f"{where}: no truth folder {ref.truth_folder}.")
      continue
    try:
      ts = F.load_set(ref.truth_folder)
    except F.TruthFormatError as exc:
      problems.extend(f"{where}: {p['file']}, {p['row']}, {p['field']}: {p['message']}" for p in exc.problems)
      continue
  
    raw = S._raw_case(os.path.join(args.root, ref.case))
    want = (raw.get("sha256") or {}).get(ref.pdf)
    if want and ts.document.sha256 != want:
      problems.append(f"{where}: document.yaml sha256 differs from case.yaml.")
    if ts.document.case != ref.case:
      problems.append(f"{where}: document.yaml names case {ts.document.case!r}, the folder is in {ref.case!r}.")
    if ref.pdf_path:
      if CASE.sha256_of(ref.pdf_path) != ts.document.sha256:
        problems.append(f"{where}: the PDF in the PDF folder has a different hash.")
      else:
        pages, _ = _pdf_facts(ref.pdf_path)
        if pages != ts.document.pages:
          problems.append(f"{where}: document.yaml says {ts.document.pages} pages, the PDF has {pages}.")
          
  for case in CIO.list_cases(args.root):
    base = os.path.join(args.root, case, S.READING)
    if os.path.isdir(base):
      for name in sorted(os.listdir(base)):
        full = os.path.normpath(os.path.join(base, name))
        if os.path.isdir(full) and full not in seen:
          problems.append(f"{case}/{S.READING}/{name}: no PDF of any case has this key.")
          
  for p in problems:
    print(p)
  print(f"{len(problems)} problem(s)")
  return 1 if problems else 0

def cmd_init(args) -> int:
  refs = [r for r in S.find_sets(args.cases_dir, args.root) if not r.link and not os.path.isdir(r.truth_folder)]
  if not refs:
    print("every PDF already has a truth folder")
    return 0

  for ref in refs:
    if not ref.pdf_path:
      print(f"{ref.case}/{ref.pdf}: the PDF is not in the PDF folder; give --cases-dir.")
      return 1
  
    pages, producer = _pdf_facts(ref.pdf_path)
    sha = CASE.sha256_of(ref.pdf_path)
    siblings = [r for r in S.find_sets(args.cases_dir, args.root) if r.case == ref.case]
    alias = ref.case if len(siblings) == 1 else f"{ref.case}-{siblings.index(ref) + 1}"
    os.makedirs(ref.truth_folder)
    doc = {"alias": alias, "split": V.Split.HELDOUT.value.lower(), "case": ref.case, "sha256": sha, "pages": pages, "consultant": None, "producer": producer, "units": "UNKNOWN"}
    F.write_truth_files(ref.truth_folder, {"document.yaml": doc, **{name: [] for name in F.FILES[1:]}})
    print(f"made {ref.truth_folder} ({alias}, {pages} pages, heldout)")
  return 0

def cmd_score(args) -> int:
  import time
  t0 = time.monotonic()
  doc = SCR.run(args.split, args.cases_dir, args.score_dir, args.root)
  base = SCR.load_baseline()
  cmp = SCR.compare(base, doc, SCR.load_accepted()) if base else None
  os.makedirs(args.out, exist_ok=True)
  with open(os.path.join(args.out, "reading_score.json"), "w", encoding="utf-8", newline="\n") as fh:
    json.dump(doc, fh, indent=1, sort_keys=True)
  with open(os.path.join(args.out, "reading_score.md"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write(RP.render(doc, cmp))
  t = doc["metrics"]["by_split"]
  print(f"reading score {args.split}: {len(doc['sets'])} PDF(s), {len(doc['outcomes'])} outcomes; hash {doc['hash'][:16]}; {time.monotonic() - t0:.1f} s")
  for sp, row in t.items():
    print(f"  {sp}: truth {row['truth']}, matched {row['matched']}, silent-wrong {row['silent_wrong']}")
    if row["truth"]:
      print(f"      recall {row['recall']:.1%}, Wilson 95% interval {row['recall_ci'][0]:.1%} to {row['recall_ci'][1]:.1%}")
  if args.write_baseline:
    with open(SCR.BASELINE, "w", encoding="utf-8", newline="\n") as fh:
      json.dump(SCR.to_baseline(doc), fh, indent=1, sort_keys=True)
      fh.write("\n")
    print(f"baseline written: {SCR.BASELINE}")
  return 0

def _structure_first(case: dict, rows_by_pdf: dict) -> list:
  """The PDFs of a case, the one with most structural sheets first."""
  def structural(name: str) -> int:
    return sum(1 for r in rows_by_pdf[name] if ((r.get("meta") or {}).get("identity") or {}).get("discipline") == "STRUCTURAL")
  return sorted(case["pdfs"], key=lambda n: -structural(n))

def cmd_set_join(args) -> int:
  from app.modules.drawings_boq.takeoff.extract import set_join as SJN
  files_dir = CIO.cases_dir(args.cases_dir)
  docs = []
  
  for name in CIO.list_cases(args.root):
    case = CIO.load_case(os.path.join(args.root, name))
    if len(case["pdfs"]) < 2:
      continue
    found, problems = CIO.find_files(case, files_dir)
    if problems:
      raise RuntimeError("; ".join(problems))
    rows = AD.read_case(case, found)
    order = _structure_first(case, rows)
    if not any(((r.get("meta") or {}).get("identity") or {}).get("discipline") == "STRUCTURAL" for r in rows[order[0]]):
      continue
    doc = SJN.join_sets(order[0], rows[order[0]], order[1], rows[order[1]])
    doc["case"] = name
    refs = [r for r in S.find_sets(args.cases_dir, args.root) if r.case == name and r.pdf == order[0] and not r.link]
    if refs:
      doc["ledger"] = SCR.ledger_after_join(F.load_set(refs[0].truth_folder), doc)
      
    docs.append(doc)
  os.makedirs(args.out, exist_ok=True)
  with open(os.path.join(args.out, "set_join.json"), "w", encoding="utf-8", newline="\n") as fh:
    json.dump(docs, fh, indent=1, sort_keys=True, default=str)
  with open(os.path.join(args.out, "set_join.md"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write(RP.render_set_join(docs))
  for d in docs:
    al = d.get("alignment") or {}
    print(f"{d['case']}: paired {d['pair']['paired']} ({d['pair']['why']}); alignment {al.get('basis')} {al.get('status')} residual {al.get('residual_in')} in; slab conflict {(d.get('slab') or {}).get('conflict')}")
  return 0

def cmd_diff(args) -> int:
  path = os.path.join(args.out, "reading_score.json")
  if not os.path.isfile(path):
    print(f"{path} is missing; run score first")
    return 2
  with open(path, encoding="utf-8") as fh:
    doc = json.load(fh)
  base = SCR.load_baseline()
  if base is None:
    print("no baseline")
    return 2

  cmp = SCR.compare(base, doc, SCR.load_accepted())
  print(f"truth {'unchanged' if cmp['same_truth'] else 'changed'}; {len(cmp['changed'])} outcome(s) changed; {len(cmp['lost'])} lost; silent rises {cmp['silent_rises'] or 'none'}")
  for i, a, b in cmp["changed"]:
    print(f"  {i}: {a} to {b}")
  return 0 if cmp["ok"] else 1

def cmd_parity(args) -> int:
  from app.modules.drawings_boq.takeoff.proof import score as SC
  rows, bad = [], 0
  for name in ("plot1", "191c"):
    case = CIO.load_case(os.path.join(args.root, name))
    found, problems = CIO.find_files(case, CIO.cases_dir(args.cases_dir))
    if problems:
      print("; ".join(problems))
      return 2
    reads = AD.read_case(case, found)
    results = SC.check_facts([r for rs in reads.values() for r in rs], case["facts"])
    
    old = {}
    for r in results:
      old[r["status"]] = old.get(r["status"], 0) + 1
    new = {SCR.OK: 0, SCR.WRONG: 0, SCR.MISSED_S: 0, "UNJUDGED": 0}
    for r in results:
      new[SCR.FACT_OUTCOME.get(r["status"], "UNJUDGED")] += 1
      
    tally = {}
    if args.score_dir and os.path.isfile(os.path.join(args.score_dir, name, "score.json")):
      with open(os.path.join(args.score_dir, name, "score.json"), encoding="utf-8") as fh:
        tally = json.load(fh).get("facts_tally") or {}
    same = old.get("PASS", 0) == new[SCR.OK] and old.get("FAIL", 0) == new[SCR.WRONG] and old.get("MISSING", 0) == new[SCR.MISSED_S] and (not tally or tally.get("PASS", 0) == new[SCR.OK])
    bad += 0 if same else 1
    rows.append((name, len(results), tally or old, new, "equal" if same else "DIFFERENT"))
    
  print(f"{'case':6} {'facts':>5}  score.py (PASS / FAIL / MISSING / other)           reading scorer (OK / WRONG / MISSED_SILENT / unjudged)")
  for name, n, old, new, verdict in rows:
    other = sum(v for k, v in old.items() if k not in ("PASS", "FAIL", "MISSING"))
    print(f"{name:6} {n:>5}  {old.get('PASS', 0)} / {old.get('FAIL', 0)} / {old.get('MISSING', 0)} / {other}".ljust(62) + f"{new[SCR.OK]} / {new[SCR.WRONG]} / {new[SCR.MISSED_S]} / {new['UNJUDGED']}   {verdict}")
  return 1 if bad else 0

def cmd_profile(args) -> int:
  import datetime
  refs = [r for r in S.find_sets(args.cases_dir, args.root) if not r.link]
  done = 0
  for ref in refs:
    ts = F.load_set(ref.truth_folder)
    if args.alias and ts.document.alias != args.alias:
      continue
    if not ref.pdf_path:
      print(f"{ts.document.alias}: the PDF is not in the PDF folder; give --cases-dir.")
      return 1
  
    prof = PR.profile_pdf(ref.pdf_path)
    kinds: dict = {}
    for p in prof["pages"]:
      kinds[p["text_type"]] = kinds.get(p["text_type"], 0) + 1
    damaged = sum(1 for p in prof["pages"] if PR.damaged_fonts(p))
    print(f"{ts.document.alias}: {len(prof['pages'])} pages, text types " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())) + f", {damaged} page(s) with a damaged font, producer {prof['producer']}")
    if args.out:
      os.makedirs(args.out, exist_ok=True)
      with open(os.path.join(args.out, ts.document.alias + ".profile.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(prof, fh, indent=1, sort_keys=True)
        
    if args.draft_register:
      if ts.register and not args.force:
        print(f"  register.yaml already has {len(ts.register)} row(s); use --force to replace it with a draft")
        continue
      case = CIO.load_case(os.path.join(args.root, ref.case))
      found, problems = CIO.find_files(case, CIO.cases_dir(args.cases_dir))
      if problems:
        print("; ".join(problems))
        return 1
    
      read = AD.items_of(AD.read_case(case, found)[ref.pdf])
      rows = PR.draft_rows(prof, {n: i.register for n, i in read.pages.items()}, datetime.date.today().isoformat())
      PR.write_register(ref.truth_folder, rows)
      print(f"  drafted {len(rows)} register row(s), truth.by draft")
    done += 1
  return 0 if done else 1

def cmd_gate(args) -> int:
  try:
    ok, note = SCR.gate(args.cases_dir, args.score_dir, args.root)
  except (RuntimeError, ValueError) as exc:
    ok, note = False, str(exc)
  print(f"{'ok  ' if ok else 'FAIL'}  reading no regression (gate 14)   {note}")
  return 0 if ok else 1

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(prog="proof.reading", description="The reading benchmark: truth folders for every PDF.")
  ap.add_argument("--cases-dir", help=f"the folder with the PDFs (default: {CIO.CASES_DIR_ENV})")
  ap.add_argument("--root", default=CIO.HERE, help="the folder of case folders")
  sub = ap.add_subparsers(dest="command", required=True)
  sj = sub.add_parser("set-join", help="join the structure set of each two-PDF case to its architecture set; writes set_join.md and .json")
  sj.add_argument("--out", default="reading_out")
  sub.add_parser("list", help="every PDF with its split, pages and truth counts")
  sub.add_parser("validate", help="check every truth folder; exit 1 on any problem")
  sub.add_parser("init", help="make the truth folder of a PDF that has none (held out)")
  sp = sub.add_parser("score", help="read the PDFs that have truth and score them; writes reading_score.md and .json")
  sp.add_argument("--split", choices=("dev", "heldout", "all"), default="all")
  sp.add_argument("--out", default="reading_out")
  sp.add_argument("--score-dir", help="a folder with <case>/score.json from proof.score, to take the fact results from instead of reading the case again")
  sp.add_argument("--write-baseline", action="store_true")
  dp = sub.add_parser("diff", help="the outcomes that changed since the baseline")
  dp.add_argument("--out", default="reading_out")
  pf = sub.add_parser("profile", help="measure every page of a PDF (words, paths, images, fonts, decode gain, text type); --draft-register fills register.yaml from Trace's own identity")
  pf.add_argument("--alias")
  pf.add_argument("--out", help="a folder for <alias>.profile.json")
  pf.add_argument("--draft-register", action="store_true")
  pf.add_argument("--force", action="store_true")
  gp = sub.add_parser("gate", help="gate 14 on its own: no truth item lost since the baseline, silent-wrong not up")
  gp.add_argument("--score-dir")
  pp = sub.add_parser("parity", help="the facts of Plot_1 and 191-C through score.py and through the reading scorer, side by side")
  pp.add_argument("--score-dir")
  ip = sub.add_parser("intake", help="take in a new PDF as held out: key, truth folder, profile, draft register, first sight (never overwritten), pages for the eye check, 10% sample")
  ip.add_argument("pdf")
  ip.add_argument("--case", required=True)
  ip.add_argument("--consultant", required=True)
  ip.add_argument("--alias")
  ip.add_argument("--note")
  ip.add_argument("--plot-size")
  ip.add_argument("--storeys")
  ip.add_argument("--city")
  ip.add_argument("--companions")
  rd = sub.add_parser("redraft", help="add a draft row (truth.by DRAFT, source draft, never scored) for every item Trace read that no truth row covers; prints the 10% sample to check")
  rd.add_argument("set", help="the PDF key (or its first characters) or the alias of one set")
  rd.add_argument("--write", action="store_true", help="write the rows; without it nothing changes")
  sub.add_parser("first-sight-check", help="read each held-out set again and say whether the engine still reads it as at first sight")
  cp = sub.add_parser("corpus", help="write proof/reading/corpus.md: one row per set and the variety gaps")
  cp.add_argument("--score-json", help="reading_score.json from a score run, for the first-sight scores (default reading_out/reading_score.json)")
  args = ap.parse_args(argv)
  return {"list": cmd_list, "validate": cmd_validate, "init": cmd_init, "score": cmd_score, "diff": cmd_diff, "parity": cmd_parity, "set-join": cmd_set_join, "gate": cmd_gate, "profile": cmd_profile,
    "intake": IN.cmd_intake, "redraft": IN.cmd_redraft, "first-sight-check": IN.cmd_first_sight_check, "corpus": IN.cmd_corpus}[args.command](args)

if __name__ == "__main__":
  sys.exit(main())
