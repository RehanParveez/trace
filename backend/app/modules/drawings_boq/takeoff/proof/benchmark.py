from __future__ import annotations
import argparse
import json
import os
import sys
import time
from app.modules.drawings_boq.takeoff.extract.crosschecks import _floor, _sheet_floor
from app.modules.drawings_boq.takeoff.extract import floor_overlap as FO
from app.modules.drawings_boq.takeoff.extract import floor_sources as FS
from app.modules.drawings_boq.takeoff.proof import benchmark_sheet as BS
from app.modules.drawings_boq.takeoff.proof import known_facts as K
from app.modules.drawings_boq.takeoff.proof import readsummary as RS
from app.modules.drawings_boq.takeoff.extract import base_plan as BP
from app.modules.drawings_boq.takeoff.prep.project_facts import summary as PF_SUMMARY

DEFAULT_MM_PER_PT = 25.4 / 72.0 * 100.0           
PAGE_BUDGET_S = 30.0

def analyse_pdf(pdf: bytes, pages: list | None = None) -> tuple:
  """(document, {page: analysis}, problems): every page of the PDF read the way the application reads a sheet when it prepares it. read_pdf takes this as prepared, so a set of PDFs can be
  analysed first and read together."""
  from app.modules.drawings_boq.takeoff import prep_service as PSV
  from app.modules.drawings_boq.takeoff.prep.analyze import analyze_page
  from app.modules.drawings_boq.takeoff.prep.extract import extract_page, open_document
  doc = open_document(pdf)
  total = len(doc)
  want = [p for p in (pages or range(1, total + 1)) if 1 <= p <= total]
  analysed, problems = {}, []
  for no in want:
    try:
      raw = extract_page(doc, no - 1, budget_s=20)
      analysed[no] = analyze_page(raw, 1.0, budget_s=20)
      PSV._read_details(doc, no, raw, analysed[no])
    except Exception as exc:
      problems.append((no, f"{type(exc).__name__}: {str(exc)[:80]}"))
  return doc, analysed, problems

def _outline_scales(prepared: list) -> list:
  """The outline scale check (extract/scale_outline.propose) over the analysed PDFs of a set, as the application does it after the sheets are prepared. -> for each PDF {page: {"mm_per_pt",
  "ratio", "refs": [(pdf index, page)]}} of the sheets that printed no scale and take one from the outline of the other plans."""
  from app.modules.drawings_boq.takeoff.extract import scale_outline as SO
  from app.modules.drawings_boq.takeoff.extract.scalegate import auto_scale_gate
  from app.modules.drawings_boq.takeoff.prep import facts as DF, outline_witness as OW
  from app.modules.drawings_boq.takeoff.prep.analyze import AGREE_TOL
  entries, held = [], {}
  for i, (_doc, analysed, _problems) in enumerate(prepared):
    for no, a in analysed.items():
      samples = ((a.meta or {}).get("outline") or {}).get("samples")
      if not samples:
        continue
      full = a.detected_scale or {}
      ok, _code, _msg = auto_scale_gate(full)
      rec = full.get("recommended") or {}
      mm = float(rec["ratio"]) * SO.PT_MM if rec.get("ratio") else None
      ident, title = a.meta.get("identity") or {}, a.meta.get("title") or {}
      floor = ident.get("floor") or (None if title.get("composite") else title.get("level_hint"))
      entries.append({"id": (i, no), "page_no": no, "floor": floor, "trusted": bool(ok and mm), "mm_per_pt": mm, "samples": samples})
      held[(i, no)] = full
  verdicts = SO.propose(entries, list(DF.FLOOR_ORDER))
  out = [dict() for _ in prepared]
  for key, full in held.items():
    v = verdicts.get(key)
    if not v or v["status"] != SO.PROPOSED:
      continue
    prop = {**v, "ratio": v["mm_per_pt"] / SO.PT_MM}
    new = OW.rebuild(full, prop, [{"sheet_id": str(r), "page_no": r[1]} for r in v["refs"]], AGREE_TOL)
    settled = bool(((new.get("outline") or {}).get("verdict") or {}).get("settled"))
    if new.get("agreement") == "OUTLINE_ONLY" or settled:
      ratio = float(new["recommended"]["ratio"])
      out[key[0]][key[1]] = {"ratio": ratio, "mm_per_pt": ratio * 25.4 / 72.0, "refs": list(v["refs"]), "settled": settled}
  return out

