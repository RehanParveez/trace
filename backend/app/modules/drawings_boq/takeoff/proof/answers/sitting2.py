from __future__ import annotations
import argparse
import datetime
import json
import os
import re
import sys
from app.engine.catalogue import loader as CL
from app.engine.catalogue import methods_qs as MQ
from app.modules.drawings_boq.takeoff.completeness import ledger as LG
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.proof.answers import answers as AN
from app.modules.drawings_boq.takeoff.proof.bench import failures as FL
from app.modules.drawings_boq.takeoff.proof.bench import money as MN

QUESTIONS, CONFIRM, DIFFS, META, KIND = "Method questions", "Methods to confirm", "Differences", "_meta", "sitting2"
CAUSES = ("TRACE_WRONG", "METHOD", "WORKBOOK_SLIP")
NOTE_NEEDED = ("METHOD", "WORKBOOK_SLIP")
FILE = "differences.yaml"
TOP = 20
YES, NO = "yes", "no"

class SheetError(Exception):
  pass

def rows_of(bench_dir: str) -> list:
  path = os.path.join(bench_dir, "rows.jsonl")
  if not os.path.isfile(path):
    raise SheetError(f"there is no rows.jsonl in {bench_dir}; run the benchmark first")
  with open(path, encoding="utf-8") as fh:
    return [json.loads(ln) for ln in fh if ln.strip()]

def differences(rows: list, rates: dict, top: int = TOP) -> list:
  runs: dict = {}
  for r in rows:
    runs.setdefault(r["set"], set()).add(r["run"])
  out = []
  for name in sorted(runs):
    run = MN.METHOD_RUN if MN.METHOD_RUN in runs[name] else "PRODUCT"
    by: dict = {}
    for r in rows:
      if r["set"] == name and r["run"] == run:
        by.setdefault(r["element"], []).append(r)
    for element, rs in sorted(by.items()):
      for r in [x for x in rs if x["floor"] == LG.ALL] or rs:
        if r["answer_qty"] in (None, 0) or r["trace_qty"] is None or r["within_tol"]:
          continue
        entry = MN.rate_entry(element, rates)
        qty = None if entry is None else MN.to_rate_unit(abs(float(r["answer_qty"]) - float(r["trace_qty"])), r.get("unit"), entry[1])
        out.append({"set": name, "run": run, "element": element, "floor": r["floor"], "answer_qty": r["answer_qty"], "trace_qty": r["trace_qty"], "unit": r.get("unit"), "diff_pct": r["diff_pct"],
          "tol_pct": r["tol_pct"], "money_pkr": None if qty is None else round(qty * entry[0], 2)})
  out.sort(key=lambda d: (d["money_pkr"] is None, -(d["money_pkr"] or 0.0), -abs(d["diff_pct"] or 0.0), d["set"], d["element"], d["floor"]))
  return out[:top]

def key_of(d: dict) -> str:
  return f"{d['set']}/{d['element']}/{d['floor']}"

def unconfirmed_methods() -> list:
  out = []
  for p in MQ.profiles():
    for m in p["methods"]:
      src = m["source"]
      if src.get("kind") == MQ.WORKBOOK and not src.get("confirmed"):
        out.append({"id": m["id"], "profile": p["id"], "qs": p["qs"], "item": m["item"], "says": m["says"], "source": MQ.source_text(src)})
  return out

