from __future__ import annotations
import argparse
import json
import os
import re
import sys
import yaml
from app.modules.drawings_boq.takeoff.proof.reading import sets as S
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from collections import Counter
from app.modules.drawings_boq.takeoff.ai_reader import cache as CACHE
from app.modules.drawings_boq.takeoff.ai_reader import compare as CMP
from app.modules.drawings_boq.takeoff.ai_reader import contract as C
from app.modules.drawings_boq.takeoff.ai_reader import cost as COST
from app.modules.drawings_boq.takeoff.ai_reader import legend as LG
from app.modules.drawings_boq.takeoff.ai_reader import notes as NT
from app.modules.drawings_boq.takeoff.ai_reader import schedule as SCH
from app.modules.drawings_boq.takeoff.proof.reading import formats as F
from app.modules.drawings_boq.takeoff.proof.reading.formats import KEY_LEN
from app.modules.drawings_boq.takeoff.run import reading_adapter as RA

TRUTH_KEYS = ("discipline", "floor", "title", "sheet_no", "role")
ROLE_FAMILY = {"LEGEND": "NOTES", "SPEC": "NOTES"}
READ_ROLE = re.compile(r"^role: truth (?P<truth>\w+), read (?P<read>\w+)$")
MAX_LISTED = 40
ABSENT = object()

def role_family(role) -> str | None:
  """Puts a role on the scale the register truth uses, where a legend and a specification are notes and the four kinds of plan are one."""
  if role is None:
    return None
  mapped = RA.ROLE_OF.get(str(role))
  return ROLE_FAMILY.get(str(role), mapped.value if mapped else str(role))

def rule_reads(path: str | None) -> dict:
  """Reads, from a reading score, the role the rule reader gave each sheet of each set, keyed by the set's pdf key and the sheet."""
  if not path:
    return {}
  with open(path, encoding="utf-8") as fh:
    rows = json.load(fh)["outcomes"]
  out: dict = {}
  for r in rows:
    if r.get("class") != "REGISTER" or not str(r["id"]).endswith(":role"):
      continue
    key = (str(r["id"]).split(":")[0], int(r["sheet"]))
    if r["outcome"] == "MATCHED_OK":
      m = READ_ROLE.match(str(r.get("detail") or ""))
      out[key] = m.group("truth") if m else "SAME"
      continue
    m = READ_ROLE.match(str(r.get("detail") or ""))
    out[key] = None if not m or m.group("read") == "None" else m.group("read")
  return out

def sheet_no_same(a, b) -> bool:
  norm = lambda v: re.sub(r"[^A-Z0-9]", "", str(v or "").upper())
  return bool(norm(a)) and norm(a) == norm(b)

def role_report(rows: list) -> dict:
  tally = lambda: {"right": 0, "wrong": 0, "none": 0}
  out = {"role": tally(), "rule": tally(), "helped": 0, "at_risk": 0, "both_none": 0, "sheet_no": tally(), "floor": tally(), "listed": []}
  for page, truth, ai, rule in rows:
    ai = ai or {}
    
    want, got = role_family(truth.get("role")), role_family(ai.get("role"))
    if want and want != "3D":
      out["role"]["right" if got == want else "none" if got is None else "wrong"] += 1
      said = want if rule == "SAME" else rule
      if rule is not ABSENT:
        out["rule"]["none" if said is None else "right" if said == want else "wrong"] += 1
        out["both_none"] += 1 if got is None and said is None else 0
        out["helped"] += 1 if got == want and said != want else 0
        out["at_risk"] += 1 if got is not None and said == want and got != want else 0
        if got is not None and said is not None and got != said and len(out["listed"]) < MAX_LISTED:
          out["listed"].append({"page": page, "truth": want, "rule": said, "ai": got, "quote": (ai.get("quotes") or {}).get("role")})
          
    if truth.get("sheet_no"):
      value = ai.get("sheet_no")
      out["sheet_no"]["none" if value is None else "right" if sheet_no_same(value, truth["sheet_no"]) else "wrong"] += 1
    if truth.get("floor"):
      floors = ai.get("floors")
      out["floor"]["none" if not floors else "right" if str(truth["floor"]).upper() in floors else "wrong"] += 1
  return out

def note_report(entries: list) -> dict:
  failed, keys = Counter(), Counter()
  proposed = accepted = 0
  for e in entries:
    checks = e.get("validators") or []
    proposed += sum(1 for v in checks if v["name"].startswith("quote_printed"))
    facts = (e.get("answer") or {}).get("facts") or []
    accepted += len(facts)
    keys.update(f["key"] for f in facts)
    failed.update(v["name"].split(".")[0] for v in checks if not v["passed"])
  return {"proposed": proposed, "accepted": accepted, "failed": dict(sorted(failed.items())), "keys": dict(sorted(keys.items()))}