def _merge_project(sheets: list, others: list) -> dict:
  """The facts of this PDF with what the other PDFs of the set print added (prep/project_facts.bundle). others: [(pdf name, sheets)]."""
  from app.modules.drawings_boq.takeoff.prep import project_facts as PF
  return PF.bundle([("this", s) for s in sheets] + [(name, s) for name, group in others for s in group], "this")

def read_set(items: list, pages: dict | None = None, *, budget_s: float = PAGE_BUDGET_S, scale_unverified: bool = False, project: bool | None = None) -> list:
  """The PDFs of a set read together, the way the application reads the PDFs of a project: [(name, pdf bytes)] -> [(name, rows, problems)]. Every PDF is analysed first. A sheet that printed
  no scale takes one from the outline of the other plans (any PDF), what one PDF does not print is taken from the others, and a floor drawn on plans of several PDFs keeps its base plan
  and sets the others aside. A set of one PDF is read as read_pdf reads it, except for the scale from the outline and the choice of the base plan. project=False (or TAKEOFF_PROJECT_FACTS off)
  reads each PDF alone."""
  from types import SimpleNamespace
  from app.core.config import settings
  use = settings.takeoff_project_facts if project is None else project
  prepared = [analyse_pdf(data, (pages or {}).get(name)) for name, data in items]
  scales = _outline_scales(prepared) if use else [dict() for _ in prepared]
  groups = [[SimpleNamespace(page_no=no, label=None, prep_meta=a.meta) for no, a in sorted(analysed.items())] for _doc, analysed, _p in prepared]
  out, every = [], []
  for i, (name, data) in enumerate(items):
    others = [(items[j][0], groups[j]) for j in range(len(items)) if j != i] if use and len(items) > 1 else []
    rows, problems = read_pdf(data, (pages or {}).get(name), budget_s=budget_s, scale_unverified=scale_unverified, prepared=prepared[i], project={"others": others, "scales": scales[i]})
    for r in rows:
      r["drawing"], r["drawing_order"] = name, i
    out.append((name, rows, problems))
    every.extend(rows)
  if use:
    choose_floor_sources(every)
  for doc, _a, _p in prepared:
    try:
      doc.close()
    except Exception:
      pass
  return out

