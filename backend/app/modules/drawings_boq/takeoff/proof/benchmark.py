from __future__ import annotations
import argparse
import json
import os
import sys
import time
from app.modules.drawings_boq.takeoff.extract import floor_overlap as FO
from app.modules.drawings_boq.takeoff.extract import floor_sources as FS
from app.modules.drawings_boq.takeoff.proof import benchmark_sheet as BS
from app.modules.drawings_boq.takeoff.proof import known_facts as K
from app.modules.drawings_boq.takeoff.proof import readsummary as RS

DEFAULT_MM_PER_PT = 25.4 / 72.0 * 100.0           
PAGE_BUDGET_S = 30.0

def read_pdf(pdf: bytes, pages: list | None = None, *, budget_s: float = PAGE_BUDGET_S, scale_unverified: bool = False) -> tuple:
  from app.modules.drawings_boq.takeoff.prep.analyze import analyze_page
  from app.modules.drawings_boq.takeoff.prep import schedules as DS, units as UR
  from app.modules.drawings_boq.takeoff.extract import pipeline as P
  from app.modules.drawings_boq.takeoff.prep.extract import extract_page, open_document
  
  doc = open_document(pdf)
  total = len(doc)
  want = [p for p in (pages or range(1, total + 1)) if 1 <= p <= total]
  analysed, problems = {}, []
  for no in want:
    try:
      analysed[no] = analyze_page(extract_page(doc, no - 1, budget_s=20), 1.0, budget_s=20)
    except Exception as exc:                                                       
      problems.append((no, f"{type(exc).__name__}: {str(exc)[:80]}"))
  schedule = DS.gather([{"page_no": no, "schedule": a.meta.get("schedule")} for no, a in analysed.items()])
  
  read = []
  for no, a in sorted(analysed.items()):
    started = time.monotonic()
    meta = a.meta
    title = meta.get("title") or {}
    
    measured = ((a.detected_scale or {}).get("measured") or {}).get("clusters") or []
    mm_per_pt = float(measured[0]["ratio"]) * 25.4 / 72.0 if measured else DEFAULT_MM_PER_PT
    units = UR.drawing_imperial([{"page_no": no, "units": meta.get("units"), "hint": meta.get("units_hint")}])
    try:
      res = P.run_extraction(a.index, mm_per_pt, composite=bool(title.get("composite")), regions_only=False, cal_factor=1.0, scale_unverified=scale_unverified, content_kind=a.content_kind,
        budget_s=budget_s, schedule=schedule, views_meta=meta.get("views"), frame=meta.get("frame"), col_details={}, floor_heights={}, level_hint=title.get("level_hint"), slab_values=[],
        text_source=meta.get("text_source", "TEXT"), lowest_level=True, with_finishes=True, beam_sections=[], tank_details=[], imperial=units["imperial"], wall_vocab=[], footing_sections=[])
    except Exception as exc:
      problems.append((no, f"{type(exc).__name__}: {str(exc)[:80]}"))
      continue
  
    for c in res.candidates:
      c.decision = "PENDING"                                                       
    read.append({"page_no": no, "title": title, "schedule": schedule, "candidates": res.candidates, "notes": [n.get("code") for n in res.notes], "mm_per_pt": round(mm_per_pt, 4),
      "seconds": round(time.monotonic() - started, 1), "facts": meta.get("facts")})
  return read, problems

EXTRA_KINDS = ("ELECTRICAL", "NOT_BUILT") + BS.SHEET_KINDS

