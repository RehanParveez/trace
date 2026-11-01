from __future__ import annotations
import argparse
import json
import os
import re
import sys
import yaml

FT_MM = 304.8
FACTORS = ("count", "length", "width", "height")
PART_ORDER = ("only_qs", "only_trace", "count", "length", "width", "height", "openings", "lintels", "overlap", "other", "rows_vs_dims")
GROUP_OF = {"only_qs": "extent", "only_trace": "extent", "count": "extent", "length": "extent", "width": "height_or_thickness", "height": "height_or_thickness",
  "openings": "deductions", "lintels": "deductions", "other": "deductions", "overlap": "convention", "rows_vs_dims": "typed_totals"}
GROUPS = ("extent", "height_or_thickness", "deductions", "convention", "typed_totals")
PART_TEXT = {"only_qs": "in the workbook, not in Trace", "only_trace": "in Trace, not in the workbook", "count": "number of members or runs", "length": "length per member or run",
  "width": "width or thickness", "height": "height or depth", "openings": "door, window and ventilator openings", "lintels": "lintel volume taken out of the wall",
  "overlap": "volume given to the slab or beam that shares it (FRAME_MONOLITHIC_A, rule wall.intrusion_deducted)", "other": "other adjustment",
  "rows_vs_dims": "workbook row total not equal to its own length x width x height"}
DED = "(deductions)"
WORKBOOK_COLUMNS = {"desc": 1, "nos": 3, "length": 4, "width": 5, "height": 6, "qty": 7, "remark": 8}
BRICK_STAGES = (("plinth beam to lintel", "PLINTH_TO_LINTEL"), ("lintel level to basement slab", "LINTEL_TO_SLAB"), ("ground floor", "UPPER_FLOOR_1"),
  ("first floor", "UPPER_FLOOR_2"), ("mumty", "UPPER_FLOOR_3"))

def _num(v):
  if isinstance(v, bool) or v is None:
    return None
  if isinstance(v, (int, float)):
    return float(v)
  try:
    return float(str(v).strip().replace(",", ""))
  except ValueError:
    return None

def _text(v) -> str:
  return "" if v is None else str(v).strip()

def volume(t: dict) -> float:
  if t.get("length") is None or t.get("width") is None or t.get("height") is None:
    return 0.0
  return t["nos"] * t["length"] * t["width"] * t["height"]

def term(key, nos, length, width, height, qty, label="", deduction=False, kind=None) -> dict:
  return {"key": key, "nos": float(nos), "length": length, "width": width, "height": height, "qty": float(qty), "label": label, "deduction": bool(deduction), "kind": kind}

def mark_of(text: str) -> str | None:
  m = re.search(r"\b([A-Z]{1,2})[-\s]?(\d+)\b", text.upper())
  return f"{m.group(1)}{m.group(2)}" if m else None

def wall_class(width_ft: float | None, remark: str = "", by_width: bool = False) -> str:
  if "4.5" in remark:
    return "4.5"
  if by_width and width_ft is not None:
    return "4.5" if width_ft < 0.55 else "9"
  return "9"

def class_of_tag(tag: str, thickness_mm: float | None = None) -> str:
  t = (tag or "").upper()
  if "4.5IN" in t or "4.5\" WALL" in t or "4.5IN" in t.replace(" ", ""):
    return "4.5"
  if "9IN" in t:
    return "9"
  if thickness_mm is not None:
    return "4.5" if thickness_mm < 150 else "9"
  return "9"

