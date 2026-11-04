from __future__ import annotations
import hashlib
import json
import os
from decimal import Decimal as D
import yaml
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.rebar import bbs_layouts as BBS
from app.modules.drawings_boq.rebar import member_source as MS
from app.modules.drawings_boq.rebar import expect_source as ES
from app.modules.drawings_boq.rebar import bbs_report as BR
from app.modules.drawings_boq.rebar import bbs_audit as AUD
from app.modules.drawings_boq.rebar import bbs_crosscheck as XC
from app.modules.drawings_boq.rebar import bbs_decisions as DEC
from app.modules.drawings_boq.rebar import member_match as MM
from app.modules.drawings_boq.takeoff.proof import case as CASE

KIND = CIO.AUDIT_KIND
CLASS = "BBS_FINDING"
EXPECTED = "expected_findings.yaml"
DECISIONS = "decisions.yaml"
READS = "reads"
BBS_READ = "bbs_read.json"
STRUCTURE_READ = "structure_read.json"
OK, WRONG, MISSED, MISSED_KNOWN, INV_FLAGGED, INV_SILENT, TRUE = "MATCHED_OK", "MATCHED_WRONG_VALUE", "MISSED_SILENT", "MISSED_REPORTED", "INVENTED_FLAGGED", "INVENTED_SILENT", "TRUE"
ANY = "*"
ROW_FIELDS = ("page", "sheet", "member", "sr", "description", "dia", "spacing_in", "members", "each", "total", "cut_ft", "total_ft", "unit_kg_ft", "total_kg")

def audit_cases(root: str = CIO.HERE) -> list:
  return [n for n in CIO.list_cases(root, audit=True) if CIO.is_audit_case(os.path.join(root, n))]

def pdf_in(folder: str, cases_dir: str | None) -> str | None:
  files = CIO.cases_dir(cases_dir)
  raw = _yaml(os.path.join(folder, "case.yaml")) or {}
  for name in raw.get("pdfs") or []:
    path = os.path.join(files, name) if files else None
    if path and os.path.isfile(path) and (not (raw.get("sha256") or {}).get(name) or CASE.sha256_of(path) == raw["sha256"][name]):
      return path
  return None

def gate_case(name: str, cases_dir: str | None = None, root: str = CIO.HERE) -> tuple:
  folder = os.path.join(root, name)
  return gate(folder, pdf_in(folder, cases_dir))

def norm(text) -> str:
  return "".join(ch for ch in str(text or "").upper() if ch.isalnum())

def _yaml(path: str):
  with open(path, encoding="utf-8") as fh:
    return yaml.safe_load(fh)

def _classes(value, where: str) -> tuple:
  items = value if isinstance(value, list) else [value]
  if not items or any(not isinstance(c, str) or c not in BR.CLASS_RANK for c in items):
    raise ValueError(f"{where}: class is one of {', '.join(BR.CLASS_RANK)} (or a list of them)")
  return tuple(items)

