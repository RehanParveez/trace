from __future__ import annotations
import argparse
import datetime
import json
import os
import sys
from app.engine.catalogue import note_keys as NK
from app.modules.drawings_boq.takeoff.ai_reader import ask_plan as AP
from app.modules.drawings_boq.takeoff.ai_reader import notes as NT
from app.modules.drawings_boq.takeoff.ai_reader import regions as R
from app.modules.drawings_boq.takeoff.ai_reader import tasks as T
from app.modules.drawings_boq.takeoff.prep import facts as DF
from app.modules.drawings_boq.takeoff.prep import printed_params as PP
from app.modules.drawings_boq.takeoff.proof import case_io as CIO

PAGE_STEP = 10000

def missing(items: list) -> dict:
  return NT.missing(items)

def page_tiles(contents: bytes, page: int, need: dict) -> tuple:
  page_pt = R.page_picture(contents, page, 64)[1]["page_pt"]
  text = R.page_text(contents, page, page_pt)
  boxes = R.note_tiles(page_pt, len((text or "").split()))
  wanted = sum(1 for b in boxes if NT.tile_wanted(R.text_in_boxes(contents, page, [b]), need))
  return len(boxes), wanted

def pages_plan(contents: bytes, total: int, need: dict) -> dict:
  reads = len(T.route(NT.TASK)["scales"])
  pages, every, asked = [], 0, 0
  for page in range(1, total + 1):
    all_, want = page_tiles(contents, page, need)
    every += all_
    asked += want
    if want:
      pages.append(page)
  return {"pages": pages, "pages_all": total, "tiles_all": every, "tiles_asked": asked, "calls_all": every * reads, "calls_planned": asked * reads}

def read_items(blobs: list) -> list:
  from app.modules.drawings_boq.takeoff.run import reader as RDR
  sheets = []
  for n, (_name, data) in enumerate(blobs):
    doc, analysed, _problems = RDR.analyse_pdf(data)
    for no, a in sorted(analysed.items()):
      if (a.meta or {}).get("facts") is not None:
        sheets.append({"page_no": n * PAGE_STEP + no, "label": None, "facts": a.meta["facts"], "ai_facts": None})
    try:
      doc.close()
    except Exception:
      pass
  return DF.gather(sheets)["items"]

def plan_case(name: str, folder: str, files: dict, pdfs: list) -> dict:
  from app.modules.drawings_boq.takeoff.prep.extract import open_document
  blobs = []
  for pdf in pdfs:
    with open(files[pdf], "rb") as fh:
      blobs.append((pdf, fh.read()))
  items = read_items(blobs)
  need = missing(items)
  out: dict = {"case": name, "date": datetime.date.today().isoformat(), "keys_state": NK.state(), "need": need, "printed": sorted(PP.from_items(items)["params"]), "pdfs": {}}
  for pdf, data in blobs:
    doc = open_document(data)
    total = len(doc)
    doc.close()
    out["pdfs"][pdf] = pages_plan(data, total, need) if need else {"pages": [], "pages_all": total, "tiles_all": 0, "tiles_asked": 0, "calls_all": 0, "calls_planned": 0}
  return out

def lines(plans: list) -> list:
  out = []
  total = {"calls_all": 0, "calls_planned": 0}
  for p in plans:
    asked = {k: (", ".join(v) if v else "any scope") for k, v in p["need"].items()}
    out.append(f"{p['case']}: missing {len(p['need'])} of {len(NK.keys())} note keys" + (": " + "; ".join(f"{k} ({v})" for k, v in asked.items()) if asked else "; nothing to ask"))
    for pdf, v in sorted(p["pdfs"].items()):
      out.append(f"  {pdf}: {len(v['pages'])} of {v['pages_all']} page(s), {v['tiles_asked']} of {v['tiles_all']} tile(s), {v['calls_planned']} call(s) against {v['calls_all']} for every tile (two readings each, before any escalation)")
      total["calls_all"] += v["calls_all"]
      total["calls_planned"] += v["calls_planned"]
  out.append(f"all: {total['calls_planned']} call(s) planned against {total['calls_all']} for every tile of every page")
  return out

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Plan the NOTE_FACT asks of each case from what the rule reader left unread: which note keys are missing, and which pages and tiles could print them. It asks no model; --write keeps the plan beside the case so that `ai_fill_all --missing` asks only that.")
  ap.add_argument("--cases-dir", help="the folder with the case PDFs (default: TRACE_CASES_DIR)")
  ap.add_argument("--root", default=CIO.HERE, help="the folder of case folders")
  ap.add_argument("--case", action="append", default=[])
  ap.add_argument("--write", action="store_true")
  a = ap.parse_args(argv)
  
  cases_dir = CIO.cases_dir(a.cases_dir)
  if not cases_dir:
    print(f"Name the folder with the PDFs: --cases-dir, or set {CIO.CASES_DIR_ENV}.", file=sys.stderr)
    return 2
  plans = []
  for name in CIO.list_cases(a.root, audit=False):
    if a.case and name not in a.case:
      continue
    folder = os.path.join(a.root, name)
    case = CIO.load_case(folder)
    files, bad = CIO.find_files(case, cases_dir)
    if bad:
      print(f"{name}: {'; '.join(bad)}", file=sys.stderr)
      return 2
    plan = plan_case(name, folder, files, list(case["pdfs"]))
    plans.append(plan)
    print("\n".join(lines([plan])[:-1]), flush=True)
    if a.write:
      AP.write(folder, plan)
      
  print("\n".join(lines(plans)[-1:]))
  print(f"{len(plans)} case(s) planned" + ("; plans written beside each case" if a.write else "; nothing written, add --write"))
  return 0

if __name__ == "__main__":
  sys.exit(main())