def read_pdf(pdf: bytes, pages: list | None = None, *, budget_s: float = PAGE_BUDGET_S, scale_unverified: bool = False, prepared: tuple | None = None, project: dict | None = None) -> tuple:
  """Every page of the set read the way the application reads a drawing: the pictures on each sheet are read when it is analysed, and what the whole drawing prints (floor
  heights from the sections, slab values, specification, beam sections, tank and footing details, units, schedules) is gathered from all the sheets and given to each one. Only
  the database is left out. The wall thicknesses the drawing's own sheets agree on are gathered as the sheets are read, plain sheets first, as a first run does."""
  from types import SimpleNamespace
  from app.modules.drawings_boq.takeoff import prep_service as PSV
  from app.modules.drawings_boq.takeoff.prep import beam_details as BD, facts as DF, tank_details as TD, units as UR
  from app.modules.drawings_boq.takeoff.prep import schedules as DS, mark_vocab as MV, opening_heights as OHT
  from app.modules.drawings_boq.takeoff.prep.storeys import storey_heights
  from app.modules.drawings_boq.takeoff.extract import electrical as EL, pipeline as P, spec_facts as SPF
  from app.modules.drawings_boq.takeoff.extract.structure import column_details
  
  doc, analysed, problems = prepared if prepared is not None else analyse_pdf(pdf, pages)
  problems = list(problems)
  sheets = [SimpleNamespace(page_no=no, label=None, prep_meta=a.meta) for no, a in sorted(analysed.items())]
  schedule = DS.gather(PSV.PrepService._schedule_sheets(sheets))
  floor_keys = PSV.PrepService._floor_keys(sheets)

  gathered = DF.gather([{"page_no": s.page_no, "label": s.label, "facts": s.prep_meta.get("facts")} for s in sheets if s.prep_meta.get("facts") is not None])
  drawing = {"floor_heights": storey_heights(floor_keys, gathered.get("storeys")), "slab_values": DF.slab_values(gathered["items"]), "spec_facts": SPF.build(gathered["items"]),
    "beam_sections": BD.gather([{"page_no": s.page_no, "details": s.prep_meta.get("beam_details")} for s in sheets if s.prep_meta.get("beam_details")]),
    "tank_details": TD.gather([{"page_no": s.page_no, "details": s.prep_meta.get("tank_details")} for s in sheets if s.prep_meta.get("tank_details")]),
    "footing_sections": [{**sec, "page_no": s.page_no} for s in sheets for sec in (s.prep_meta.get("footing_sections") or [])]}
  units = UR.drawing_imperial([{"page_no": s.page_no, "units": s.prep_meta.get("units"), "hint": s.prep_meta.get("units_hint")} for s in sheets])
  merged = _merge_project(sheets, project["others"]) if project and project.get("others") else None
  if merged is not None:
    known = merged["facts"]
    schedule, units = known["schedule"], known["units"]
    drawing = {"floor_heights": known["storey_heights"], "slab_values": known["slab_values"], "spec_facts": known["spec_facts"], "beam_sections": known["beam_sections"],
      "tank_details": known["tank_details"], "footing_sections": known["footing_sections"]}
  opening_heights = OHT.decide(merged["facts"]["opening_labels"] if merged is not None else OHT.gather(sheets))
  vocab = MV.build(sheets + [s for _name, group in ((project or {}).get("others") or []) for s in group])
  legend = EL.project_rows(EL.gather_legend([{"page_no": no, "legend": a.meta.get("electrical_legend")} for no, a in analysed.items() if a.meta.get("electrical_legend")]),
    [{"page_no": s.page_no, "legend": s.prep_meta.get("electrical_legend")} for _name, group in ((project or {}).get("others") or []) for s in group if (s.prep_meta or {}).get("electrical_legend")])
  
  read, wall_rows = [], []
  order = sorted(analysed.items(), key=lambda kv: (bool(((kv[1].meta.get("title")) or {}).get("composite")), kv[0]))
  for no, a in order:
    started = time.monotonic()
    meta = a.meta
    title = meta.get("title") or {}
    level_hint = None if title.get("composite") else title.get("level_hint")
    
    measured = ((a.detected_scale or {}).get("measured") or {}).get("clusters") or []
    from_outline = ((project or {}).get("scales") or {}).get(no)
    if from_outline and measured and not from_outline.get("settled"):
      from_outline = None
    verdict = a.detected_scale or {}
    labels = float((verdict.get("recommended") or {}).get("ratio")) if not measured and verdict.get("agreement") == "ROOMS_ONLY" and (verdict.get("recommended") or {}).get("ratio") else None
    used = from_outline["ratio"] if from_outline else (float(measured[0]["ratio"]) if measured else labels)
    source = ("SETTLED" if from_outline.get("settled") else "OUTLINE") if from_outline else ("MEASURED" if measured else ("LABELS" if labels else "DEFAULT"))
    mm_per_pt = used * 25.4 / 72.0 if used else DEFAULT_MM_PER_PT
    try:
      res = P.run_extraction(a.index, mm_per_pt, composite=bool(title.get("composite")), regions_only=False, cal_factor=1.0, scale_unverified=scale_unverified, content_kind=a.content_kind,
        budget_s=budget_s, schedule=schedule, views_meta=meta.get("views"), frame=meta.get("frame"), col_details=column_details(meta), floor_heights=drawing["floor_heights"],
        level_hint=level_hint, slab_values=drawing["slab_values"], text_source=meta.get("text_source", "TEXT"), pdf_type=meta.get("pdf_type"), identity=meta.get("identity"), scan_reading=meta.get("scan_reading"), lowest_level=bool(level_hint) and bool(floor_keys) and floor_keys[0] == level_hint,
        with_finishes=True, beam_sections=drawing["beam_sections"], tank_details=drawing["tank_details"], imperial=units["imperial"], wall_vocab=UR.wall_vocabulary(wall_rows, units["imperial"]),
        footing_sections=drawing["footing_sections"], spec_facts=drawing["spec_facts"], mark_vocab=vocab, opening_heights=opening_heights,
        electrical=EL.count_page(doc, no, legend["rows"]) if legend["rows"] and EL.is_plan_sheet(a.index.words, meta.get("identity")) else None)
    except Exception as exc:
      problems.append((no, f"{type(exc).__name__}: {str(exc)[:80]}"))
      continue
  
    for c in res.candidates:
      c.decision = "PENDING"                                                       
      f = c.facts or {}
      if not title.get("composite") and c.category == "WALL" and f.get("thickness_used_mm"):
        wall_rows.append((f.get("thickness_used_mm"), f.get("thickness_standard_mm"), False))
    read.append({"page_no": no, "title": title, "schedule": schedule, "candidates": res.candidates, "notes": [n.get("code") for n in res.notes], "mm_per_pt": round(mm_per_pt, 4),
      "seconds": round(time.monotonic() - started, 1), "facts": meta.get("facts"), "stats": res.stats,
      "meta": meta, "ratio": used, "scale_source": source, "content_kind": a.content_kind})
  read.sort(key=lambda sh: sh["page_no"])
  return read, problems