def load_expected(folder: str) -> dict:
  path = os.path.join(folder, EXPECTED)
  doc = _yaml(path) if os.path.isfile(path) else None
  if not isinstance(doc, dict) or not isinstance(doc.get("findings"), list) or not doc["findings"]:
    raise ValueError(f"{path} must hold `findings`, a list of items.")
  
  items, seen = [], set()
  for i, e in enumerate(doc["findings"], 1):
    if not isinstance(e, dict) or not isinstance(e.get("item"), int) or not e.get("title"):
      raise ValueError(f"{path}, entry {i}: each item needs `item` (a number) and `title`.")
    if e["item"] in seen:
      raise ValueError(f"{path}: item {e['item']} is listed twice.")
    seen.add(e["item"])
    raises = e.get("raises")
    if not isinstance(raises, list) or not raises:
      raise ValueError(f"{path}, item {e['item']}: `raises` is a list of what the audit must raise.")
    clean = []
    
    for j, r in enumerate(raises, 1):
      where = f"{path}, item {e['item']}, raise {j}"
      if not isinstance(r, dict) or not r.get("code"):
        raise ValueError(f"{where}: needs `code`, `class`, `member` and `floor`.")
      for name in r:
        if name not in ("code", "class", "member", "floor", "count"):
          raise ValueError(f"{where}: unknown field {name}; allowed: code, class, member, floor, count. A weight does not belong here.")
      count = r.get("count", 1)
      if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ValueError(f"{where}: count is a whole number of at least 1 (the least that must be raised).")
      clean.append({"code": str(r["code"]), "classes": _classes(r.get("class"), where), "member": None if r.get("member") is None else str(r["member"]), "floor": r.get("floor"), "count": count})
    if e.get("gap") is not None and not (isinstance(e["gap"], str) and e["gap"].strip()):
      raise ValueError(f"{path}, item {e['item']}: `gap` is the reason this item is not raised as the build file says.")
    items.append({"item": e["item"], "title": str(e["title"]), "raises": clean, "gap": e.get("gap"), "note": e.get("note")})
  held = []
  
  for i, e in enumerate(doc.get("accepted_errors") or [], 1):
    if not isinstance(e, dict) or not e.get("code") or not e.get("reason"):
      raise ValueError(f"{path}, accepted_errors {i}: needs `code`, `member`, `floor` and a `reason`.")
    held.append({"code": str(e["code"]), "member": None if e.get("member") is None else str(e["member"]), "floor": e.get("floor"), "reason": str(e["reason"])})
  return {"items": items, "accepted_errors": held}

def load_decisions(folder: str) -> dict:
  path = os.path.join(folder, DECISIONS)
  doc = _yaml(path) if os.path.isfile(path) else None
  if not isinstance(doc, dict):
    raise ValueError(f"{path} must be a table of decisions (bbs_floor_map, stock_length_ft, tie_zones, curtail_extras, ...).")
  out = {}
  for key, value in doc.items():
    try:
      out[str(key)] = DEC.clean(str(key), value)
    except ValueError as e:
      raise ValueError(f"{path}, {key}: {e}")
  return out

def _dd(v):
  return None if v is None else D(v)

def snapshot_document(j: dict) -> BBS.BbsDocument:
  doc = BBS.BbsDocument(title=j["title"], pages=j["pages"], profile=j["profile"], page_counters=[tuple(x) for x in j["page_counters"]])
  doc.sheets = [BBS.BbsSheet(index=s["index"], name=s["name"], first_page=s["first_page"], last_page=s["last_page"], printed_total_kg=_dd(s["printed_total_kg"]),
    dia_totals_kg={k: D(v) for k, v in s["dia_totals_kg"].items()}) for s in j["sheets"]]
  doc.rows = [BBS.BbsRow(page=r["page"], y=r["y"], sheet=r["sheet"], member=r["member"], sr=r["sr"], description=r["description"], dia=r["dia"], spacing_in=_dd(r["spacing_in"]),
    members=_dd(r["members"]), each=_dd(r["each"]), total=_dd(r["total"]), cut_ft=_dd(r["cut_ft"]), total_ft=_dd(r["total_ft"]), unit_kg_ft=_dd(r["unit_kg_ft"]),
    total_kg=_dd(r["total_kg"]), parts=[D(p) for p in r["parts"]], notes=r["notes"], issues=r["issues"]) for r in j["rows"]]
  return doc

def rows_digest(rows: list) -> str:
  h = hashlib.sha256()
  for r in rows:
    h.update(json.dumps([None if getattr(r, k) is None else str(getattr(r, k)) for k in ROW_FIELDS], sort_keys=True).encode())
  return h.hexdigest()

def read_drift(doc: BBS.BbsDocument, pdf_path: str) -> str | None:
  with open(pdf_path, "rb") as fh:
    fresh = BBS.read_bbs_pdf(fh.read())
  if len(fresh.rows) != len(doc.rows):
    return f"the reader now gives {len(fresh.rows)} rows, the snapshot has {len(doc.rows)}"
  if rows_digest(fresh.rows) != rows_digest(doc.rows):
    bad = next(i for i, (a, b) in enumerate(zip(fresh.rows, doc.rows), 1) if rows_digest([a]) != rows_digest([b]))
    return f"the reader's rows differ from the snapshot's, the first at row {bad}"
  return None