SCHEDULE_CLASSES = {"COLUMN_SCHEDULE": "COLUMN_SCHEDULE_CELL", "BEAM_SCHEDULE": "BEAM_SECTION", "FINISH_SCHEDULE": "FINISH_LAYER"}
SIZE_SLACK_IN = 0.05

def _truth_sizes(attrs: dict) -> tuple | None:
  """Gives the two lengths of a truth row in inches, or None when it states none."""
  mm = attrs.get("size_mm")
  if mm:
    return (mm[0] / SCH.IN_MM, mm[1] / SCH.IN_MM)
  if attrs.get("width_in"):
    return (float(attrs["width_in"]), float(attrs["depth_in"]) if attrs.get("depth_in") else None)
  return None

def _row_matches(kind: str, row: dict, truth) -> bool:
  """Says whether an accepted row of the AI is the truth row: the same mark, and the same floor, size or layer text as the truth states."""
  attrs = truth.attrs or {}
  if SCH._compact(row.get("mark")) != SCH._compact(truth.mark):
    return False
  if kind == "FINISH_SCHEDULE":
    mine, theirs = SCH._compact(row.get("layer")), SCH._compact(attrs.get("text"))
    return bool(mine and theirs and (mine in theirs or theirs in mine))
  if kind == "COLUMN_SCHEDULE" and attrs.get("floor") and SCH.floor_of(row.get("floor")) != str(attrs["floor"]).upper():
    return False
  size, want = SCH.size_in(row.get("size")), _truth_sizes(attrs)
  if size is None or want is None:
    return False
  if want[1] is None:
    return min(abs(size[0] - want[0]), abs(size[1] - want[0])) <= SIZE_SLACK_IN
  return (abs(size[0] - want[0]) <= SIZE_SLACK_IN and abs(size[1] - want[1]) <= SIZE_SLACK_IN) or (abs(size[0] - want[1]) <= SIZE_SLACK_IN and abs(size[1] - want[0]) <= SIZE_SLACK_IN)

def schedule_report(entries: list, refs: dict) -> dict:
  held, kept = Counter(), Counter()
  proposed = accepted = 0
  found: dict = {}
  
  for e in entries:
    checks = e.get("validators") or []
    proposed += sum(1 for v in checks if v["name"].startswith("quote_printed"))
    value = e.get("answer") or {}
    for h in value.get("held") or []:
      held.update(h["reasons"])
    ref = refs.get(str(e["pdf_sha256"])[:KEY_LEN])
    truth = [t for t in F.load_set(ref.truth_folder).elements if ref and t.sheet == int(e["page"])] if ref else []
    for s in value.get("schedules") or []:
      accepted += len(s["rows"])
      
      kept[s["kind"]] += len(s["rows"])
      cls = SCHEDULE_CLASSES[s["kind"]]
      slot = found.setdefault(cls, {"truth": 0, "read": 0, "ids": set()})
      for t in (t for t in truth if t.cls.value == cls):
        if id(t) not in slot["ids"] and any(_row_matches(s["kind"], r, t) for r in s["rows"]):
          slot["ids"].add(id(t))
          slot["read"] += 1
          
  for ref_key in {str(e["pdf_sha256"])[:KEY_LEN] for e in entries}:
    ref = refs.get(ref_key)
    if not ref:
      continue
    pages = {int(e["page"]) for e in entries if str(e["pdf_sha256"])[:KEY_LEN] == ref_key}
    truth = F.load_set(ref.truth_folder).elements
    for cls in SCHEDULE_CLASSES.values():
      n = sum(1 for t in truth if t.cls.value == cls and t.sheet in pages)
      if n:
        found.setdefault(cls, {"truth": 0, "read": 0, "ids": set()})["truth"] += n
  return {"proposed": proposed, "accepted": accepted, "held": dict(sorted(held.items())), "kinds": dict(sorted(kept.items())), "truth": {c: [v["read"], v["truth"]] for c, v in sorted(found.items())}}

def legend_report(entries: list) -> dict:
  held, kinds, agreement = Counter(), Counter(), Counter()
  proposed = accepted = 0
  for e in entries:
    checks = e.get("validators") or []
    proposed += sum(1 for v in checks if v["name"].startswith("quote_printed"))
    value = e.get("answer") or {}
    accepted += len(value.get("rows") or [])
    kinds.update(r["meaning"] for r in value.get("rows") or [])
    for h in value.get("held") or []:
      held.update(h["reasons"])
    agreement.update(c["agreement"] for c in value.get("compared") or [])
  return {"proposed": proposed, "accepted": accepted, "held": dict(sorted(held.items())), "kinds": dict(sorted(kinds.items())), "agreement": {k: agreement.get(k, 0) for k in CMP.AGREEMENTS}}

