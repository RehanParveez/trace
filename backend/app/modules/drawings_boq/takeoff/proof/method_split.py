from __future__ import annotations
import argparse
import json
import os
import re
import sys
import time
from app.engine.catalogue import methods_qs as MQ

READ, METHOD, FACT, WORKBOOK = "READ", "METHOD", "FACT", "WORKBOOK"
UNSOURCED = "METHOD_WITHOUT_SOURCE"
SUSPECT = re.compile(r"\bhis (choice|convention|conventions|own method)\b", re.I)

def read_part(amount, cause) -> dict:
  text = cause or "not diagnosed"
  part = {"part": READ, "amount": amount, "text": text}
  if SUSPECT.search(text):
    part["method_suspected"] = True
  return part

def _same(a, b) -> bool:
  if isinstance(a, dict) or isinstance(b, dict):
    return isinstance(a, dict) and isinstance(b, dict) and a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
  try:
    return abs(float(a) - float(b)) <= 1e-9
  except (TypeError, ValueError):
    return str(a).strip().upper() == str(b).strip().upper()

def classify_rows(rows: list) -> dict:
  out = {METHOD: [], FACT: [], "CHOICE": [], "problems": []}
  for r in rows:
    key, scope = r["key"], dict(r.get("scope") or {})
    kind = MQ.kind_of(key)
    if kind is None:
      out["problems"].append(f"{key}: the method file does not say whether this is a QS method, a fact of the building or a project choice")
      out[FACT].append(r)
      
    elif kind == MQ.METHOD:
      m = MQ.method_for(key, scope)
      if m is None:
        out["problems"].append(f"{key} {scope or ''}: {UNSOURCED}: no method of that scope is in the method file")
      elif not (_same(m["rule"]["value"], r["value"]) or any(_same(a["value"], r["value"]) for a in m.get("also_seen") or [])):
        out["problems"].append(f"{key} {scope or ''}: {UNSOURCED}: the case holds {r['value']!r}, the method file {m['rule']['value']!r}, and no other figure of his is listed")
      out[METHOD].append(r)
    elif kind == MQ.FACT:
      out[FACT].append(r)
    else:
      out["CHOICE"].append(r)
  return out

def pct(a, b):
  return None if a is None or b in (None, 0) else (a - b) / b * 100.0

def workbook_marks(case: dict, answers: dict | None, lines: list) -> dict:
  marks: dict = {}
  
  def add(key, why):
    marks.setdefault(key, [])
    if why not in marks[key]:
      marks[key].append(why)
      
  for l in lines:
    if l.get("kind") == "QS_ERROR" or l.get("class") == "QS_ERROR":
      add(l["key"], "expected.yaml lists it as a QS error")
  for c in case.get("corrections") or []:
    if c.get("signed") and c.get("evidence"):
      add(c["line"], f"signed correction {c['qs_figure']:g} to {c['corrected']:g}: {c['reason'][:100]}")
      
  if answers:
    from app.modules.drawings_boq.takeoff.proof.answers import answers as ANS
    bad = answers.get("totals_check") or []
    for it in answers.get("items") or []:
      for b in bad:
        if it.get("sheet") != b["sheet"] or not _rows_overlap(str(it.get("rows") or ""), str(b["rows"])):
          continue
        fam = ANS.ledger_line(it["element"], it.get("unit"))
        if fam:
          add(f"{fam}/{it.get('floor') or 'ALL'}", f"the rows of sheet {b['sheet']} ({b['rows']}) add to {b['summed']:.4g} and the workbook's own total says {b['workbook']:.4g}")
  return {k: v for k, v in marks.items() if any(l["key"] == k for l in lines)}

def _rows_overlap(item_rows: str, block: str) -> bool:
  def spans(text):
    out = []
    for part in text.replace(" ", "").split(","):
      if not part:
        continue
      a, _, b = part.partition("-")
      try:
        out.append((int(a), int(b or a)))
      except ValueError:
        continue
    return out
  return any(x[0] <= y[1] and y[0] <= x[1] for x in spans(item_rows) for y in spans(block))