def _finding_dict(f, i: int) -> dict:
  return {"id": str(i), "code": f.code, "finding_class": f.finding_class, "rule": f.rule, "bbs_ref": f.bbs_ref, "drawing_ref": getattr(f, "drawing_ref", None), "effect_basis": getattr(f, "effect_basis", None),
    "convention": getattr(f, "convention", None), "bbs_value": f.bbs_value, "trace_value": f.trace_value, "diff_kg": f.diff_kg, "diff_pct": f.diff_pct, "confidence": f.confidence,
    "question": f.question, "status": "OPEN", "reason": None}

def run_audit(folder: str) -> dict:
  reads = os.path.join(folder, READS)
  with open(os.path.join(reads, BBS_READ), encoding="utf-8") as fh:
    doc = snapshot_document(json.load(fh))
  with open(os.path.join(reads, STRUCTURE_READ), encoding="utf-8") as fh:
    data = json.load(fh)
  decisions = load_decisions(folder)
  expect = {k: v for k, v in decisions.items() if k in DEC.EXPECT_KEYS}
  names = {s.index: s.name for s in doc.sheets}
  cands = {(k.split("|")[0], int(k.split("|")[1])): v for k, v in data["candidates"].items()}
  jobs = ES.build_jobs(data["sheets"], cands, expect, [s.name for s in doc.sheets])
  results = ES.run_jobs(jobs)
  members = MS.collapse(MS.members_from_sheets(data["sheets"], cands))
  
  for job, _e in results:
    if job.get("decision_only") and job["cls"] != "SLAB":
      members.append(MS.DrawingMember("", 0, job["cls"], job["mark"], job["floor"], 1, "DECISION"))
  match = MM.match_rows(doc.rows, names, members, decisions)
  cross = XC.crosscheck(doc.rows, names, match, results, members, expect, XC.load_cross_bands(), XC.drawing_refs(data["sheets"]), XC.size_conflicts(data["sheets"], doc.rows, match, names))
  l1 = AUD.run_l1(doc, AUD.load_bands(), None, None)
  found = list(l1.findings) + list(cross.findings)
  rows = [{"row_no": i, "sheet": r.sheet, **{k: getattr(r, k) for k in ("page", "y", "member", "sr", "description", "dia", "spacing_in", "members", "each", "total", "cut_ft", "total_ft", "unit_kg_ft", "total_kg")}}
    for i, r in enumerate(doc.rows, start=1)]
  sheets = [{"idx": s.index, "name": s.name, "first_page": s.first_page, "last_page": s.last_page, "printed_total_kg": s.printed_total_kg} for s in doc.sheets]
  findings = BR.sort_findings([_finding_dict(f, i) for i, f in enumerate(found, 1)])
  floor_map = {k: list(v) for k, v in (decisions.get("bbs_floor_map") or match.floor_map or {}).items()}
  return {"document": doc, "rows": rows, "sheets": sheets, "findings": findings, "floor_map": floor_map, "decisions": decisions, "summary": BR.summarize(rows, sheets, findings)}

def floor_of(f: dict, floor_map: dict) -> str | None:
  floors = floor_map.get((f.get("bbs_ref") or {}).get("sheet_name") or "")
  return floors[0] if floors else None

def key_of(code, member, floor) -> tuple:
  return (str(code), ANY if member == ANY else norm(member), None if floor is None else str(floor).upper())

def raised_keys(findings: list, floor_map: dict) -> dict:
  out: dict = {}
  for f in findings:
    out.setdefault(key_of(f["code"], (f.get("bbs_ref") or {}).get("member"), floor_of(f, floor_map)), []).append(f)
  return out

def _matches(entry_key: tuple, raised: dict) -> list:
  code, member, floor = entry_key
  if member == ANY:
    return [f for k, fs in raised.items() if k[0] == code for f in fs]
  return list(raised.get((code, member, floor), []))

