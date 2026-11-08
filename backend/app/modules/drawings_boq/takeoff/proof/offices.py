from __future__ import annotations
import argparse
import asyncio
import datetime
import os
import sys
import yaml
from app.modules.drawings_boq.takeoff.ai_reader import cache as CACHE
from app.modules.drawings_boq.takeoff.proof.bench import offices as OFF
from app.modules.drawings_boq.takeoff.proof import case_io as CIO

from app.modules.drawings_boq.takeoff.ai_reader import tasks as TASKS

KNOWN, NEW, CONFLICT, NONE = "KNOWN", "NEW", "CONFLICT", "NONE"
BLOCK = "intake"

def pages_of(spec, total: int) -> list:
  out: list = []
  for part in str(spec).split(","):
    a, _, b = part.strip().partition("-")
    out.extend(range(int(a), int(b or a) + 1))
  return [p for p in dict.fromkeys(out) if 1 <= p <= total]

def cached_firms(folder: str, sha: str) -> list:
  out = []
  for e in CACHE.read_all(folder):
    answer = e.get("answer") or {}
    if e.get("task") == TASKS.get("SHEET").name and e.get("pdf_sha256") == sha and answer.get("firm"):
      out.append({"firm": str(answer["firm"]), "quote": (answer.get("quotes") or {}).get("firm"), "page": e.get("page"), "source": "SHEET_ANSWER"})
  return out

def printed_firms(doc: dict, contents: bytes) -> list:
  from app.modules.drawings_boq.takeoff.prep.extract import open_document
  pdf = open_document(contents)
  out = []
  try:
    for no in pages_of(f"1-{int(doc['settings']['scan_pages'])}", len(pdf)):
      body = OFF.norm(pdf[no - 1].get_textpage().get_text_range())
      for letter, row in sorted(doc["offices"].items()):
        out += [{"firm": firm, "quote": None, "page": no, "source": "TEXT_LAYER"} for firm in row.get("firms") or [] if OFF.norm(firm) and OFF.norm(firm) in body]
  finally:
    pdf.close()
  return out

def propose(doc: dict, folder: str, files: dict, consultant: str | None) -> dict:
  found = []
  for _name, path in sorted(files.items()):
    with open(path, "rb") as fh:
      contents = fh.read()
    found += cached_firms(folder, CACHE.pdf_sha256(contents)) + printed_firms(doc, contents)
  if consultant:
    found.append({"firm": consultant, "quote": None, "page": None, "source": "TYPED"})
  by: dict = {}
  
  for f in found:
    by.setdefault(OFF.norm(f["firm"]), []).append(f)
  ranked = sorted(by.values(), key=lambda fs: (-len(fs), OFF.norm(fs[0]["firm"])))
  letters = {OFF.norm(fs[0]["firm"]): OFF.office_for_firm(doc, fs[0]["firm"]) for fs in ranked}
  evidence = [{"firm": fs[0]["firm"], "times": len(fs), "office": letters[OFF.norm(fs[0]["firm"])], "sources": sorted({f["source"] for f in fs}), "pages": sorted({f["page"] for f in fs if f["page"]}),
    "quote": next((f["quote"] for f in fs if f["quote"]), None)} for fs in ranked]
  leaders = [fs for fs in ranked if len(fs) == len(ranked[0])] if ranked else []
  offices = sorted({letters[OFF.norm(fs[0]["firm"])] for fs in leaders} - {None})
  if len(offices) > 1:
    return {"status": CONFLICT, "office": None, "firm": None, "evidence": evidence, "offices": offices}
  if offices:
    firm = next(fs[0]["firm"] for fs in leaders if letters[OFF.norm(fs[0]["firm"])] == offices[0])
    return {"status": KNOWN, "office": offices[0], "firm": firm, "evidence": evidence, "offices": offices}
  if ranked:
    return {"status": NEW, "office": OFF.next_letter(doc), "firm": ranked[0][0]["firm"], "evidence": evidence, "offices": []}
  return {"status": NONE, "office": None, "firm": None, "evidence": [], "offices": []}