def export(out_dir: str, bench_dir: str, rates: dict, top: int = TOP) -> dict:
  from openpyxl import Workbook
  from openpyxl.styles import Alignment, Font
  from openpyxl.worksheet.datavalidation import DataValidation
  diffs = differences(rows_of(bench_dir), rates, top)
  names = {i.id: i.name for i in CL.items()}
  wb = Workbook()
  hint = wb.active
  hint.title = "Read me"
  
  for line in ("Sitting 2 with the QS: the open method questions, the workbook-derived methods he has not confirmed, and the differences that matter most.",
    "Method questions: write his answer in his own words. It is recorded under his name and the date; it does not change what Trace does until a rule is written from it.",
    "Methods to confirm: yes if that is how he measures, no if it is not. Only the QS who owns the profile can confirm; Trace's totals never do.",
    f"Differences: the {len(diffs)} rows with the most money between the workbook and Trace's number, outside the item's tolerance. Cause: TRACE_WRONG (Trace's reading or measuring is wrong), METHOD (he measures differently) or WORKBOOK_SLIP (the workbook is wrong). METHOD and WORKBOOK_SLIP need a note.",
    "Leave a row empty if he cannot tell. Then run: python -m app.modules.drawings_boq.takeoff.proof.answers.sitting2 import <this file> --by \"<his name>\" [--write]"):
    hint.append([line])
    
  hint.column_dimensions["A"].width = 150
  wrap = Alignment(wrap_text=True, vertical="top")
  q = wb.create_sheet(QUESTIONS)
  q.append(["Id", "Aspect", "Item", "Question", "Trace holds", "Standard", "Asked", "His answer"])
  for o in MQ.open_questions():
    q.append([o["id"], o["aspect"], o["item"], o["question"], o["trace"], o.get("standard"), o.get("asked"), o.get("answer")])
  c = wb.create_sheet(CONFIRM)
  c.append(["Id", "Profile", "Item", "Trace holds that the QS", "Where it was read", "Confirmed (yes / no)"])
  yn = DataValidation(type="list", formula1=f'"{YES},{NO}"', allow_blank=True)
  c.add_data_validation(yn)
  
  for m in unconfirmed_methods():
    c.append([m["id"], m["profile"], m["item"], m["says"], m["source"], None])
    yn.add(f"F{c.max_row}")
  d = wb.create_sheet(DIFFS)
  d.append(["Key", "Set", "Item", "Name", "Floor", "Workbook quantity", "Trace quantity", "Unit", "Difference %", "Tolerance %", "Money at stake (PKR)", "Cause", "Note"])
  cause = DataValidation(type="list", formula1='"' + ",".join(CAUSES) + '"', allow_blank=True)
  d.add_data_validation(cause)
  
  for x in diffs:
    d.append([key_of(x), x["set"], x["element"], names.get(x["element"], x["element"]), x["floor"], x["answer_qty"], x["trace_qty"], x["unit"], x["diff_pct"], x["tol_pct"], x["money_pkr"], None, None])
    cause.add(f"L{d.max_row}")
    
  for ws, widths in ((q, (22, 14, 8, 50, 40, 30, 10, 50)), (c, (28, 14, 8, 60, 50, 16)), (d, (26, 9, 8, 40, 12, 12, 12, 7, 11, 10, 14, 16, 40))):
    for row in ws.iter_rows():
      for cell in row:
        cell.alignment = wrap
    for cell in ws[1]:
      cell.font = Font(bold=True)
    for col, width in zip("ABCDEFGHIJKLM", widths):
      ws.column_dimensions[col].width = width
    ws.freeze_panes = "B2"
    
  meta = wb.create_sheet(META)
  meta.sheet_state = "hidden"
  for k, v in (("kind", KIND), ("bench", os.path.basename(os.path.normpath(bench_dir))), ("differences", len(diffs))):
    meta.append([k, v])
  os.makedirs(out_dir, exist_ok=True)
  path = os.path.join(out_dir, "sitting2.xlsx")
  wb.save(path)
  return {"path": path, "questions": len(MQ.open_questions()), "methods": len(unconfirmed_methods()), "differences": len(diffs)}

def read(path: str) -> dict:
  from openpyxl import load_workbook
  wb = load_workbook(path, data_only=True)
  if META not in wb.sheetnames or {QUESTIONS, CONFIRM, DIFFS} - set(wb.sheetnames):
    raise SheetError("this is not a sitting 2 sheet made by `sitting2 export`")
  if {str(r[0]): r[1] for r in wb[META].iter_rows(values_only=True) if r[0]}.get("kind") != KIND:
    raise SheetError("this is not a sitting 2 sheet made by `sitting2 export`")
  def cells(name: str) -> list:
    return [r for r in wb[name].iter_rows(min_row=2, values_only=True) if r[0] is not None]
  return {"questions": [{"id": str(r[0]), "answer": str(r[7] or "").strip()} for r in cells(QUESTIONS)], "methods": [{"id": str(r[0]), "decision": str(r[5] or "").strip().lower()} for r in cells(CONFIRM)],
    "differences": [{"key": str(r[0]), "set": str(r[1]), "element": str(r[2]), "floor": str(r[4]), "answer_qty": r[5], "trace_qty": r[6], "diff_pct": r[8], "money_pkr": r[10], "cause": str(r[11] or "").strip().upper(), "note": str(r[12] or "").strip()} for r in cells(DIFFS)]}