def split_line(s: dict, f: dict | None, m: dict | None, marks: dict, correction: dict | None, residual: dict | None) -> dict:
  q = (m or s).get("qs")
  tol = (m or s).get("tolerance_pct")
  ts, tf, tm = (x.get("trace") if x else None for x in (s, f, m))
  fact = None if ts is None or tf is None else tf - ts
  method = None if tf is None or tm is None else tm - tf
  left = None if tm is None or q is None else tm - q
  corrected = correction["corrected"] if correction else None
  
  out = {"key": (m or s)["key"], "item": (m or s).get("item"), "unit": (m or s).get("unit"), "qs": q, "tolerance_pct": tol, "trace_default": ts, "trace_with_facts": tf, "trace_with_method": tm,
    "diff_pct_default": pct(ts, q), "diff_pct": pct(tm, q), "fact": fact, "method": method, "left": left, "status": (m or s).get("status")}
  if q is None or tm is None:
    out["verdict"] = "NO_NUMBER"
    out["parts"] = [{"part": READ, "text": (m or s).get("why") or "Trace has no number for this line"}] if tm is None else []
    return out
  within = abs(pct(tm, q)) <= (tol or 10.0)
  out["within"] = within
  
  parts = []
  if fact:
    parts.append({"part": FACT, "amount": fact, "text": "typed from the workbook for this building, not a QS method"})
  if method:
    parts.append({"part": METHOD, "amount": method, "text": "the QS's way of measuring, from the same reading"})
  why = marks.get(out["key"])
  if why:
    out["workbook"] = why
    if corrected is not None:
      parts.append({"part": WORKBOOK, "amount": corrected - q, "text": "; ".join(why)})
      rest = tm - corrected
      out["left_after_workbook"] = rest
      if abs(pct(tm, corrected) or 0.0) > (tol or 10.0):
        parts.append(read_part(rest, (residual or {}).get("cause")))
    else:
      parts.append({"part": WORKBOOK, "amount": left, "text": "; ".join(why)})
  elif not within:
    parts.append(read_part(left, (residual or {}).get("cause")))
  out["parts"] = parts
  out["verdict"] = "WORKBOOK" if why else "WITHIN" if within else "SPLIT"
  return out

def summarise(rows: list) -> dict:
  numbered = [r for r in rows if r["verdict"] != "NO_NUMBER"]
  wb = [r for r in numbered if r["verdict"] == "WORKBOOK"]
  read = [r for r in numbered if r["verdict"] != "WORKBOOK"]
  
  def inside(rs, field):
    return sum(1 for r in rs if r.get(field) is not None and abs(r[field]) <= (r["tolerance_pct"] or 10.0))
  return {"lines": len(rows), "with_a_number": len(numbered), "no_number": len(rows) - len(numbered),
    "within_tolerance_default": inside(numbered, "diff_pct_default"), "within_tolerance_with_methods": inside(numbered, "diff_pct"),
    "moved_by_facts": sum(1 for r in numbered if r["fact"]), "moved_by_methods": sum(1 for r in numbered if r["method"]),
    "workbook_lines": len(wb), "read_lines": len(read), "read_within_tolerance": inside(read, "diff_pct"),
    "split_lines": sum(1 for r in numbered if r["verdict"] == "SPLIT"), "method_suspected": sum(1 for r in numbered if any(p.get("method_suspected") for p in r["parts"])),
    "unexplained": sum(1 for r in numbered if any(p["part"] == READ and p["text"].startswith("not diagnosed") for p in r["parts"]))}

def line_map(doc: dict) -> dict:
  return {l["key"]: {**l, **{f: (round(l[f], 3) if isinstance(l.get(f), (int, float)) else l.get(f)) for f in ("trace", "qs")}} for l in doc.get("lines") or []}

def split_case(case: dict, docs: dict, rows_by_kind: dict) -> dict:
  s, f, m = (line_map(docs[k]) for k in ("default", "facts", "method"))
  marks = workbook_marks(case, answers_raw(case), list(m.values()))
  corr = {c["line"]: c for c in case.get("corrections") or [] if c.get("signed")}
  res = {r["line"]: r for r in case.get("residuals") or []}
  keys = [k for k in m] + [k for k in s if k not in m]
  rows = [split_line(s.get(k) or m.get(k), f.get(k), m.get(k), marks, corr.get(k), res.get(k)) for k in keys if (m.get(k) or s.get(k)).get("status") not in ("EXTRA", "ALLOWANCE")]
  return {"case": case["name"], "rules": {"methods": [r["key"] for r in rows_by_kind[METHOD]], "facts": [r["key"] for r in rows_by_kind[FACT]], "choices": [r["key"] for r in rows_by_kind["CHOICE"]], "problems": rows_by_kind["problems"]},
    "hash": {k: docs[k].get("hash") for k in docs}, "lines": rows, "summary": summarise(rows)}

def answers_raw(case: dict) -> dict | None:
  from app.modules.drawings_boq.takeoff.proof.answers import answers as ANS
  return ANS.load(case["folder"])