def judge(expected: dict, audit: dict) -> dict:
  findings, floor_map = audit["findings"], audit["floor_map"]
  raised = raised_keys(findings, floor_map)
  named: set = set()
  
  verdicts, stale_gaps = [], []
  for item in expected["items"]:
    for r in item["raises"]:
      k = key_of(r["code"], r["member"], r["floor"])
      hits = _matches(k, raised)
      named.update(id(f) for f in hits)
      right = [f for f in hits if f["finding_class"] in r["classes"]]
      if len(right) >= r["count"]:
        verdict, why = OK, None
      elif not hits:
        verdict, why = MISSED, "not raised"
      else:
        verdict, why = WRONG, f"raised as {', '.join(sorted({f['finding_class'] for f in hits}))}, expected {' or '.join(r['classes'])}" if not right else f"raised {len(right)} of {r['count']} as {r['classes'][0]}"
      verdicts.append({"item": item["item"], "code": r["code"], "member": r["member"], "floor": r["floor"], "classes": r["classes"], "verdict": verdict, "why": why, "gap": item["gap"], "raised": len(hits)})
    if item["gap"] and all(v["verdict"] == OK for v in verdicts if v["item"] == item["item"]):
      stale_gaps.append(item["item"])
      
  by_item = set(named)
  held = {key_of(h["code"], h["member"], h["floor"]): h for h in expected["accepted_errors"]}
  for k in held:
    named.update(id(f) for f in _matches(k, raised) if f["finding_class"] == "ERROR")
  outside = [f for f in findings if f["finding_class"] == "ERROR" and id(f) not in named]
  held_stale = [h for k, h in held.items() if not any(f["finding_class"] == "ERROR" for f in _matches(k, raised))]
  held_hits = [f for k in held for f in _matches(k, raised) if f["finding_class"] == "ERROR"]
  return {"verdicts": verdicts, "outside": outside, "held_stale": held_stale, "held_hits": held_hits, "stale_gaps": stale_gaps, "raised": raised, "by_item": by_item}

def reconcile(audit: dict, tol_kg=D("1"), tol_share=D("0.001")) -> list:
  bad = []
  s = audit["summary"]
  for sh in s["sheets"]:
    if sh["printed_total_kg"] is None:
      bad.append(f"{sh['name']} (pages {sh['first_page']} to {sh['last_page']}) prints no total")
    elif abs(sh["printed_diff_kg"]) > max(tol_kg, tol_share * sh["printed_total_kg"]):
      bad.append(f"{sh['name']} (pages {sh['first_page']} to {sh['last_page']}): recomputed {sh['computed_kg']}, printed {sh['printed_total_kg']}")
  if abs(sum((sh["effect_kg"] for sh in s["sheets"]), D(0)) + s["unassigned"]["effect_kg"] - s["diff_kg"]) > D("0.05"):
    bad.append("the sheets' effects plus the unassigned effect do not add to the total effect")
  return bad