EXTRA_KINDS = ("ELECTRICAL", "NOT_BUILT", "DRAINAGE", "QS_VOLUME") + BS.SHEET_KINDS
CFT_MM3 = 304.8 ** 3                       

def member_cft(c) -> float | None:
  """The concrete of a footing, column or beam item in cubic feet (number of pieces x length x width x depth, or height for a column); None while a size is missing."""
  p = c.params or {}
  depth = (p.get("height_mm") or p.get("depth_mm")) if c.category == "COLUMN" else p.get("depth_mm")
  if c.missing or not (p.get("length_mm") and p.get("width_mm") and depth):
    return None
  return int(c.count or 1) * float(p["length_mm"]) * float(p["width_mm"]) * float(depth) / CFT_MM3

def qs_range(f: dict) -> tuple:
  if f.get("min_cft") not in (None, "") and f.get("max_cft") not in (None, ""):
    return float(f["min_cft"]), float(f["max_cft"])
  mid, tol = float(f["cft"]), float(f["tolerance_pct"])
  return mid * (1.0 - tol / 100.0), mid * (1.0 + tol / 100.0)

def qs_volume(f: dict, read: list) -> dict:
  lo, hi = qs_range(f)
  floor = str(f.get("floor") or "").upper() or None
  category = str(f["category"]).upper()

  items = [c for sh in read for c in sh["candidates"] if c.category == category and not FS.is_set_aside(c)
    and (floor is None or (FO.level_of(c) or (sh.get("title") or {}).get("level_hint")) == floor)]
  got = [member_cft(c) for c in items]
  found = round(sum(v for v in got if v is not None), 1)
  open_items = [c for c, v in zip(items, got) if v is None]
  text = f"{category.lower()} concrete {lo:g} to {hi:g} cft" + (f" on the {floor.lower()} floor" if floor else "")
  base = {"fact": {"kind": "QS_VOLUME", "category": category}, "text": text, "expected": f"{lo:g} to {hi:g} cft", "found": found, "note": str(f.get("note") or "")}

  if not items:
    return {**base, "status": K.MISSING, "found": None, "message": f"No {category.lower()} item was read."}
  if found > hi:
    return {**base, "status": K.FAIL, "message": f"The QS has {lo:g} to {hi:g} cft; {found:g} cft is read from {len(items) - len(open_items)} of {len(items)} items (more than the QS's top figure)."}
  if open_items:
    need = sorted({m for c in open_items for m in (c.missing or ["a size"])})
    return {**base, "status": K.MISSING, "message": f"{len(open_items)} of {len(items)} items have no {', '.join(need)} yet; the other {len(items) - len(open_items)} give {found:g} cft (QS {lo:g} to {hi:g})."}
  if lo <= found <= hi:
    return {**base, "status": K.PASS, "message": f"{found:g} cft from {len(items)} items, inside the QS's {lo:g} to {hi:g} cft."}
  return {**base, "status": K.FAIL, "message": f"The QS has {lo:g} to {hi:g} cft; {found:g} cft is read from {len(items)} items."}