def describe(p: dict) -> list:
  out = [f"  firm texts found: {len(p['evidence'])}"] + [f"    {e['firm']!r} x{e['times']}" + (f", recorded under office {e['office']}" if e["office"] else ", not recorded") + f" ({', '.join(e['sources'])}" + (f", pages {','.join(map(str, e['pages']))}" if e["pages"] else "") + ")" + (f" quote: {e['quote']!r}" if e["quote"] else "") for e in p["evidence"]]
  if p["status"] == KNOWN:
    out.append(f"  proposed: office {p['office']}, the firm {p['firm']!r} is recorded under it")
  elif p["status"] == NEW:
    out.append(f"  proposed: a NEW office, letter {p['office']}, for the firm {p['firm']!r}; confirm with --new --firm to record it")
  elif p["status"] == CONFLICT:
    out.append(f"  the firm texts point to offices {', '.join(p['offices'])}; decide which one it is")
  else:
    out.append("  no firm text found (no cached SHEET answer, no known firm printed, none typed); give --office and --firm by hand, or run propose with --ask")
  return out

def checklist(register: list, declared: dict | None, boq: str | None, pages: int) -> dict:
  declared = declared or {}
  roles: dict = {}
  for r in register:
    if r.get("role"):
      roles[r["role"]] = roles.get(r["role"], 0) + 1
  return {"city": declared.get("city") or None, "building_type": declared.get("building_type") or None,
    "disciplines": sorted({r["discipline"] for r in register if r.get("discipline")}), "sheet_roles": dict(sorted(roles.items())), "pages": pages,
    "qs_boq": {"present": bool(boq), "path": boq or None}, "taken": datetime.date.today().isoformat()}

def write_checklist(folder: str, data: dict) -> None:
  path = os.path.join(folder, "case.yaml")
  with open(path, encoding="utf-8", newline="") as fh:
    text = fh.read()
  nl = "\r\n" if "\r\n" in text else "\n"
  lines = text.split(nl)
  start = next((n for n, ln in enumerate(lines) if ln.startswith(f"{BLOCK}:")), None)
  
  if start is not None:
    end = start + 1
    while end < len(lines) and (lines[end].startswith(" ") or not lines[end].strip()):
      end += 1
    lines = lines[:start] + lines[end:]
  while lines and not lines[-1].strip():
    lines.pop()
  block = yaml.safe_dump({BLOCK: data}, sort_keys=False, allow_unicode=True, width=200).rstrip("\n").split("\n")
  with open(path, "w", encoding="utf-8", newline="") as fh:
    fh.write(nl.join(lines + block) + nl)

def case_folder(name: str, root: str = CIO.HERE) -> str:
  folder = os.path.join(root, name)
  if not os.path.isfile(os.path.join(folder, "case.yaml")):
    raise ValueError(f"There is no case {name}.")
  return folder

def confirm(name: str, office: str, by: str, today: str, firm: str | None = None, new: bool = False, city: str | None = None, building_type: str | None = None, root: str = CIO.HERE) -> dict:
  folder = case_folder(name, root)
  doc, sets_doc = OFF.load(), OFF.read_sets()
  if name in (sets_doc.get("sets") or {}):
    raise ValueError(f"{name} is already in sets.yaml with office {sets_doc['sets'][name].get('office')}.")
  if office not in doc["offices"]:
    if not new:
      raise ValueError(f"Office {office} is not recorded; add --new to record it.")
    if office != OFF.next_letter(doc):
      raise ValueError(f"A new office takes the next letter, {OFF.next_letter(doc)}, not {office}.")
    if not firm:
      raise ValueError("A new office needs the firm text (--firm).")
    doc["offices"][office] = {"firms": [], "city": city, "confirmed_by": by, "date": today}
  row = doc["offices"][office]
  if firm and OFF.norm(firm) not in {OFF.norm(f) for f in row["firms"]}:
    owner = OFF.office_for_firm(doc, firm)
    if owner and owner != office:
      raise ValueError(f"The firm {firm!r} is already recorded under office {owner}.")
    row["firms"].append(firm)
  if city and not row.get("city"):
    row["city"] = city
    
  groups = list((sets_doc.get("section_groups") or {}).keys())
  OFF.write_set_row(name, {"office": office, "split": {g: OFF.FIRST_SIGHT for g in groups}})
  doc["set_log"][name] = [{"group": g, "split": OFF.FIRST_SIGHT, "date": today, "by": by} for g in groups]
  OFF.save(doc)
  with open(os.path.join(folder, "case.yaml"), encoding="utf-8") as fh:
    intake = (yaml.safe_load(fh) or {}).get(BLOCK) or {}
  intake.update({"office": office, "office_confirmed_by": by, "office_confirmed_date": today})
  if city:
    intake["city"] = city
  if building_type:
    intake["building_type"] = building_type
  write_checklist(folder, intake)
  return {"office": office, "groups": groups, "new_office": new}

