from __future__ import annotations
import time
from app.engine.measure import rule_registry as RR
from app.modules.drawings_boq.takeoff.extract import floor_overlap as FO
from app.modules.drawings_boq.takeoff.extract import floor_sources as FS
from app.modules.drawings_boq.takeoff.extract import base_plan as BP

DEFAULT_MM_PER_POINT = 25.4 / 72.0 * 100.0           
PAGE_BUDGET_S = 30.0

def analyse_pdf(pdf: bytes, pages: list | None = None) -> tuple:
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
  from app.modules.drawings_boq.takeoff.extract import sheet_sections as SS
  SS.apply([(no, a.meta.get("identity")) for no, a in analysed.items()])
  from app.modules.drawings_boq.takeoff.extract import wall_scale as WS
  WS.apply([(no, a.meta.get("wall_gap"), a.meta.get("identity")) for no, a in analysed.items() if a.meta.get("identity")])
  from app.modules.drawings_boq.takeoff.profile import sheet_numbers as SN
  SN.apply([(no, a.meta) for no, a in analysed.items()])
  return doc, analysed, problems

def _outline_scales(prepared: list) -> list:
  from app.modules.drawings_boq.takeoff.extract import scale_outline as SO
  from app.modules.drawings_boq.takeoff.extract.scalegate import auto_scale_gate
  from app.modules.drawings_boq.takeoff.prep import facts as DF, outline_witness as OW
  from app.modules.drawings_boq.takeoff.prep.analyze import AGREE_TOL
  
  entries, held = [], {}
  for i, (_doc, analysed, _problems) in enumerate(prepared):
    for no, a in analysed.items():
      samples = ((a.meta or {}).get("outline") or {}).get("samples") or []
      full = a.detected_scale or {}
      ok, _code, _msg = auto_scale_gate(full)
      rec = full.get("recommended") or {}
      mm = float(rec["ratio"]) * SO.PT_MM if rec.get("ratio") else None
      ident, title = a.meta.get("identity") or {}, a.meta.get("title") or {}
      floor = ident.get("floor") or (None if title.get("composite") else title.get("level_hint"))
      entries.append({"id": (i, no), "page_no": no, "floor": floor, "trusted": bool(ok and mm), "mm_per_pt": mm, "samples": samples, "drawing": i,
        **SO.floor_fields(full, ident, full.get("paper") or (a.meta or {}).get("paper"))})
      held[(i, no)] = full
  verdicts = SO.propose(entries, list(DF.FLOOR_ORDER))
  out = [dict() for _ in prepared]
  
  built = {}
  for key, full in held.items():
    built[key] = full
    v = verdicts.get(key)
    if not v or v["status"] != SO.PROPOSED:
      continue
    
    prop = {**v, "ratio": v["mm_per_pt"] / SO.PT_MM}
    new = OW.rebuild(full, prop, [{"sheet_id": str(r), "page_no": r[1]} for r in v["refs"]], AGREE_TOL)
    built[key] = new
    settled = bool(((new.get("outline") or {}).get("verdict") or {}).get("settled"))
    if new.get("agreement") == "OUTLINE_ONLY" or settled:
      ratio = float(new["recommended"]["ratio"])
      out[key[0]][key[1]] = {"ratio": ratio, "mm_per_pt": ratio * 25.4 / 72.0, "refs": list(v["refs"]), "settled": settled}
      
  for key, prop in SO.inherit([{**e, "wanted": not auto_scale_gate(built[e["id"]])[0]} for e in entries]).items():
    new = OW.rebuild(held[key], None, [], AGREE_TOL, floor={**prop, "ref": prop["ref"]})
    ratio = float(new["recommended"]["ratio"])
    out[key[0]][key[1]] = {"ratio": ratio, "mm_per_pt": ratio * 25.4 / 72.0, "refs": [prop["ref"]], "settled": bool(prop["dims"]), "source": "FLOOR_PLAN"}
  return out

def _merge_project(sheets: list, others: list) -> dict:
  from app.modules.drawings_boq.takeoff.prep import project_facts as PF
  return PF.bundle([("this", s) for s in sheets] + [(name, s) for name, group in others for s in group], "this")

PROJECT_FACTS_RULE = "PROJECT_FACTS"

def project_facts_on() -> bool:
  return RR.on(PROJECT_FACTS_RULE)