def read_sheet(ws, first: int, last: int) -> list:
  out, sections = [], []
  
  for r in range(first, last + 1):
    cells = [ws.cell(row=r, column=c + 1).value for c in range(10)]
    desc = _text(cells[WORKBOOK_COLUMNS["desc"]])
    nos, ln, wd, ht, qty = (_num(cells[WORKBOOK_COLUMNS[k]]) for k in ("nos", "length", "width", "height", "qty"))
    
    if nos is None and (qty is None or qty == 0):
      if desc:
        sections.append(desc)
      continue
    if qty is None:
      qty = (nos or 1.0) * (ln or 0.0) * (wd if wd is not None else 1.0) * (ht if ht is not None else 1.0)
    out.append({"row": r, "desc": desc, "nos": nos if nos is not None else 1.0, "length": ln, "width": wd, "height": ht, "qty": qty,
      "remark": _text(cells[WORKBOOK_COLUMNS["remark"]]) if isinstance(cells[WORKBOOK_COLUMNS["remark"]], str) else "", "sections": list(sections)})
  return out

def qs_excavation(r):
  if "complete area" in r["desc"].lower():
    return "BASE", False
  return wall_class(r["width"], r["remark"]), False

def qs_pcc(r):
  if "column foundation" in " ".join(r["sections"]).lower():
    return "FOOTING-BED", False
  return wall_class(None, r["remark"]), False

def qs_brick_step(r):
  step = None
  for s in reversed(r["sections"]):
    m = re.match(r"(\d)(?:st|nd|rd|th) step", s.lower())
    if m:
      step = m.group(1)
      break
  return f"{wall_class(None, r['remark'])} step {step}", False

def qs_mark(r):
  text = r["remark"] or r["desc"]
  m = mark_of(text)
  if m:
    return m, False
  return ("OPEN" if "open" in r["desc"].lower() else (m or r["desc"][:20].upper())), False

def qs_beam_class(r):
  return wall_class(r["width"], r["remark"], True), False

def qs_wall_stage(r):
  stage = None
  for s in reversed(r["sections"]):
    low = s.lower()
    for token, name in BRICK_STAGES:
      if token in low:
        stage = name
        break
    if stage:
      break
  if r["qty"] < 0:
    return f"{stage} {DED}", True
  return f"{stage} {wall_class(r['width'], r['remark'], True)}", False

QS_KEYS = {"excavation": qs_excavation, "pcc": qs_pcc, "brick_step": qs_brick_step, "mark": qs_mark, "beam_class": qs_beam_class, "wall_stage": qs_wall_stage}

def _ledger_nos(r: dict) -> float:
  for step in ((r.get("trace") or {}).get("steps") or []):
    if step.get("op") == "count" and step.get("nos") is not None:
      try:
        return float(step["nos"])
      except (TypeError, ValueError):
        return 1.0
  return 1.0

def _inputs(r: dict) -> dict:
  return (r.get("trace") or {}).get("inputs") or {}

def tr_trench(r, tag):
  t = tag.upper()
  if t.startswith("EXCAVATION"):
    return "BASE"
  return class_of_tag(t)

def tr_pcc(r, tag):
  t = tag.upper()
  if t.startswith("PCC-STRIP"):
    return class_of_tag(t)
  return "FOOTING-BED"

def tr_brick_step(r, tag):
  m = re.match(r"BRICK-STEP-(.*)-(\d)$", tag.upper())
  return f"{class_of_tag(tag)} step {m.group(2) if m else '?'}"

def tr_mark(r, tag):
  label = (r.get("trace") or {}).get("label") or ""
  t = tag.upper()
  if "OPEN" in t:
    return "OPEN"
  m = mark_of(re.sub(r"^L-", "", t)) if t else None
  if m:
    return m
  m = mark_of(label)
  return m or t or label[:20].upper()

def tr_beam_class(r, tag):
  return class_of_tag(tag, None)

def tr_wall_stage(r, tag):
  i = _inputs(r)
  return f"{i.get('work_stage') or 'UNKNOWN'} {class_of_tag('', _num(i.get('thickness_mm')))}"

TRACE_KEYS = {"trench": tr_trench, "pcc": tr_pcc, "brick_step": tr_brick_step, "mark": tr_mark, "beam_class": tr_beam_class, "wall_stage": tr_wall_stage}