def gate(folder: str, pdf_path: str | None = None) -> tuple:
  try:
    expected = load_expected(folder)
    audit = run_audit(folder)
  except (ValueError, OSError, KeyError) as e:
    return False, str(e)
  j = judge(expected, audit)
  
  bad: list = []
  gaps = [v for v in j["verdicts"] if v["gap"] and v["verdict"] != OK]
  for v in j["verdicts"]:
    if v["verdict"] != OK and not v["gap"]:
      bad.append(f"item {v['item']}: {v['code']} {v['member'] or ''} {v['floor'] or ''} {v['why']}".replace("  ", " ").strip())
  for n in j["stale_gaps"]:
    bad.append(f"item {n} is listed as a gap but is now raised as the build file says; remove its `gap`")
  if j["outside"]:
    bad.append(f"{len(j['outside'])} ERROR(s) outside the list: " + "; ".join(sorted({f"{f['code']} {(f.get('bbs_ref') or {}).get('member')}" for f in j["outside"]})[:6]))
  for h in j["held_stale"]:
    bad.append(f"held ERROR {h['code']} {h['member'] or ''} is no longer raised; remove it from accepted_errors")
  bad += [f"sheet does not reconcile: {x}" for x in reconcile(audit)]
  if pdf_path:
    if os.path.isfile(pdf_path):
      drift = read_drift(audit["document"], pdf_path)
      if drift:
        bad.append("reader drift: " + drift)
        
  n_items = len(expected["items"])
  ok_items = sum(1 for it in expected["items"] if all(v["verdict"] == OK for v in j["verdicts"] if v["item"] == it["item"]))
  if bad:
    return False, "; ".join(bad)
  note = f"{ok_items} of {n_items} items raised with their class; {len(audit['rows'])} rows, {len(audit['sheets'])} sheets reconcile; {len(j['held_hits'])} held ERROR(s), none outside the list"
  if gaps:
    note += "; known gaps: " + ", ".join(sorted({f"item {v['item']}" for v in gaps}))
  note += "; reader " + ("same as the snapshot" if pdf_path and os.path.isfile(pdf_path) else "not compared (PDF not in the folder)")
  return True, note

def outcomes(key: str, alias: str, split: str, folder: str) -> list:
  expected = load_expected(folder)
  audit = run_audit(folder)
  j = judge(expected, audit)
  out = []
  for n, v in enumerate(j["verdicts"], 1):
    out.append({"id": f"{key}:BBS:{v['item']}:{v['code']}:{norm(v['member']) or '-'}:{v['floor'] or '-'}", "set": alias, "split": split, "class": CLASS, "sheet": None, "side": "truth",
      "outcome": MISSED_KNOWN if v["verdict"] == MISSED and v["gap"] else v["verdict"], "mark": v["member"], "detail": v["why"]})
    
  seen: dict = {}
  for f in audit["findings"]:
    if f["finding_class"] != "ERROR":
      continue
    member = (f.get("bbs_ref") or {}).get("member")
    k = key_of(f["code"], member, floor_of(f, audit["floor_map"]))
    verdict = TRUE if id(f) in j["by_item"] else (INV_SILENT if f in j["outside"] else INV_FLAGGED)
    n = seen[k] = seen.get(k, 0) + 1
    out.append({"id": f"{key}:BBSRD:{k[0]}:{k[1] or '-'}:{k[2] or '-'}:{n}", "set": alias, "split": split, "class": CLASS, "sheet": None, "side": "read", "outcome": verdict, "mark": member, "detail": f["rule"][:120]})
  return out

def metrics(rows: list) -> dict:
  truth = [o for o in rows if o["side"] == "truth"]
  read = [o for o in rows if o["side"] == "read"]
  raised = sum(1 for o in truth if o["outcome"] in (OK, WRONG))
  right = sum(1 for o in truth if o["outcome"] == OK)
  false = sum(1 for o in read if o["outcome"] in (INV_FLAGGED, INV_SILENT))
  silent = sum(1 for o in read if o["outcome"] == INV_SILENT)
  return {"expected": len(truth), "raised": raised, "recall": None if not truth else round(raised / len(truth), 4), "class_accuracy": None if not raised else round(right / raised, 4),
    "errors_raised": len(read), "errors_outside_items": false, "errors_silent": silent, "false_error_rate": None if not read else round(false / len(read), 4)}

def main(argv: list | None = None) -> int:
  import argparse
  ap = argparse.ArgumentParser(description="Gate 15: the bar schedule audit against the findings the build file says it must raise.")
  ap.add_argument("--cases-dir", help="the folder with the case PDFs (default: TRACE_CASES_DIR); without the schedule PDF the reader is not compared")
  args = ap.parse_args(argv)
  bad = 0
  for name in audit_cases():
    ok, note = gate_case(name, args.cases_dir)
    print(f"{'ok  ' if ok else 'FAIL'}  bbs audit {name} (gate 15)   {note}")
    bad += 0 if ok else 1
  return 1 if bad else 0

if __name__ == "__main__":
  raise SystemExit(main())