def quote(text: str) -> str:
  return json.dumps(text, ensure_ascii=False)

def block_of(lines: list, mid: str) -> tuple:
  start = next((n for n, ln in enumerate(lines) if re.match(rf"^\s*- id: {re.escape(mid)}\s*$", ln)), None)
  if start is None:
    return None, None
  end = next((n for n in range(start + 1, len(lines)) if re.match(r"^\s*- id: ", lines[n]) or re.match(r"^\S", lines[n])), len(lines))
  return start, end

def edit_methods(text: str, answers: list, decisions: list, by: str, today: str) -> tuple:
  lines = text.split("\n")
  done_q = done_m = 0
  refused = []
  
  for a in answers:
    n = next((i for i, ln in enumerate(lines) if re.match(rf"^\s*- \{{id: {re.escape(a['id'])},", ln)), None)
    if n is None:
      refused.append(f"{a['id']}: not an open question of methods_qs.yaml any more")
    elif "answered_by:" in lines[n]:
      refused.append(f"{a['id']}: already answered; change it in the file, not through a sheet")
    else:
      lines[n] = lines[n].rstrip()[:-1] + f", answer: {quote(a['answer'])}, answered_by: {quote(by)}, answered_date: \"{today}\"}}"
      done_q += 1
  for d in decisions:
    start, end = block_of(lines, d["id"])
    at = None if start is None else next((i for i in range(start, end) if "source: {kind: WORKBOOK" in lines[i] and "confirmed: false}" in lines[i]), None)
    if at is None:
      refused.append(f"{d['id']}: not a workbook-derived method awaiting confirmation")
      continue
  
    stamp = f"confirmed: true, confirmed_by: {quote(by)}, confirmed_date: \"{today}\"}}" if d["decision"] == YES else f"confirmed: false, denied_by: {quote(by)}, denied_date: \"{today}\"}}"
    lines[at] = lines[at].replace("confirmed: false}", stamp)
    done_m += 1
  return "\n".join(lines), done_q, done_m, refused