def choose_floor_sources(read: list, chosen: dict | None = None) -> dict:
  chosen = {str(k).upper(): int(v) for k, v in (chosen or {}).items()}
  by_floor: dict = {}
  info: dict = {}

  for sh in read:
    title = sh.get("title") or {}
    meta = sh.get("meta") or {}
    key = (sh.get("drawing_order") or 0, sh["page_no"])
    info[key] = {"page_no": sh["page_no"], "drawing_order": key[0], "from_plans": bool(title.get("composite")), "plan_kind": (meta.get("identity") or {}).get("plan_kind"),
      "dims": int((meta.get("floor_clues") or {}).get("dim_pairs") or 0), "advice": ((sh.get("stats") or {}).get("sheet_role") or {}).get("advice"),
      "read_as": (sh.get("stats") or {}).get("read_as")}
    
    sheet_floor = None if title.get("composite") else title.get("level_hint")
    floors = set(FO.floors_read(sh.get("stats"), title)[0]) | ({sheet_floor} if sheet_floor else set())
    for fl in floors:
      rows = [c for c in sh["candidates"] if FS.in_floor(c, fl, sheet_floor) and not FS.is_set_aside(c) and not BP.is_electrical(c)]
      if rows:
        by_floor.setdefault(fl, {})[key] = rows

  used = {}
  for floor, pages in by_floor.items():
    pool = [k for k in pages if BP.eligible(info[k])]
    if len(pool) < 2:
      continue
    keep = next((k for k in pool if k[1] == chosen.get(floor)), None) or min(pool, key=lambda k: BP.key(info[k]))
    used[floor] = keep[1]
    for page in pool:
      if page != keep:
        services = BP.keeps_services(info[page], info[keep], [info[k] for k in pool])
        for c in pages[page]:
          if services and BP.is_services(c):
            continue
          c.facts = {**(c.facts or {}), FS.SET_ASIDE: {"by": FS.SET_ASIDE_BY, "page_no": keep[1]}}
  return used

def load_facts(path: str) -> tuple:
  data = json.load(open(path, encoding="utf-8"))
  raw = data["facts"] if isinstance(data, dict) else data
  facts, notes, extras = [], [], []
  
  for i, r in enumerate(raw, 1):
    kind = str(r.get("kind") or "").strip().upper()
    if kind in EXTRA_KINDS:
      need = BS.NEEDS.get(kind) or (("symbol", "page", "count") if kind == "ELECTRICAL" else (("item", "family", "count") if kind == "DRAINAGE" else (("category",) if kind == "QS_VOLUME" else ("family", "count"))))
      missing = [k for k in need if r.get(k) in (None, "")]
      if kind == "QS_VOLUME" and not ((r.get("cft") not in (None, "") and r.get("tolerance_pct") not in (None, "")) or (r.get("min_cft") not in (None, "") and r.get("max_cft") not in (None, ""))):
        missing.append("min_cft and max_cft (or cft and tolerance_pct)")
      if missing:
        raise SystemExit(f"{path}: fact {i}: a {kind} fact needs {', '.join(missing)}.")
      extras.append({**r, "kind": kind})
      continue
  
    try:
      f = K.normalise(r)
    except ValueError as exc:
      raise SystemExit(f"{path}: fact {i}: {exc}")
    if str(r.get("checked_by") or "").strip():
      f["checked_by"] = str(r["checked_by"]).strip()
    facts.append(f)
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
  for f in sheet:
    out.append({**BS.check(f, read or []), "checked_by": str(f.get("checked_by") or "").strip()})
  if any(f["kind"] == "ELECTRICAL" for f in extras):
    if not electrical or "legend_page" not in electrical or not electrical.get("plan_pages"):
      raise SystemExit("The facts file has ELECTRICAL facts but no \"electrical\": {\"legend_page\": n, \"plan_pages\": [...]}.")
  
    from app.modules.drawings_boq.takeoff.extract import electrical_symbols as ES
    from app.modules.drawings_boq.takeoff.prep.extract import open_document
    
    counts = ES.read_electrical(open_document(pdf), int(electrical["legend_page"]) - 1, [int(p) - 1 for p in electrical["plan_pages"]])["pages"]
  tagged = len(out)
  for f in extras:
    for r in out[tagged:]:
      r.setdefault("checked_by", str(prev.get("checked_by") or "").strip())
    prev, tagged = f, len(out)
    if f["kind"] == "QS_VOLUME":
      out.append(qs_volume(f, read or []))
      continue
    n = int(f["count"])
    if f["kind"] == "DRAINAGE":
      page = int(f["page"]) if f.get("page") not in (None, "") else None
      got = sum(int(c.count or 1) for sh in (read or []) if page is None or sh["page_no"] == page for c in sh["candidates"] if (c.facts or {}).get("drainage") == f["item"])
      where = f" on page {page}" if page else ""
      if got == n:
        out.append(_extra_result(f, K.PASS, n, got, f"{got} of '{f['family']}' read{where}: as you say."))
      elif got == 0:
        out.append(_extra_result(f, K.MISSING, n, 0, f"None of '{f['family']}' was read{where}."))
      else:
        out.append(_extra_result(f, K.FAIL, n, got, f"You say {n}; {got} were read{where}."))
      continue
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
  for r in out[tagged:]:
    r.setdefault("checked_by", str(prev.get("checked_by") or "").strip() if extras else "")
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