def truth_rows(folder: str) -> dict:
  path = os.path.join(folder, "register.yaml")
  if not os.path.isfile(path):
    return {}
  with open(path, encoding="utf-8") as fh:
    rows = yaml.safe_load(fh) or []
  return {int(r["sheet"]): {k: r.get(k) for k in TRUTH_KEYS} for r in rows if r.get("sheet") is not None}

def evaluate(cases_dir: str | None = None, root: str = CIO.HERE, reading_score: str | None = None) -> dict:
  refs = {}
  reads = rule_reads(reading_score)
  for ref in S.find_sets(cases_dir, root):
    refs.setdefault(ref.pdf_key, ref)
  out: dict = {}
  for name in CIO.list_cases(root, audit=True):
    entries = CACHE.read_all(os.path.join(root, name))
    for e in entries:
      slot = out.setdefault((name, e["task"]), {"entries": [], "refs": set()})
      slot["entries"].append(e)
      slot["refs"].add(str(e["pdf_sha256"])[:KEY_LEN])
      
  report: dict = {}
  for (case, task), slot in sorted(out.items()):
    entries = slot["entries"]
    if task == SCH.TASK:
      report[f"{case}/{task}"] = {"schedules": schedule_report(entries, refs), "entries": len(entries), "status": {"OK": sum(1 for e in entries if e["status"] == "OK")},
        "cost": COST.summarise(entries), "models": sorted({e["model"] for e in entries})}
      continue
    if task == LG.TASK:
      report[f"{case}/{task}"] = {"legends": legend_report(entries), "entries": len(entries), "status": {"OK": sum(1 for e in entries if e["status"] == "OK")},
        "cost": COST.summarise(entries), "models": sorted({e["model"] for e in entries})}
      continue
    if task == NT.TASK:
      report[f"{case}/{task}"] = {"notes": note_report(entries), "entries": len(entries), "status": {"OK": sum(1 for e in entries if e["status"] == "OK")},
        "cost": COST.summarise(entries), "models": sorted({e["model"] for e in entries})}
      continue
    status = {"OK": 0, "INVALID": 0}
    shape_ok = 0
    check_total = check_pass = 0
    facts = {k: {a: 0 for a in CMP.AGREEMENTS} for k in C.KEYS if k != "role"}
    unmatched = 0
    role_rows: list = []
    
    for e in entries:
      status[e["status"]] = status.get(e["status"], 0) + 1
      clean, _problems = C.validate(e.get("answer"))
      shape_ok += 1 if clean is not None else 0
      for v in e.get("validators") or []:
        check_total += 1
        check_pass += 1 if v["passed"] else 0
      ref = refs.get(str(e["pdf_sha256"])[:KEY_LEN])
      truth = truth_rows(ref.truth_folder).get(int(e["page"])) if ref else None
      if truth is None or clean is None:
        unmatched += 1
        continue
      
      for rec in CMP.compare({k: v for k, v in truth.items() if k != "role"}, clean):
        if rec["fact_key"] in facts:
          facts[rec["fact_key"]][rec["agreement"]] += 1
      role_rows.append((int(e["page"]), truth, clean, reads.get((str(e["pdf_sha256"])[:KEY_LEN], int(e["page"])), ABSENT) if reads else ABSENT))
    report[f"{case}/{task}"] = {"roles": role_report(role_rows), "entries": len(entries), "status": status, "shape_ok": shape_ok, "checks": [check_pass, check_total], "unmatched": unmatched, "facts": facts,
      "cost": COST.summarise(entries), "models": sorted({e["model"] for e in entries})}
  return report

def role_lines(roles: dict, judged: int) -> list:
  r, rule, no, fl = roles["role"], roles["rule"], roles["sheet_no"], roles["floor"]
  total = sum(r.values())
  out = []
  if total:
    out.append(f"    role (against {total} truth rows): AI right {r['right']}, wrong {r['wrong']}, gave none {r['none']} ({100.0 * r['none'] / total:.1f}% unknown)")
  if sum(rule.values()):
    out.append(f"    role, rule reader: right {rule['right']}, wrong {rule['wrong']}, none {rule['none']}; the AI is right where the rule reader is not on {roles['helped']}, differs from a right rule reading on {roles['at_risk']}; both give none on {roles['both_none']} ({100.0 * roles['both_none'] / max(total, 1):.1f}% unknown with the AI)")
  if sum(no.values()):
    out.append(f"    sheet number: right {no['right']}, wrong {no['wrong']}, none {no['none']}")
  if sum(fl.values()):
    out.append(f"    floor: right {fl['right']}, wrong {fl['wrong']}, none {fl['none']}")
  out.extend(f"    differs: page {d['page']} truth {d['truth']}, rule {d['rule']}, AI {d['ai']}" + (f" ({d['quote']})" if d["quote"] else "") for d in roles["listed"])
  return out