def trace_terms(rows: list, family: str, key_name: str, cft_per_m3: float, family_of) -> list:
  fn = TRACE_KEYS[key_name]
  out = []
  for r in rows:
    if family_of(r) != family:
      continue
    i = _inputs(r)
    tag = i.get("tag") or ""
    key = fn(r, tag)
    qty_net = float(r.get("quantity_net") or r.get("quantity") or 0.0) * cft_per_m3
    if r.get("formula_code") == "PDF_TAKEOFF_LENGTH_X_HEIGHT_X_THICKNESS":
      length, width, height = (_num(i.get("length_m")) or 0.0) * 1000.0 / FT_MM, (_num(i.get("thickness_mm")) or 0.0) / FT_MM, (_num(i.get("height_mm")) or 0.0) / FT_MM
      steps = (r.get("trace") or {}).get("steps") or []
      whole = [float(st["m3"]) for st in steps if st.get("op") in ("net_volume", "net") and st.get("m3") is not None]
      share = (qty_net / cft_per_m3 / whole[-1]) if whole and whole[-1] > 0 else 1.0
      
      height = height * share
      gross = length * width * height
      out.append(term(key, 1.0, length, width, height, gross, (r.get("trace") or {}).get("label") or ""))
      kinds = {"openings": 0.0, "lintels": 0.0, "overlap": 0.0}
      thick_m = (_num(i.get("thickness_mm")) or 0.0) / 1000.0
      
      for st in steps:
        if st.get("op") == "deduction" and st.get("type") == "VOID_DEDUCTION":
          kinds["openings"] -= float(st.get("m2") or 0.0) * thick_m * cft_per_m3 * share
        elif st.get("op") == "deduction" and st.get("type") == "OVERLAP_ALLOCATION":
          kinds["overlap"] -= float(st.get("m3") or 0.0) * cft_per_m3 * share
        elif st.get("op") == "adjustment" and st.get("type") == "LESS":
          kinds["lintels"] -= float(st.get("m3") or 0.0) * cft_per_m3 * share
      other = (qty_net - gross) - sum(kinds.values())
      if abs(other) > 1e-3:
        kinds["other"] = other
      for kind, v in kinds.items():
        if abs(v) > 1e-12:
          out.append(term(key if kind == "overlap" else DED, 1.0, None, None, None, v, kind, True, kind))
    else:
      length, width, height = (_num(i.get("length_mm")) or 0.0) / FT_MM, (_num(i.get("width_mm")) or 0.0) / FT_MM, (_num(i.get("depth_mm")) or 0.0) / FT_MM
      nos = _ledger_nos(r)
      dims = nos * length * width * height
      out.append(term(key, nos, length, width, height, dims, (r.get("trace") or {}).get("label") or ""))
      if abs(qty_net - dims) > 1e-9:
        out.append(term(key, 1.0, None, None, None, qty_net - dims, "volume given to the member that shares it", True, "overlap"))
  return out

def trace_extents(rows: list, family: str, cft_per_m3: float, family_of) -> list:
  groups = {}
  for r in rows:
    if family_of(r) != family:
      continue
    i = _inputs(r)
    tag = i.get("tag") or ((r.get("trace") or {}).get("label") or "")[:40]
    g = groups.setdefault(tag, {"tag": tag, "rows": 0, "length_m": 0.0, "quantity": 0.0})
    g["rows"] += 1
    g["length_m"] += (_num(i.get("length_m")) or (_num(i.get("length_mm")) or 0.0) / 1000.0) * _ledger_nos(r)
    g["quantity"] += float(r.get("quantity_net") or r.get("quantity") or 0.0) * cft_per_m3
  return sorted(groups.values(), key=lambda g: -abs(g["quantity"]))