def promote(name: str, group: str, to: str, by: str, today: str) -> dict:
  to = to.upper()
  if to not in OFF.LEAVES:
    raise ValueError(f"A set moves to {' or '.join(OFF.LEAVES)}, never to {to}.")
  doc, sets_doc = OFF.load(), OFF.read_sets()
  row = (sets_doc.get("sets") or {}).get(name)
  if row is None:
    raise ValueError(f"{name} is not in sets.yaml.")
  if OFF.split_label(row, group) != OFF.FIRST_SIGHT:
    raise ValueError(f"{name} is not first sight for {group} (it is {OFF.split_label(row, group) or 'decided by its office'}).")
  if OFF.first_score(name, OFF.history_rows()) is None:
    raise ValueError(f"The benchmark has not scored {name} yet: no first-sight line in history.csv. Run the benchmark first; the score comes before any truth.")
  row["split"][group] = to
  OFF.write_set_row(name, row)
  doc["set_log"].setdefault(name, []).append({"group": group, "split": to, "date": today, "by": by})
  OFF.save(doc)
  return {"set": name, "group": group, "to": to}

def report_lines(doc: dict, sets_doc: dict, history: list) -> list:
  sets = sets_doc.get("sets") or {}
  target = int(doc["settings"].get("target_offices") or 0)
  unconfirmed = [k for k, r in sorted(doc["offices"].items()) if not r.get("confirmed_by")]
  out = [f"{len(doc['offices'])} office(s) recorded of the {target} wanted; {len(unconfirmed)} not confirmed" + (f" ({', '.join(unconfirmed)})" if unconfirmed else "")]
  for letter, row in sorted(doc["offices"].items()):
    mine = sorted(n for n, s in sets.items() if s.get("office") == letter)
    out.append(f"  {letter}: {', '.join(row.get('firms') or ['no firm recorded'])}; confirmed by {row.get('confirmed_by')}; sets {', '.join(mine) or 'none'}")
  entered = sorted(n for n in doc["set_log"] if n in sets)
  scored = [n for n in entered if OFF.first_score(n, history)]
  out.append(f"{len(entered)} set(s) entered as first sight; {len(scored)} with a first-sight score in history.csv")
  for n in entered:
    f = OFF.first_score(n, history)
    now = ", ".join(f"{g} {OFF.split_label(sets[n], g)}" for g in sorted(sets[n].get("split") or {}))
    out.append(f"  {n} (office {sets[n]['office']}): " + (f"first score {f['date']}, product coverage {f['coverage_pct']}%, within 10%: {f['within_10']} of {f['compared']}" if f else "NOT SCORED YET: run the benchmark before anyone looks at its pages") + f"; now {now}")
  return out