def lines(report: dict) -> list:
  out = []
  for key, r in report.items():
    if "schedules" in r:
      n, c = r["schedules"], r["cost"]
      out.append(f"{key}: {r['entries']} cached answer(s), models {', '.join(r['models'])}; {n['proposed']} row(s) proposed, {n['accepted']} passed every page check; held because: "
        + (", ".join(f"{k} {v}" for k, v in n["held"].items()) or "nothing") + "; kept: " + (", ".join(f"{k} {v}" for k, v in n["kinds"].items()) or "none"))
      out.extend(f"    {cls}: {read} of {truth} truth row(s) read by an accepted row" for cls, (read, truth) in n["truth"].items())
      out.append(f"    cost: {c['input_tokens']} input and {c['output_tokens']} output tokens, {c['seconds']} s, {c['usd']} USD, {c['pkr']} PKR")
      continue
    if "legends" in r:
      n, c, a = r["legends"], r["cost"], r["legends"]["agreement"]
      out.append(f"{key}: {r['entries']} cached answer(s), models {', '.join(r['models'])}; {n['proposed']} legend row(s) asked, {n['accepted']} passed every check; held because: "
        + (", ".join(f"{k} {v}" for k, v in n["held"].items()) or "nothing") + "; meanings kept: " + (", ".join(f"{k} {v}" for k, v in n["kinds"].items()) or "none"))
      out.append(f"    against the rules' reading of the words: {a['AGREE']} agree, {a['DISAGREE']} differ, {a['AI_ONLY']} placed by the AI alone, {a['RULE_ONLY']} placed by the rules alone")
      out.append(f"    cost: {c['input_tokens']} input and {c['output_tokens']} output tokens, {c['seconds']} s, {c['usd']} USD, {c['pkr']} PKR")
      continue
    if "notes" in r:
      n, c = r["notes"], r["cost"]
      out.append(f"{key}: {r['entries']} cached answer(s), models {', '.join(r['models'])}; {n['proposed']} fact(s) proposed, {n['accepted']} passed every page check; stopped by: "
        + (", ".join(f"{k} {v}" for k, v in n["failed"].items()) or "nothing") + "; kept: " + (", ".join(f"{k} {v}" for k, v in n["keys"].items()) or "none"))
      out.append(f"    cost: {c['input_tokens']} input and {c['output_tokens']} output tokens, {c['seconds']} s, {c['usd']} USD, {c['pkr']} PKR")
      continue
    out.append(f"{key}: {r['entries']} cached answer(s), models {', '.join(r['models'])}; {r['shape_ok']} with a valid shape, {r['status'].get('INVALID', 0)} unusable; evidence checks passed {r['checks'][0]} of {r['checks'][1]}; {r['unmatched']} without a truth row")
    for fact, a in r["facts"].items():
      n = sum(a.values())
      if n:
        out.append(f"    {fact}: {a['AGREE']} agree, {a['DISAGREE']} differ, {a['AI_ONLY']} AI only, {a['RULE_ONLY']} truth only (of {n})")
    out.extend(role_lines(r["roles"], r["entries"] - r["unmatched"]))
    c = r["cost"]
    out.append(f"    cost: {c['input_tokens']} input and {c['output_tokens']} output tokens, {c['seconds']} s, {c['usd']} USD, {c['pkr']} PKR" + (f"; no price set for {', '.join(c['unpriced_models'])}" if c["unpriced_models"] else ""))
  return out

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Score the cached AI answers of every case against its truth folder and report time and cost. It reads files only and never calls a model.")
  ap.add_argument("--cases-dir", default=None)
  ap.add_argument("--reading-score", default=None, help="a reading_score.json; the rule reader's role for each sheet is read from it and printed beside the AI's")
  args = ap.parse_args(argv)
  report = evaluate(args.cases_dir, reading_score=args.reading_score)
  if not report:
    print("No ai_cache folder holds an answer yet.")
    return 0
  for ln in lines(report):
    print(ln)
  return 0

if __name__ == "__main__":
  sys.exit(main())