def _polyline_m(c, mm_per_pt: float) -> float:
  pts = (c.geometry or {}).get("points") or []
  if c.kind == "COUNT" or len(pts) < 2:
    return 0.0
  return sum(((pts[i + 1][0] - pts[i][0]) ** 2 + (pts[i + 1][1] - pts[i][1]) ** 2) ** 0.5 for i in range(len(pts) - 1)) * mm_per_pt / 1000.0

def open_items(read: list) -> list:
  groups: dict = {}
  for sh in read:
    for c in sh["candidates"]:
      if FS.is_set_aside(c) or not c.missing:
        continue
    
      f = c.facts or {}
      n = int(c.count or 1)
      key = (c.category, f.get("foundation_item") or c.kind, tuple(sorted(c.missing)))
      g = groups.setdefault(key, {"category": key[0], "kind": key[1], "missing": list(key[2]), "items": 0, "pieces": 0, "metres": 0.0, "area_m2": 0.0, "no_floor": 0, "pages": set()})
      g["items"] += 1
      g["pieces"] += n
      g["metres"] += float(f["length_cc_m"]) * n if f.get("length_cc_m") else _polyline_m(c, float(sh.get("mm_per_pt") or 0.0))
      g["area_m2"] += float(f["area_m2"]) if f.get("area_m2") else 0.0
      g["no_floor"] += 0 if (FO.level_of(c) or (sh.get("title") or {}).get("level_hint")) else 1
      g["pages"].add(sh["page_no"])
  rows = [{**g, "metres": round(g["metres"], 1), "area_m2": round(g["area_m2"], 1), "pages": sorted(g["pages"])} for g in groups.values()]
  return sorted(rows, key=lambda g: (-g["metres"], -g["pieces"], g["category"], g["kind"]))

def render_open(rows: list) -> str:
  if not rows:
    return "Open items: none. Every item read has its sizes."
  lines = [f"Open items: {sum(r['items'] for r in rows)} items in {len(rows)} groups still lack something (biggest first; no rupees, see the value at risk in the application):"]
  for r in rows:
    lines.append("  %-9s %-18s lacks %-28s %4d items (%d no floor) %5d pieces %8.1f m %8.1f m2  pages %s" % (r["category"], str(r["kind"])[:18], ", ".join(r["missing"])[:28], r["items"], r["no_floor"], r["pieces"], r["metres"], r["area_m2"], ",".join(str(p) for p in r["pages"])))
  return "\n".join(lines)

def _checked(r: dict) -> str:
  return str(r.get("checked_by") or (r.get("fact") or {}).get("checked_by") or "").strip()