def first_sight_line(doc: dict | None = None, sets_doc: dict | None = None, history: list | None = None) -> str:
  doc = doc or OFF.load()
  sets = (sets_doc if sets_doc is not None else OFF.read_sets()).get("sets") or {}
  history = OFF.history_rows() if history is None else history
  entered = [n for n in doc["set_log"] if n in sets]
  scored = [n for n in entered if OFF.first_score(n, history)]
  return f"First sight: {len(doc['offices'])} office(s) recorded of {doc['settings'].get('target_offices')}; {len(entered)} set(s) entered as first sight, {len(scored)} with a first score" + (f"; not scored: {', '.join(sorted(set(entered) - set(scored)))}" if len(scored) < len(entered) else "") + "."

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Office of a new set from its title block, the intake checklist, and first sight. A person confirms every office; nothing is written until then.")
  sub = ap.add_subparsers(dest="cmd", required=True)
  p = sub.add_parser("propose")
  p.add_argument("case")
  p.add_argument("--consultant", default=None, help="the firm as you read it; a proposal, not a required guess")
  p.add_argument("--cases-dir", default=None)
  p.add_argument("--ask", choices=("local", "outside"), default=None, help="run the SHEET task on the first pages to read the firm (local uses Ollama; outside uses the Anthropic API)")
  c = sub.add_parser("confirm")
  c.add_argument("case")
  c.add_argument("--office", required=True)
  c.add_argument("--by", required=True)
  c.add_argument("--firm", default=None)
  c.add_argument("--new", action="store_true")
  c.add_argument("--city", default=None)
  c.add_argument("--type", dest="building_type", default=None)
  m = sub.add_parser("promote")
  m.add_argument("case")
  m.add_argument("--group", required=True)
  m.add_argument("--to", required=True, choices=("test", "dev", "TEST", "DEV"))
  m.add_argument("--by", required=True)
  sub.add_parser("report")
  args = ap.parse_args(argv)
  today = datetime.date.today().isoformat()
  
  try:
    if args.cmd == "propose":
      folder = case_folder(args.case)
      case = CIO.load_case(folder)
      found, problems = CIO.find_files(case, CIO.cases_dir(args.cases_dir))
      if problems:
        raise ValueError("; ".join(problems))
      doc = OFF.load()
      if args.ask:
        from app.modules.ai_requests.service import CONSENT_PROVIDER, model_of
        from app.modules.drawings_boq.takeoff.ai_reader import fill_cache as FC
        provider = CONSENT_PROVIDER["LOCAL" if args.ask == "local" else "OUTSIDE"]
        for name, path in sorted(found.items()):
          stats = asyncio.run(FC.fill(pdf=path, out=folder, provider=provider, model=model_of(provider), pages=str(doc["settings"]["firm_pages"]), force=False, max_tokens=1024, timeout_s=None))
          print(f"{name}: {stats['asked']} asked, {stats['cached']} already cached, {stats['failed']} failed")
      print(f"{args.case}:")
      print("\n".join(describe(propose(doc, folder, found, args.consultant))))
      
    elif args.cmd == "confirm":
      r = confirm(args.case, args.office.upper(), args.by, today, args.firm, args.new, args.city, args.building_type)
      print(f"{args.case} is office {r['office']}" + (" (new office recorded)" if r["new_office"] else "") + f"; first sight for {', '.join(r['groups'])}.")
      print("Next: run the benchmark. It scores the set once and appends the line to history.csv before any truth is written.")
    elif args.cmd == "promote":
      r = promote(args.case, args.group, args.to, args.by, today)
      print(f"{r['set']}: {r['group']} moved from first sight to {r['to']}. It cannot go back.")
  except ValueError as exc:
    print(f"REFUSED  {exc}", file=sys.stderr)
    return 2
  if args.cmd == "report" or args.cmd in ("confirm", "promote"):
    bad = OFF.problems(groups=list((OFF.read_sets().get("section_groups") or {}).keys()))
    for ln in report_lines(OFF.load(), OFF.read_sets(), OFF.history_rows()):
      print(ln)
    for b in bad:
      print(f"PROBLEM  {b}", file=sys.stderr)
    return 1 if bad else 0
  return 0

if __name__ == "__main__":
  sys.exit(main())