def read_set(items: list, pages: dict | None = None, *, budget_s: float = PAGE_BUDGET_S, scale_unverified: bool = False, project: bool | None = None, storeys: list | None = None,
  sections: list | None = None, runs: bool | None = None, structure: bool = True, rules: dict | None = None, legends: dict | None = None, notes: dict | None = None) -> list:
  if rules:
    with RR.using(rules):
      return read_set(items, pages, budget_s=budget_s, scale_unverified=scale_unverified, project=project, storeys=storeys, sections=sections, runs=runs, structure=structure, legends=legends, notes=notes)
    
  from types import SimpleNamespace
  use = project_facts_on() if project is None else project
  prepared = [analyse_pdf(data, (pages or {}).get(name)) for name, data in items]
  if legends:
    from app.modules.drawings_boq.takeoff.ai_reader import legend as LG
    LG.attach(items, prepared, legends)
  if notes:
    from app.modules.drawings_boq.takeoff.ai_reader import notes as NT
    NT.attach(items, prepared, notes)
  scales = _outline_scales(prepared) if use else [dict() for _ in prepared]
  groups = [[SimpleNamespace(page_no=no, label=None, prep_meta=a.meta) for no, a in sorted(analysed.items())] for _doc, analysed, _p in prepared]
  out, every = [], []
  
  for i, (name, data) in enumerate(items):
    others = [(items[j][0], groups[j]) for j in range(len(items)) if j != i] if use and len(items) > 1 else []
    rows, problems = read_pdf(data, (pages or {}).get(name), budget_s=budget_s, scale_unverified=scale_unverified, prepared=prepared[i], project={"others": others, "scales": scales[i]}, storeys=storeys, sections=sections, runs=runs, structure=structure)
    for r in rows:
      r["drawing"], r["drawing_order"] = name, i
    out.append((name, rows, problems))
    every.extend(rows)
  if use:
    choose_floor_sources(every)
    choose_revisions(every)
  for doc, _a, _p in prepared:
    try:
      doc.close()
    except Exception:
      pass
  return out

def read_pdf(pdf: bytes, pages: list | None = None, *, budget_s: float = PAGE_BUDGET_S, scale_unverified: bool = False, prepared: tuple | None = None, project: dict | None = None, storeys: list | None = None, sections: list | None = None, runs: bool | None = None, structure: bool = True, rules: dict | None = None) -> tuple:
  if rules:
    with RR.using(rules):
      return read_pdf(pdf, pages, budget_s=budget_s, scale_unverified=scale_unverified, prepared=prepared, project=project, storeys=storeys, sections=sections, runs=runs, structure=structure)
  from types import SimpleNamespace
  from app.modules.drawings_boq.takeoff import prep_service as PSV
  from app.modules.drawings_boq.takeoff.prep import beam_details as BD, facts as DF, tank_details as TD, units as UR
  from app.modules.drawings_boq.takeoff.prep import schedules as DS, mark_vocab as MV, opening_heights as OHT
  from app.modules.drawings_boq.takeoff.prep.storeys import storey_heights
  from app.modules.drawings_boq.takeoff.extract import electrical as EL, pipeline as P, spec_facts as SPF
  from app.modules.drawings_boq.takeoff.prep.project_facts import column_details_of
  
  doc, analysed, problems = prepared if prepared is not None else analyse_pdf(pdf, pages)
  problems = list(problems)
  sheets = [SimpleNamespace(page_no=no, label=None, prep_meta=a.meta) for no, a in sorted(analysed.items())]
  schedule = DS.gather(PSV.PrepService._schedule_sheets(sheets))
  floor_keys = PSV.PrepService._floor_keys(sheets)

  gathered = DF.gather([{"page_no": s.page_no, "label": s.label, "facts": s.prep_meta.get("facts"), "ai_facts": s.prep_meta.get("ai_facts")} for s in sheets if s.prep_meta.get("facts") is not None])
  drawing = {"floor_heights": storey_heights(floor_keys, gathered.get("storeys")), "slab_values": DF.slab_values(gathered["items"]), "spec_facts": SPF.build(gathered["items"]),
    "beam_sections": BD.gather([{"page_no": s.page_no, "details": s.prep_meta.get("beam_details")} for s in sheets if s.prep_meta.get("beam_details")]),
    "tank_details": TD.gather([{"page_no": s.page_no, "details": s.prep_meta.get("tank_details")} for s in sheets if s.prep_meta.get("tank_details")]),
    "footing_sections": [{**sec, "page_no": s.page_no} for s in sheets for sec in (s.prep_meta.get("footing_sections") or [])],
    "footing_views": [{**v, "page_no": s.page_no} for s in sheets for v in (s.prep_meta.get("footing_views") or [])],
    "column_details": column_details_of([s.prep_meta for s in sheets])}
  units = UR.drawing_imperial([{"page_no": s.page_no, "units": s.prep_meta.get("units"), "hint": s.prep_meta.get("units_hint")} for s in sheets])
  merged = _merge_project(sheets, project["others"]) if project and project.get("others") else None
  
  if merged is not None:
    known = merged["facts"]
    schedule, units = known["schedule"], known["units"]
    drawing = {"floor_heights": known["storey_heights"], "slab_values": known["slab_values"], "spec_facts": known["spec_facts"], "beam_sections": known["beam_sections"],
      "tank_details": known["tank_details"], "footing_sections": known["footing_sections"], "footing_views": known["footing_views"], "column_details": known["column_details"]}
  runs = RR.on("BEAM_RUNS") if runs is None else runs
  
  if runs:
    from app.modules.drawings_boq.takeoff.extract import beam_members as BMEM
    drawing["band_sections"] = BMEM.table_sections(sheets, drawing["beam_sections"])
  opening_heights = OHT.decide(merged["facts"]["opening_labels"] if merged is not None else OHT.gather(sheets))
  vocab = MV.build(sheets + [s for _name, group in ((project or {}).get("others") or []) for s in group])
  legend = EL.project_rows(EL.gather_legend([{"page_no": no, "legend": a.meta.get("electrical_legend"), "ai_legend": a.meta.get("ai_legend")} for no, a in analysed.items() if a.meta.get("electrical_legend")]),
    [{"page_no": s.page_no, "legend": s.prep_meta.get("electrical_legend"), "ai_legend": s.prep_meta.get("ai_legend")} for _name, group in ((project or {}).get("others") or []) for s in group if (s.prep_meta or {}).get("electrical_legend")])
  
  
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
    source = (from_outline.get("source") or ("SETTLED" if from_outline.get("settled") else "OUTLINE")) if from_outline else ("MEASURED" if measured else ("LABELS" if labels else "DEFAULT"))
    mm_per_pt = used * 25.4 / 72.0 if used else DEFAULT_MM_PER_POINT
    
    try:
      res = P.run_extraction(a.index, mm_per_pt, composite=bool(title.get("composite")), regions_only=False, cal_factor=1.0, scale_unverified=scale_unverified or source == "DEFAULT", content_kind=a.content_kind,
        budget_s=budget_s, schedule=schedule, views_meta=meta.get("views"), frame=meta.get("frame"), col_details=drawing["column_details"], floor_heights=drawing["floor_heights"],
        level_hint=level_hint, slab_values=drawing["slab_values"], text_source=meta.get("text_source", "TEXT"), pdf_type=meta.get("pdf_type"), identity=meta.get("identity"), scan_reading=meta.get("scan_reading"), lowest_level=bool(level_hint) and bool(floor_keys) and floor_keys[0] == level_hint,
        with_finishes=True, beam_sections=drawing["beam_sections"], band_sections=drawing.get("band_sections"), tank_details=drawing["tank_details"], imperial=units["imperial"], wall_vocab=UR.wall_vocabulary(wall_rows, units["imperial"]),
        footing_sections=drawing["footing_sections"], footing_views=drawing["footing_views"], spec_facts=drawing["spec_facts"], mark_vocab=vocab, opening_heights=opening_heights,
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
      "seconds": round(time.monotonic() - started, 1), "facts": meta.get("facts"), **({"ai_facts": meta["ai_facts"]} if meta.get("ai_facts") else {}), "stats": res.stats,
      "meta": meta, "ratio": used, "scale_source": source, "content_kind": a.content_kind})
  read.sort(key=lambda sh: sh["page_no"])
  
  if structure:
    from app.modules.drawings_boq.takeoff.extract import member_passes as MP
    problems.extend(MP.run(read, floor_keys, drawing["floor_heights"], storeys=storeys, sections=sections, runs=runs))
  return read, problems