def choose_floor_sources(read: list, chosen: dict | None = None) -> dict:
  chosen = {str(k).upper(): int(v) for k, v in (chosen or {}).items()}
  by_floor: dict = {}
  composite: dict = {}
  
  for sh in read:
    title = sh.get("title") or {}
    composite[sh["page_no"]] = bool(title.get("composite"))
    sheet_floor = None if title.get("composite") else title.get("level_hint")
    for c in sh["candidates"]:
      floor = None if c.category == "SLAB" else (FO.level_of(c) or sheet_floor)
      if floor:
        by_floor.setdefault(floor, {}).setdefault(sh["page_no"], []).append(c)
        
  used = {}
  for floor, pages in by_floor.items():
    if len(pages) < 2:
      continue
    own = [p for p in pages if not composite[p]]
    keep = chosen[floor] if chosen.get(floor) in pages else min(own or pages)
    used[floor] = keep
    for page, rows in pages.items():
      if page != keep:
        for c in rows:
          c.facts = {**(c.facts or {}), FS.SET_ASIDE: {"by": FS.SET_ASIDE_BY, "page_no": keep}}
  return used

def load_facts(path: str) -> tuple:
  data = json.load(open(path, encoding="utf-8"))
  raw = data["facts"] if isinstance(data, dict) else data
  facts, notes, extras = [], [], []
  
  for i, r in enumerate(raw, 1):
    kind = str(r.get("kind") or "").strip().upper()
    if kind in EXTRA_KINDS:
      need = BS.NEEDS.get(kind) or (("symbol", "page", "count") if kind == "ELECTRICAL" else ("family", "count"))
      missing = [k for k in need if r.get(k) in (None, "")]
      if missing:
        raise SystemExit(f"{path}: fact {i}: a {kind} fact needs {', '.join(missing)}.")
      extras.append({**r, "kind": kind})
      continue
  
    try:
      facts.append(K.normalise(r))
    except ValueError as exc:
      raise SystemExit(f"{path}: fact {i}: {exc}")
    notes.append(str(r.get("note") or ""))
  electrical = data.get("electrical") if isinstance(data, dict) else None
  sources = data.get("floor_sources") if isinstance(data, dict) else None
  return facts, notes, extras, electrical, sources

def _extra_result(f: dict, status: str, expected, found, message: str) -> dict:
  if f["kind"] == "ELECTRICAL":
    text = f"{f['count']} x {f['symbol']} on page {f['page']}" + (f" ({f['floor'].lower()} floor)" if f.get("floor") else "")
  else:
    text = f"{f['count']} x {f['family']}" + (f" on the {f['floor'].lower()} floor" if f.get("floor") else "")
  return {"fact": {"kind": f["kind"], "category": f.get("symbol") or f.get("family")}, "text": text, "status": status, "expected": expected, "found": found, "message": message, "note": str(f.get("note") or "")}

def check_extras(extras: list, pdf: bytes, electrical: dict | None, read: list | None = None) -> list:
  out, counts = [], None
  sheet = [f for f in extras if f["kind"] in BS.SHEET_KINDS]
  extras = [f for f in extras if f["kind"] not in BS.SHEET_KINDS]
  out.extend(BS.check(f, read or []) for f in sheet)
  if any(f["kind"] == "ELECTRICAL" for f in extras):
    if not electrical or "legend_page" not in electrical or not electrical.get("plan_pages"):
      raise SystemExit("The facts file has ELECTRICAL facts but no \"electrical\": {\"legend_page\": n, \"plan_pages\": [...]}.")
  
    from app.modules.drawings_boq.takeoff.extract import electrical_symbols as ES
    from app.modules.drawings_boq.takeoff.prep.extract import open_document
    
    counts = ES.read_electrical(open_document(pdf), int(electrical["legend_page"]) - 1, [int(p) - 1 for p in electrical["plan_pages"]])["pages"]
  for f in extras:
    n = int(f["count"])
    if f["kind"] == "NOT_BUILT":
      out.append(_extra_result(f, K.MISSING, n, 0, f"The program has no kind of item for '{f['family']}' yet, so none were read."))
      continue
  
    page = counts.get(int(f["page"]))
    if page is None:
      out.append(_extra_result(f, K.MISSING, n, None, f"Page {f['page']} was not read by the electrical reader (it is not in the plan pages of the facts file)."))
    elif f["symbol"] in page["not_countable"]:
      out.append(_extra_result(f, K.MISSING, n, None, f"'{f['symbol']}' is in the legend, but the reader cannot count it (its legend picture is too simple to tell from other drawing)."))
    elif f["symbol"] not in page["counts"]:
      out.append(_extra_result(f, K.MISSING, n, None, f"'{f['symbol']}' is not in the legend the reader found."))
    else:
      got = int(page["counts"][f["symbol"]])
      if got == n:
        out.append(_extra_result(f, K.PASS, n, got, f"{got} of '{f['symbol']}' on page {f['page']}: as you say."))
      elif got == 0:
        out.append(_extra_result(f, K.MISSING, n, 0, f"None of '{f['symbol']}' was found on page {f['page']}."))
      else:
        out.append(_extra_result(f, K.FAIL, n, got, f"You say {n}; {got} were found on page {f['page']}."))
  return out