def apply(path: str, by: str, write: bool, today: str | None = None, methods_path: str | None = None, cases_dir: str | None = None) -> dict:
  if not by or not by.strip():
    raise SheetError("--by must name the QS who answered; an answer with no name is not one")
  by, today = by.strip(), today or datetime.date.today().isoformat()
  methods_path = methods_path or MQ.PATH
  book = read(path)
  
  answers = [a for a in book["questions"] if a["answer"]]
  decisions = [d for d in book["methods"] if d["decision"]]
  refused = [f"{d['id']}: confirmation is yes or no, not {d['decision']!r}" for d in decisions if d["decision"] not in (YES, NO)]
  decisions = [d for d in decisions if d["decision"] in (YES, NO)]
  owners = {p["qs"] for p in MQ.profiles()}
  if decisions and by not in owners:
    raise SheetError(f"only the QS a profile belongs to ({', '.join(sorted(owners))}) can confirm its methods, not {by!r}")
  with open(methods_path, encoding="utf-8", newline="") as fh:
    text = fh.read()
    
  crlf = "\r\n" in text
  new_text, done_q, done_m, bad = edit_methods(text.replace("\r\n", "\n"), answers, decisions, by, today)
  new_text = new_text.replace("\n", "\r\n") if crlf else new_text
  refused += bad
  diffs = [d for d in book["differences"] if d["cause"]]
  
  by_set: dict = {}
  for d in diffs:
    if d["cause"] not in CAUSES:
      refused.append(f"{d['key']}: cause {d['cause']!r} is not one of {', '.join(CAUSES)}")
    elif d["cause"] in NOTE_NEEDED and not d["note"]:
      refused.append(f"{d['key']}: cause {d['cause']} needs a note")
    elif d["element"] not in {i.id for i in CL.items()}:
      refused.append(f"{d['key']}: {d['element']} is not a catalogue item")
    else:
      by_set.setdefault(d["set"], []).append(d)
  tmp = methods_path + ".new"
  with open(tmp, "w", encoding="utf-8", newline="") as fh:
    fh.write(new_text)
  try:
    problems = MQ.problems(tmp)
  finally:
    os.remove(tmp)
  if problems:
    raise SheetError("methods_qs.yaml would not load after this import: " + "; ".join(problems[:3]))

  res = {"answers": done_q, "confirmed": done_m, "differences": sum(len(v) for v in by_set.values()), "sets": sorted(by_set), "refused": refused, "written": False}
  if write and not refused:
    if done_q or done_m:
      with open(methods_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(new_text)
      MQ.reload()
      
    for name, rows in sorted(by_set.items()):
      target = os.path.join(CIO.HERE if cases_dir is None else cases_dir, name, FILE)
      have = (AN.read_yaml(target) or {}).get("differences") or {}
      merged = {x["key"]: x for x in have.get("items") or []}
      for d in rows:
        merged[d["key"]] = AN.Flow({"key": d["key"], "element": d["element"], "floor": d["floor"], "answer_qty": d["answer_qty"], "trace_qty": d["trace_qty"], "diff_pct": d["diff_pct"], "money_pkr": d["money_pkr"], "cause": d["cause"], "note": d["note"]})
      AN.write_yaml(target, {"differences": {"set": name, "confirmed_by": by, "confirmed_date": today, "items": [merged[k] for k in sorted(merged)]}})
    res["written"] = True
  return res

def problems_of(doc: dict | None, name: str) -> list:
  out = []
  d = (doc or {}).get("differences")
  if not isinstance(d, dict) or d.get("set") != name or not d.get("confirmed_by") or not d.get("confirmed_date"):
    return [f"{name}/{FILE}: needs set, confirmed_by and confirmed_date"]
  ids = {i.id for i in CL.items()}
  for x in d.get("items") or []:
    if x.get("cause") not in CAUSES:
      out.append(f"{name}/{FILE}: {x.get('key')} has cause {x.get('cause')!r}")
    if x.get("element") not in ids:
      out.append(f"{name}/{FILE}: {x.get('key')} names {x.get('element')}, which is not a catalogue item")
    if x.get("cause") in NOTE_NEEDED and not x.get("note"):
      out.append(f"{name}/{FILE}: {x.get('key')} has cause {x.get('cause')} and no note")
  return out

def cmd_export(a) -> int:
  try:
    r = export(a.out, a.bench, FL.read_yaml("rates.yaml"), a.top)
  except SheetError as exc:
    print(f"refused: {exc}")
    return 1
  print(f"{r['questions']} open question(s), {r['methods']} method(s) to confirm, {r['differences']} difference(s) -> {r['path']}")
  if not (FL.read_yaml("rates.yaml").get("per_item_unit") or {}):
    print("rates.yaml holds no rate, so the differences are ordered by percentage, not money")
  return 0

def cmd_import(a) -> int:
  try:
    r = apply(a.workbook, a.by, a.write)
  except SheetError as exc:
    print(f"refused: {exc}")
    return 1
  print(f"{r['answers']} answer(s), {r['confirmed']} method decision(s), {r['differences']} difference cause(s) in {', '.join(r['sets']) or 'no set'}")
  for x in r["refused"]:
    print(f"  not applied: {x}")
  if r["refused"]:
    print("nothing written: fix the rows above and import again")
    return 1
  print("written to methods_qs.yaml and each case's differences.yaml" if r["written"] else "nothing written; add --write to record them under the QS's name and the date")
  return 0

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Sitting 2 sheet: the open method questions, the workbook-derived methods to confirm and the top differences between the workbook and Trace, and the import of the QS's answers.")
  sub = ap.add_subparsers(dest="cmd", required=True)
  ex = sub.add_parser("export")
  ex.add_argument("--bench", default="bench_out", help="a benchmark output folder (its rows.jsonl)")
  ex.add_argument("--out", default="mapping_out")
  ex.add_argument("--top", type=int, default=TOP)
  im = sub.add_parser("import")
  im.add_argument("workbook")
  im.add_argument("--by", required=True)
  im.add_argument("--write", action="store_true")
  a = ap.parse_args(argv)
  return {"export": cmd_export, "import": cmd_import}[a.cmd](a)

if __name__ == "__main__":
  sys.exit(main())