def choose_revisions(read: list) -> dict:
  from app.modules.drawings_boq.takeoff.extract import revisions as RV
  sheets = [{"sheet_id": (sh.get("drawing_order") or 0, sh["page_no"]), "page_no": sh["page_no"], "title": sh.get("title"), "stats": sh.get("stats"), "identity": (sh.get("meta") or {}).get("identity"),
    "candidates": sh["candidates"], "drawing_id": sh.get("drawing_order") or 0} for sh in read]
  return RV.apply_defaults(sheets)

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
      "read_as": (sh.get("stats") or {}).get("read_as"),
      "purpose": ((sh.get("stats") or {}).get("sheet_role") or {}).get("purpose") or (meta.get("identity") or {}).get("purpose")}
    
    sheet_floor = None if title.get("composite") else title.get("level_hint")
    floors = set(FO.floors_read(sh.get("stats"), title)[0]) | ({sheet_floor} if sheet_floor else set())
    for fl in floors:
      rows = [c for c in sh["candidates"] if FS.in_floor(c, fl, sheet_floor) and not FS.is_set_aside(c) and not BP.is_electrical(c)]
      if rows:
        by_floor.setdefault(fl, {})[key] = rows

  used = {}
  for floor, pages in by_floor.items():
    pool = [k for k in pages if BP.eligible(info[k])]
    sheets = [k for k in pages if BP.openings_sheet(info[k])]
    if not pool or (len(pool) < 2 and not sheets):
      continue
    keep = next((k for k in pool if k[1] == chosen.get(floor)), None) or min(pool, key=lambda k: BP.key(info[k]))
    used[floor] = keep[1]
    source = BP.openings_source(keep, sheets, pages)
    for page in [*pool, *sheets]:
      if page != keep:
        services = BP.keeps_services(info[page], info[keep], [info[k] for k in pool])
        for c in pages[page]:
          if (services and BP.is_services(c)) or (page == source and BP.is_opening(c)):
            continue
          c.facts = {**(c.facts or {}), FS.SET_ASIDE: {"by": FS.SET_ASIDE_BY, "page_no": keep[1]}}
    if source != keep:
      for c in pages[keep]:
        if BP.is_opening(c):
          c.facts = {**(c.facts or {}), FS.SET_ASIDE: {"by": FS.SET_ASIDE_BY, "page_no": source[1]}}
  return used