def qs_terms(ws, ranges: list, key_name: str) -> list:
  fn = QS_KEYS[key_name]
  
  out = []
  rows = [r for first, last in ranges for r in read_sheet(ws, first, last)]
  for r in rows:
    key, ded = fn(r)
    if ded:
      kind = "lintels" if "lintel" in r["desc"].lower() else ("openings" if (r["length"] is None or "opening" in r["desc"].lower() or re.match(r"[DWV]\d", r["remark"])) else "other")
      out.append(term(DED, 1.0, None, None, None, r["qty"], r["desc"] or r["remark"], True, kind))
      continue
    out.append(term(key, r["nos"], r["length"], r["width"] if r["width"] is not None else 1.0, r["height"] if r["height"] is not None else 1.0, r["qty"], r["desc"] or r["remark"], False))
  return out

def factors(terms: list, count_on: bool) -> dict:
  n = sum(t["nos"] for t in terms)
  e = sum(t["nos"] * t["length"] for t in terms)
  a = sum(t["nos"] * t["length"] * t["width"] for t in terms)
  v = sum(volume(t) for t in terms)
  if e == 0 or a == 0:
    return {"count": n if count_on else 1.0, "length": 0.0, "width": 0.0, "height": 0.0, "volume": v}
  count = n if count_on else 1.0
  return {"count": count, "length": e / count, "width": a / e, "height": v / a, "volume": v}

def split(side: list) -> tuple:
  gross, ded = {}, []
  for t in side:
    if t["deduction"]:
      ded.append(t)
    else:
      gross.setdefault(t["key"], []).append(t)
  return gross, ded

def decompose(trace: list, qs: list, count_on: bool) -> dict:
  tg, td = split(trace)
  qg, qd = split(qs)
  parts, per_key = [], {}
  
  def add(kind, key, value):
    if abs(value) > 1e-12:
      parts.append({"part": kind, "key": key, "value": value})
      per_key.setdefault(key, {})[kind] = per_key.setdefault(key, {}).get(kind, 0.0) + value
  for key in sorted(set(tg) | set(qg)):
    ft = factors(tg[key], count_on) if key in tg else None
    fq = factors(qg[key], count_on) if key in qg else None
    if ft is None:
      add("only_qs", key, -fq["volume"])
      add("rows_vs_dims", key, -(sum(t["qty"] for t in qg[key]) - fq["volume"]))
      continue
    if fq is None:
      add("only_trace", key, ft["volume"])
      add("rows_vs_dims", key, sum(t["qty"] for t in tg[key]) - ft["volume"])
      continue
    add("count", key, (ft["count"] - fq["count"]) * fq["length"] * fq["width"] * fq["height"])
    add("length", key, ft["count"] * (ft["length"] - fq["length"]) * fq["width"] * fq["height"])
    add("width", key, ft["count"] * ft["length"] * (ft["width"] - fq["width"]) * fq["height"])
    add("height", key, ft["count"] * ft["length"] * ft["width"] * (ft["height"] - fq["height"]))
    add("rows_vs_dims", key, (sum(t["qty"] for t in tg[key]) - ft["volume"]) - (sum(t["qty"] for t in qg[key]) - fq["volume"]))
    
  keys = {(t["kind"], t["key"]) for t in td + qd}
  for kind, key in sorted(keys, key=lambda k: (k[0] or "", k[1])):
    dt = sum(t["qty"] for t in td if t["kind"] == kind and t["key"] == key)
    dq = sum(t["qty"] for t in qd if t["kind"] == kind and t["key"] == key)
    add(kind or "other", key, dt - dq)
  dt, dq = sum(t["qty"] for t in td), sum(t["qty"] for t in qd)
  return {"parts": parts, "per_key": per_key, "trace_deduction": dt, "qs_deduction": dq,
    "trace_sum": sum(t["qty"] for t in trace), "qs_sum": sum(t["qty"] for t in qs)}