def checked_summary(results: list) -> dict:
  """How much of the score rests on a person: a fact counts as checked only when a person put their name in its \"checked_by\". Every other fact is a draft, however it was made."""
  rows = [r for r in results if _checked(r)]
  return {"checked": len(rows), "draft": len(results) - len(rows), "by": sorted({_checked(r) for r in rows}), "tally": K.tally(rows)}

def calibration(read: list, results: list) -> list:
  """For each kind of item that has facts checked by a person: how many of them pass, against the confidence the reading gave those items (the mean of the items that are not set aside).
  A reading whose confidence means what it says has the two close. Only checked facts are used: a draft made from the reading would agree with it by construction."""
  slots: dict = {}
  for r in results:
    f = r.get("fact") or {}
    if not _checked(r):
      continue
    cat = f.get("category") if f.get("kind") in ("TOTAL", "COUNT", "QS_VOLUME") else "ROOM" if f.get("kind") == "ROOM_AREA" else "SLAB" if f.get("kind") == "SLAB_AREA" else None
    if cat:
      s = slots.setdefault(cat, {"category": cat, "checked": 0, "pass": 0})
      s["checked"] += 1
      s["pass"] += 1 if r["status"] == K.PASS else 0
  out = []
  for cat, s in sorted(slots.items()):
    conf = [float(c.confidence) for sh in read for c in sh["candidates"] if c.category == cat and not FS.is_set_aside(c) and (c.confidence or 0) > 0]
    out.append({**s, "pass_rate": round(s["pass"] / s["checked"], 3), "mean_confidence": round(sum(conf) / len(conf), 3) if conf else None, "items": len(conf)})
  return out

def draft_facts(read: list, set_name: str, pdf_name: str) -> dict:
  """A facts file made from what was read, for a person to correct. It saves typing, and it proves nothing: every fact in it is a draft (its \"checked_by\" is empty) until a person has
  compared it with the plan and put their name there."""
  def pages(pred, floor=None) -> str:
    return ", ".join(str(p) for p in sorted({sh["page_no"] for sh in read if any(pred(c) and (floor is None or (_floor(c, _sheet_floor(sh)) or "UNKNOWN") == floor) for c in sh["candidates"])})) or "?"
  def note(pred, floor=None) -> str:
    return f"read by the program from page {pages(pred, floor)}; check it against the plan, correct it, then put your name in checked_by"
  floors = set(K.FLOOR_WORDS.values())
  facts: list = []
  for cat in ("DOOR", "WINDOW", "COLUMN", "FOOTING"):
    table = RS.counts(read, cat)
    for fl in sorted(table):
      if fl not in floors:
        continue

      pred = lambda c, cat=cat: c.category == cat and not FS.is_set_aside(c)
      facts.append({"kind": "TOTAL", "category": cat, "floor": fl, "count": sum(table[fl].values()), "note": note(pred, fl), "checked_by": ""})
      for tag, n in sorted(table[fl].items()):
        if tag != "(no mark)":
          facts.append({"kind": "COUNT", "category": cat, "floor": fl, "tag": tag, "count": n, "note": note(lambda c, cat=cat, tag=tag: c.category == cat and c.tag == tag and not FS.is_set_aside(c), fl), "checked_by": ""})
  for fl, by in sorted(RS.rooms(read).items()):
    for name, area in sorted(by.items()):
      if fl in floors and "#" not in name:
        facts.append({"kind": "ROOM_AREA", "name": name, "floor": fl, "area_m2": round(area, 2), "note": note(lambda c, name=name: c.category == "ROOM" and not FS.is_set_aside(c) and str((c.facts or {}).get("name") or "").strip().upper() == name, fl), "checked_by": ""})
  for fl, area in sorted(RS.slabs(read).items()):
    if fl in floors:
      facts.append({"kind": "SLAB_AREA", "floor": fl, "area_m2": round(area, 2), "note": note(lambda c: c.category == "SLAB" and not FS.is_set_aside(c), fl), "checked_by": ""})

  rows = {}
  for sh in read:
    for o in ((sh.get("schedule") or {}).get("openings") or []):
      if o.get("mark"):
        rows.setdefault(str(o["mark"]).upper(), (sh["page_no"], o))
  for mark, (page, o) in sorted(rows.items()):
    facts.append({"kind": "SCHEDULE", "mark": mark, **{k: o[k] for k in ("width_mm", "height_mm") if o.get(k) is not None}, "note": f"read by the program from the schedule on page {page}; check it against the schedule, then put your name in checked_by", "checked_by": ""})
  return {"set": set_name, "pdf": pdf_name, "status": "DRAFT: made from what the program read, not by a person. A fact counts as checked only when its checked_by has a name.", "facts": facts}