def by_kind(results: list) -> dict:
  out: dict = {}
  for r in results:
    slot = out.setdefault(r["fact"]["kind"], {"pass": 0, "fail": 0, "missing": 0})
    slot[r["status"].lower()] += 1
  return out

def by_category(results: list) -> dict:
  out: dict = {}
  
  for r in results:
    f = r["fact"]
    if f["kind"] != "TOTAL":
      continue
    exp, got = int(r["expected"] or 0), int(r["found"] or 0)
    slot = out.setdefault(f["category"], {"expected": 0, "found": 0, "agree": 0})
    slot["expected"] += exp
    slot["found"] += got
    slot["agree"] += min(exp, got)
  for slot in out.values():
    slot["recall"] = round(slot["agree"] / slot["expected"], 3) if slot["expected"] else None
    slot["precision"] = round(slot["agree"] / slot["found"], 3) if slot["found"] else None
  return out

def key_of(result: dict) -> str:
  return result["text"]

def compare(baseline: dict, results: list) -> dict:
  now = {key_of(r): r["status"] for r in results}
  lost = sorted(k for k, s in baseline.items() if s == K.PASS and now.get(k, K.MISSING) != K.PASS)
  gained = sorted(k for k, s in now.items() if s == K.PASS and baseline.get(k) not in (None, K.PASS))
  new = sorted(k for k in now if k not in baseline)
  return {"lost": lost, "gained": gained, "new": new}

def observed(read: list) -> dict:
  rows = []
  
  for sh in read:
    s = RS.summary([sh])
    rows.append({"page_no": sh["page_no"], "floor": (sh.get("title") or {}).get("level_hint"), "mm_per_pt": sh["mm_per_pt"], "seconds": sh["seconds"], **s})
  whole = RS.summary(read)
  schedule = sorted({(o.get("mark"), o.get("width_mm"), o.get("height_mm")) for sh in read for o in ((sh.get("schedule") or {}).get("openings") or [])}, key=lambda t: str(t[0]))
  return {"pages": rows, "set": whole, "schedule": [{"mark": m, "width_mm": w, "height_mm": h} for m, w, h in schedule]}

def report(name: str, read: list, problems: list, facts: list, notes: list, baseline: dict | None, extra_results: list | None = None) -> dict:
  results = K.check(read, facts) if facts else []
  for r, note in zip(results, notes):
    r["note"] = note
  results = results + list(extra_results or [])
  return {"set": name, "pages_read": [sh["page_no"] for sh in read], "problems": problems, "tally": K.tally(results), "by_kind": by_kind(results), "by_category": by_category(results),
    "results": [{"text": r["text"], "status": r["status"], "expected": r["expected"], "found": r["found"], "message": r["message"], "note": r.get("note", "")} for r in results],
    "versus_baseline": compare(baseline, results) if baseline is not None else None}