def explain(line: dict, spec: dict, ws, rows: list, cft_per_m3: float, family_of) -> dict:
  family = spec.get("family") or line["key"].split("/")[0]
  trace = trace_terms(rows, family, spec["trace_key"], cft_per_m3, family_of)
  ranges = spec["rows"] if isinstance(spec["rows"][0], list) else [spec["rows"]]
  qs = qs_terms(ws, ranges, spec["qs_key"])
  d = decompose(trace, qs, bool(spec.get("count", True)))
  gap = float(line["trace"]) - float(line["qs"])
  attributed = sum(p["value"] for p in d["parts"])
  unattributed = gap - attributed
  
  groups = {}
  for p in d["parts"]:
    g = GROUP_OF[p["part"]]
    groups[g] = groups.get(g, 0.0) + p["value"]
  return {"line": line["key"], "unit": line["unit"], "qs": line["qs"], "trace": line["trace"], "gap": gap, "gap_pct": (gap / line["qs"] * 100.0) if line["qs"] else None,
    "groups": groups, "parts": d["parts"], "per_key": d["per_key"], "attributed": attributed, "unattributed": unattributed,
    "unattributed_pct_of_gap": (abs(unattributed) / abs(gap) * 100.0) if gap else 0.0,
    "trace_rows_sum": d["trace_sum"], "qs_rows_sum": d["qs_sum"], "trace_deduction": d["trace_deduction"], "qs_deduction": d["qs_deduction"],
    "terms": {"trace": len(trace), "qs": len(qs)}, "note": spec.get("note") or ""}

def render(e: dict) -> str:
  u = e["unit"]
  out = [f"### {e['line']}  (QS {e['qs']:,.1f} {u}, Trace {e['trace']:,.1f} {u}, gap {e['gap']:+,.1f} {u}" + (f", {e['gap_pct']:+.1f}%" if e["gap_pct"] is not None else "") + ")\n"]
  out.append("| Part | " + u + " | Share of gap |\n|---|---|---|")
  for g in GROUPS:
    v = e["groups"].get(g, 0.0)
    out.append(f"| {g.replace('_', ' ')} | {v:+,.2f} | {v / e['gap'] * 100:+.0f}% |" if e["gap"] else f"| {g} | {v:+,.2f} | |")
  out.append(f"| not attributed | {e['unattributed']:+,.2f} | {e['unattributed'] / e['gap'] * 100:+.0f}% |" if e["gap"] else f"| not attributed | {e['unattributed']:+,.2f} | |")
  out.append("\n| Key | " + " | ".join(PART_ORDER) + " | Total |\n|---|" + "---|" * (len(PART_ORDER) + 1))
  
  for key, parts in sorted(e["per_key"].items(), key=lambda kv: -abs(sum(kv[1].values()))):
    out.append(f"| {key} | " + " | ".join((f"{parts[p]:+.1f}" if p in parts else "") for p in PART_ORDER) + f" | {sum(parts.values()):+.1f} |")
  out.append(f"\nTrace rows add to {e['trace_rows_sum']:,.1f} (gross {e['trace_rows_sum'] - e['trace_deduction']:,.1f}, deductions {e['trace_deduction']:+,.1f}), workbook rows to {e['qs_rows_sum']:,.1f} (gross {e['qs_rows_sum'] - e['qs_deduction']:,.1f}, deductions {e['qs_deduction']:+,.1f}).")
  if e["note"]:
    out.append("\n" + e["note"])
  return "\n".join(out) + "\n"

def residual_text(e: dict) -> str:
  bits = []
  for g, label in (("extent", "extent"), ("height_or_thickness", "width or height"), ("deductions", "deductions"), ("convention", "overlap rule"), ("typed_totals", "typed totals")):
    v = e["groups"].get(g, 0.0)
    if abs(v) >= 0.5:
      bits.append(f"{label} {v:+,.1f}")
  if abs(e["unattributed"]) >= 0.5:
    bits.append(f"not attributed {e['unattributed']:+,.1f}")
  return f"{e['gap_pct']:+.1f}% ({e['gap']:+,.1f} {e['unit']}): " + ", ".join(bits)