def report(name: str, read: list, problems: list, facts: list, notes: list, baseline: dict | None, extra_results: list | None = None) -> dict:
  results = K.check(read, facts) if facts else []
  for r, note in zip(results, notes):
    r["note"] = note
  results = results + list(extra_results or [])
  return {"set": name, "pages_read": [sh["page_no"] for sh in read], "problems": problems, "tally": K.tally(results), "by_kind": by_kind(results), "by_category": by_category(results),
    "checked": checked_summary(results), "calibration": calibration(read, results),
    "results": [{"text": r["text"], "status": r["status"], "expected": r["expected"], "found": r["found"], "message": r["message"], "note": r.get("note", ""), "checked_by": _checked(r)} for r in results],
    "versus_baseline": compare(baseline, results) if baseline is not None else None}

def render(rep: dict) -> str:
  t = rep["tally"]
  lines = [f"Benchmark: {rep['set']}", f"Pages read: {len(rep['pages_read'])}" + (f" | pages that could not be read: {', '.join(f'{p} ({w})' for p, w in rep['problems'])}" if rep["problems"] else ""),
    "Floor sources used (floors shown by more than one sheet): " + (", ".join(f"{f.lower()} = page {p}" for f, p in sorted(rep.get("floor_sources", {}).items())) or "none needed"),
    f"Facts: {t['pass']} pass, {t['fail']} fail, {t['missing']} missing (of {t['pass'] + t['fail'] + t['missing']})"]
  ck = rep["checked"]
  lines.append(f"Checked by a person: {ck['checked']} of {ck['checked'] + ck['draft']} facts" + (f" ({', '.join(ck['by'])}): {ck['tally']['pass']} pass, {ck['tally']['fail']} fail, {ck['tally']['missing']} missing" if ck["checked"] else "")
    + f"; the other {ck['draft']} are drafts, so the score above rests on them.")
  for kind, s in sorted(rep["by_kind"].items()):
    lines.append(f"  {kind:10} pass {s['pass']:3}  fail {s['fail']:3}  missing {s['missing']:3}")
    
  if rep["by_category"]:
    lines.append("Counts by kind of item (expected / found / recall / precision):")
    for cat, s in sorted(rep["by_category"].items()):
      rec = "-" if s["recall"] is None else "%.0f%%" % (100 * s["recall"])
      pre = "-" if s["precision"] is None else "%.0f%%" % (100 * s["precision"])
      lines.append("  %-10s %4d / %4d / %5s / %5s" % (cat, s["expected"], s["found"], rec, pre))
  if rep["calibration"]:
    lines.append("Confidence against facts checked by a person (kind of item / checked / pass rate / mean confidence of the items read):")
    lines.extend("  %-10s %4d / %5s / %s" % (r["category"], r["checked"], "%.0f%%" % (100 * r["pass_rate"]), "-" if r["mean_confidence"] is None else "%.0f%% (%d items)" % (100 * r["mean_confidence"], r["items"])) for r in rep["calibration"])
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
  ap.add_argument("--draft-facts", help="write a facts file made from what was read, for a person to check and correct (every fact in it is a draft until checked_by has a name)")
  ap.add_argument("--open", action="store_true", help="also list what is still open (items that lack a size), the biggest first")
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
  if args.draft_facts:
    json.dump(draft_facts(read, os.path.splitext(os.path.basename(args.pdf))[0], os.path.basename(args.pdf)), open(args.draft_facts, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"\nA draft facts file was written to {args.draft_facts}: check each fact against the plan and put your name in its checked_by.")
  if args.open:
    rep["open"] = open_items(read)
    print("\n" + render_open(rep["open"]))
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