def render(rep: dict) -> str:
  t = rep["tally"]
  lines = [f"Benchmark: {rep['set']}", f"Pages read: {len(rep['pages_read'])}" + (f" | pages that could not be read: {', '.join(f'{p} ({w})' for p, w in rep['problems'])}" if rep["problems"] else ""),
    "Floor sources used (floors shown by more than one sheet): " + (", ".join(f"{f.lower()} = page {p}" for f, p in sorted(rep.get("floor_sources", {}).items())) or "none needed"),
    f"Facts: {t['pass']} pass, {t['fail']} fail, {t['missing']} missing (of {t['pass'] + t['fail'] + t['missing']})"]
  for kind, s in sorted(rep["by_kind"].items()):
    lines.append(f"  {kind:10} pass {s['pass']:3}  fail {s['fail']:3}  missing {s['missing']:3}")
    
  if rep["by_category"]:
    lines.append("Counts by kind of item (expected / found / recall / precision):")
    for cat, s in sorted(rep["by_category"].items()):
      rec = "-" if s["recall"] is None else "%.0f%%" % (100 * s["recall"])
      pre = "-" if s["precision"] is None else "%.0f%%" % (100 * s["precision"])
      lines.append("  %-10s %4d / %4d / %5s / %5s" % (cat, s["expected"], s["found"], rec, pre))
  bad = [r for r in rep["results"] if r["status"] != K.PASS]
  
  if bad:
    lines.append("Not passing:")
    lines.extend(f"  [{r['status']}] {r['text']}: {r['message']}" + (f"  ({r['note']})" if r["note"] else "") for r in bad)
  v = rep["versus_baseline"]
  if v is not None:
    lines.append(f"Against the baseline: {len(v['lost'])} lost, {len(v['gained'])} gained, {len(v['new'])} new")
    lines.extend(f"  LOST   {k}" for k in v["lost"])
    lines.extend(f"  GAINED {k}" for k in v["gained"])
  return "\n".join(lines)

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Read a drawing set and score it against facts checked by hand.")
  ap.add_argument("pdf")
  ap.add_argument("facts", nargs="?")
  ap.add_argument("--baseline")
  ap.add_argument("--save-baseline")
  ap.add_argument("--observed", action="store_true", help="also print what was read, page by page")
  ap.add_argument("--pages")
  ap.add_argument("--json")
  args = ap.parse_args(argv)
  
  pages = [int(p) for p in args.pages.split(",")] if args.pages else None
  read, problems = read_pdf(open(args.pdf, "rb").read(), pages)
  facts, notes, extras, electrical, sources = load_facts(args.facts) if args.facts else ([], [], [], None, None)
  used = choose_floor_sources(read, sources)
  baseline = json.load(open(args.baseline, encoding="utf-8")) if args.baseline and os.path.exists(args.baseline) else None
  pdf_bytes = open(args.pdf, "rb").read()
  rep = report(os.path.basename(args.pdf), read, problems, facts, notes, baseline, check_extras(extras, pdf_bytes, electrical, read))
  rep["floor_sources"] = used
  print(render(rep))
  if args.observed:
    obs = observed(read)
    rep["observed"] = obs
    print("\nWhat was read:")
    for p in obs["pages"]:
      print(f"  page {p['page_no']} floor={p['floor']} mm/pt={p['mm_per_pt']} ({p['seconds']}s) totals={p['totals']} rooms={sum(len(v) for v in p['rooms'].values())} slab={p['slab_m2']} wall_m={p['wall_m']}")
    print("  schedule rows:", obs["schedule"])
  if args.save_baseline:
    json.dump({r["text"]: r["status"] for r in rep["results"]}, open(args.save_baseline, "w", encoding="utf-8"), indent=1, sort_keys=True)
  if args.json:
    json.dump(rep, open(args.json, "w", encoding="utf-8"), indent=1, default=str)
  return 

if __name__ == "__main__":
  sys.exit(main())