def run_three(case_name: str, cases_dir: str | None, log=print) -> tuple:
  from app.engine.measure import rulebook as RB
  from app.modules.drawings_boq.takeoff.proof import case_io as CIO
  from app.modules.drawings_boq.takeoff.run import offline_run as OR
  from app.modules.drawings_boq.takeoff.proof import score as SC
  folder = os.path.join(CIO.HERE, case_name)
  case = CIO.load_case(folder)
  files, probs = CIO.find_files(case, CIO.cases_dir(cases_dir))
  if probs:
    raise SystemExit(f"{case_name}: {' '.join(probs)}")
  profile, rule_set = OR.seed_profile()
  catalog = OR.work_item_catalog()
  rows, rule_problems, _file = CIO.load_company_rules(case)
  
  if rule_problems:
    raise SystemExit(f"{case_name}: {' '.join(rule_problems)}")
  kinds = classify_rows(rows)
  sets = {"default": [], "facts": [r for r in rows if r not in kinds[METHOD]], "method": rows}
  docs = {}
  t0 = time.monotonic()
  for name, use in sets.items():
    with RB.using_case(use):
      docs[name], _ = SC.run_case(case, files, profile, rule_set, catalog, both=False, rules=None, keep={})
    log(f"{case_name}: {name} ({len(use)} rules) {time.monotonic() - t0:.0f} s, hash {str(docs[name]['hash'])[:16]}")
  return case, docs, kinds

def fmt(v, nd=1) -> str:
  return "" if v is None else f"{v:,.{nd}f}"

def render_md(result: dict) -> str:
  s = result["summary"]
  out = [f"# Method split: {result['case']}", "",
    f"Each line is run three times from the same reading: Trace's default method, with the building facts typed from the workbook, and with the QS's methods. {s['lines']} lines, {s['with_a_number']} with a Trace number.", "",
    f"- within tolerance of the QS: {s['within_tolerance_default']} with Trace's default, {s['within_tolerance_with_methods']} with his methods",
    f"- moved by facts typed from the workbook: {s['moved_by_facts']} lines; moved by his methods: {s['moved_by_methods']} lines",
    f"- workbook lines (his figure cannot be taken as measured): {s['workbook_lines']}; the rest, the reading score: {s['read_lines']} lines, {s['read_within_tolerance']} within tolerance",
    f"- lines outside tolerance, split into named parts: {s['split_lines']}; lines with a reading part still marked not diagnosed: {s['unexplained']}",
    f"- lines whose recorded cause calls the gap his convention or choice, kept as reading until he names the method: {s['method_suspected']}", "",
    "Rules of the case: methods " + (", ".join(result["rules"]["methods"]) or "none") + "; facts " + (", ".join(result["rules"]["facts"]) or "none") + "; choices " + (", ".join(result["rules"]["choices"]) or "none"), ""]
  
  if result["rules"]["problems"]:
    out += ["Problems with the rules of the case:"] + [f"- {p}" for p in result["rules"]["problems"]] + [""]
  out += ["| Line | Unit | QS | Trace default | + facts | + methods | Diff % | Verdict | Parts |", "|---|---|---|---|---|---|---|---|---|"]
  for r in result["lines"]:
    parts = "; ".join(f"{p['part']}{' (method suspected)' if p.get('method_suspected') else ''} {fmt(p.get('amount'))}: {p['text'][:90]}" for p in r["parts"])
    out.append(f"| {r['key']} | {r['unit'] or ''} | {fmt(r['qs'])} | {fmt(r['trace_default'])} | {fmt(r['trace_with_facts'])} | {fmt(r['trace_with_method'])} | {fmt(r['diff_pct'])} | {r['verdict']} | {parts} |")
  return "\n".join(out) + "\n"

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Split each difference between Trace and the QS into the building's facts, the QS's method, a workbook slip and what is left to reading.")
  ap.add_argument("cases", nargs="+")
  ap.add_argument("--out", default="method_split_out")
  ap.add_argument("--cases-dir")
  a = ap.parse_args(argv)
  os.makedirs(a.out, exist_ok=True)
  
  for name in a.cases:
    case, docs, kinds = run_three(name, a.cases_dir)
    result = split_case(case, docs, kinds)
    with open(os.path.join(a.out, f"method_split_{name}.json"), "w", encoding="utf-8") as fh:
      json.dump(result, fh, indent=1, sort_keys=True, ensure_ascii=False, default=str)
    with open(os.path.join(a.out, f"method_split_{name}.md"), "w", encoding="utf-8") as fh:
      fh.write(render_md(result))
    s = result["summary"]
    print(f"{name}: {s['with_a_number']} lines with a number; within tolerance {s['within_tolerance_default']} by default, {s['within_tolerance_with_methods']} with his methods; {s['workbook_lines']} workbook lines; {s['split_lines']} split; hash default {str(docs['default']['hash'])[:16]} facts {str(docs['facts']['hash'])[:16]} method {str(docs['method']['hash'])[:16]}")
    for p in result["rules"]["problems"]:
      print(f"  PROBLEM {p}")
  return 0

if __name__ == "__main__":
  sys.exit(main())