def _load(case_dir: str) -> dict:
  p = os.path.join(case_dir, "explain.yaml")
  if not os.path.isfile(p):
    return {}
  with open(p, encoding="utf-8") as fh:
    return yaml.safe_load(fh) or {}

def run(case: str, line: str | None, out_dir: str, cases_dir: str | None = None) -> dict:
  import openpyxl
  from app.modules.drawings_boq.takeoff.proof import case_io as CIO
  from app.modules.drawings_boq.takeoff.proof import score as SC
  from app.modules.drawings_boq.lab.aliases import cft_per_m3
  here = os.path.join(CIO.HERE, case)
  cfg = _load(here)
  score_json, ledger_json = (os.path.join(out_dir, case, f) for f in ("score.json", "ledger.json"))
  if not (os.path.isfile(score_json) and os.path.isfile(ledger_json)):
    SC.main([case, "--no-other", "--dump", "--out", out_dir] + (["--cases-dir", cases_dir] if cases_dir else []))
  with open(score_json, encoding="utf-8") as fh:
    score = json.load(fh)
  with open(ledger_json, encoding="utf-8") as fh:
    rows = json.load(fh)
    
  lines = {l["key"]: l for l in score["lines"]}
  wanted = [line] if line else [k for k, l in lines.items() if l.get("diff_pct_qs") is not None and abs(l["diff_pct_qs"]) > 5.0]
  wb_name = cfg.get("workbook")
  base = CIO.cases_dir(cases_dir)
  workbook = openpyxl.load_workbook(os.path.join(base, wb_name), data_only=True) if wb_name and base and os.path.isfile(os.path.join(base, wb_name)) else None
  result = {"case": case, "lines": [], "not_explained": []}
  
  c = cft_per_m3()
  for key in wanted:
    if key not in lines:
      result["not_explained"].append({"line": key, "why": "the score has no such line"})
      continue
    spec = (cfg.get("lines") or {}).get(key)
    if spec is None or workbook is None:
      why = (spec or {}).get("why") or ("no row build-up for this line is described in explain.yaml" if workbook else "this case has no workbook with row build-up (explain.yaml names none); the QS workbook holds quantities only")
      result["not_explained"].append({"line": key, "why": why, "trace_extents": trace_extents(rows, key.split("/")[0], c, SC.family_of)})
      continue
    if spec.get("why"):
      result["not_explained"].append({"line": key, "why": spec["why"]})
      continue
    result["lines"].append(explain(lines[key], spec, workbook[spec["sheet"]], rows, c, SC.family_of))
    
  return result

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Split the gap between Trace and the QS for one line into extent, width or height, deductions and typed totals.")
  ap.add_argument("case")
  ap.add_argument("line", nargs="?", help="line key such as BRICK_WALLS; default: every line more than 5% away from the QS")
  ap.add_argument("--out", default="explain_out", help="folder for the score.json and ledger.json this reads (the score runs if they are not there)")
  ap.add_argument("--cases-dir")
  ap.add_argument("--json", dest="json_path")
  a = ap.parse_args(argv)
  res = run(a.case, a.line, a.out, a.cases_dir)
  print(f"# Line breakdown: {res['case']}\n")
  
  for e in res["lines"]:
    print(render(e))
  for n in res["not_explained"]:
    print(f"### {n['line']}\n\nNot split: {n['why']}\n")
    ext = n.get("trace_extents") or []
    if ext:
      print("| Trace tag | Rows | Run (m) | Quantity |\n|---|---|---|---|")
      for g in ext[:8]:
        print(f"| {g['tag']} | {g['rows']} | {g['length_m']:,.1f} | {g['quantity']:,.1f} |")
      print()
      
  print("Residual text:\n")
  for e in res["lines"]:
    print(f"- {e['line']}: {residual_text(e)}")
  if a.json_path:
    with open(a.json_path, "w", encoding="utf-8") as fh:
      json.dump(res, fh, indent=1, default=str)
  return 0

if __name__ == "__main__":
  sys.exit(main())
