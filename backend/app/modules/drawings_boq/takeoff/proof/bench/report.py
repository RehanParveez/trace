from __future__ import annotations
import csv
import datetime
import hashlib
import json
import os
import subprocess
from app.modules.drawings_boq.takeoff.proof.bench import sets as ST
from app.modules.drawings_boq.takeoff.proof import completeness_run as CR
from app.engine.catalogue import loader as CL
from app.modules.drawings_boq.takeoff.run import first_run_bindings as RB
from app.modules.drawings_boq.takeoff.completeness import ledger as LG
from app.modules.drawings_boq.takeoff.proof import gate16 as G16
from app.modules.drawings_boq.takeoff.questions import engine as QE
from app.modules.drawings_boq.takeoff.proof.answers import answers as ANS
from app.modules.drawings_boq.takeoff.ai_reader import cache as CACHE
from app.modules.drawings_boq.takeoff.ai_reader import cost as COST
from app.modules.drawings_boq.takeoff.completeness import facts as F
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.proof.bench import failures as FL
from app.modules.drawings_boq.takeoff.proof.bench import reads as RD
from app.modules.drawings_boq.takeoff.proof.bench import rows as RW
from app.modules.drawings_boq.takeoff.proof.reading import sets as RS
from app.modules.drawings_boq.takeoff.questions import answers as AN

PRODUCT, PROOF = "PRODUCT", "PROOF"
HISTORY = os.path.join(ST.HERE, "history.csv")
HISTORY_HEAD = ["date", "commit", "set", "run", "coverage_pct", "within_10", "compared", "silent", "ai_cost_pkr", "rows_sha"]

def engine_lines(score_dir: str | None, name: str) -> list | None:
  if not score_dir:
    return None
  lines = CR.lines_of(score_dir, name)
  path = os.path.join(score_dir, name, "score.json")
  if not os.path.isfile(path):
    return lines
  with open(path, encoding="utf-8") as fh:
    doc = json.load(fh)
    
  have = {(ln["family"], ln["floor"]) for ln in lines}
  for r in (doc.get("answers") or {}).get("table") or []:
    parts = str(r["key"]).split("/")
    floor = parts[1].upper() if len(parts) > 1 and parts[1] != "ALL" else None
    floor = floor if floor in F.FLOOR_ORDER else None
    if r.get("trace") is not None and (parts[0], floor) not in have:
      lines.append({"family": parts[0], "floor": floor, "value": r["trace"], "unit": r.get("unit")})
      have.add((parts[0], floor))
  return lines

def run_once(plain: dict, lines: list | None, storeys: list, answers: dict) -> dict:
  state, out, _rep, _b = RB.run_project(plains=[plain], lines=lines, storeys=storeys, answers=answers)
  result = {"ledger": state["ledger"], "facts": state["facts"], "scope": F.scope_of(state["facts"])}
  silent = G16.invariants(result, plain) + G16.assumption_problems(result, False)
  open_q = [q for q in state["questions"] if q["state"] == QE.OPEN]
  return {"state": state, "failed": list(out["failed"]), "silent": silent, "open": open_q}

def commit_id() -> str:
  try:
    out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=20, cwd=os.path.dirname(os.path.abspath(__file__)))
    return out.stdout.strip() or "no-git"
  except (OSError, subprocess.SubprocessError):
    return "no-git"

def stats(rows: list) -> dict:
  live = [r for r in rows if r["state"] != LG.NOT_APPLICABLE]
  n = len(live)
  not_read = sum(1 for r in live if r["state"] == LG.NOT_READ)
  assumed = sum(1 for r in live if r["state"] == LG.ASSUMED)
  asked = sum(1 for r in live if r["state"] == LG.ASKED)
  both = [r for r in rows if r["trace_qty"] is not None and r["answer_qty"] is not None]
  return {"rows": len(rows), "applicable": n, "not_read": not_read, "assumed": assumed, "asked": asked,
    "coverage": None if not n else round(100.0 * (n - not_read) / n, 1), "assumed_pct": None if not n else round(100.0 * assumed / n, 1),
    "compared": len(both), "within_10": sum(1 for r in both if r["within_10"]), "answer_no_number": sum(1 for r in rows if r["answer_qty"] is not None and r["trace_qty"] is None)}

def agreement(rows: list, answers_doc: dict | None, table: list, lines: list | None) -> dict:
  empty = {"compared": 0, "identical": 0, "not_compared": 0, "no_floor_row": 0, "differences": []}
  if not answers_doc or not table:
    return empty
  by_line: dict = {}
  keys_of: dict = {}
  
  for it in answers_doc.get("items") or []:
    line = ANS.ledger_line(it["element"], it.get("unit"))
    key = (line, it.get("floor") or "ALL")
    by_line.setdefault(key, set()).add(it["element"])
    keys_of.setdefault(it["element"], set()).add(key)
  at = {(r["element"], r["floor"]): r for r in rows}
  out = dict(empty)
  
  for t in table:
    parts = str(t["key"]).split("/")
    key = (parts[0], parts[1] if len(parts) > 1 else "ALL")
    elements = by_line.get(key) or set()
    item = CL.get(next(iter(elements))) if len(elements) == 1 else None
    if item is None or len({b.line for b in item.billing.PRIVATE_QS}) != 1:
      out["not_compared"] += 1
      continue
    row = at.get((item.id, key[1]))
    if row is None:
      out["not_compared"] += 1
      out["no_floor_row"] += 1
      continue
    whole = key[1] == "ALL"
    want = t.get("trace")
    if whole:
      same_family = [ln["value"] for ln in lines or [] if ln["family"] == key[0] and (ln.get("unit") or row["unit"]) == row["unit"]]
      want = round(sum(same_family), 3) if same_family else None
    only = keys_of[item.id] == {key}
    out["compared"] += 1
    ok = row["trace_qty"] is not None and want is not None and abs(row["trace_qty"] - want) <= 0.01 + abs(want) * 1e-6
    if ok and only:
      ok = (row["answer_qty"] is not None and abs(row["answer_qty"] - t["qs"]) <= 0.01 + abs(t["qs"]) * 1e-6
        and row["within_10"] == (t.get("diff_pct") is not None and abs(t["diff_pct"]) <= RW.WITHIN_PCT))
    if ok:
      out["identical"] += 1
    else:
      out["differences"].append(f"{t['key']} ({item.id}): bench trace {row['trace_qty']} answer {row['answer_qty']}, expected trace {want}" + (f" answer {t['qs']}" if only else ""))
  return out

def ai_cost(case_dir: str) -> dict:
  entries = CACHE.read_all(case_dir)
  c = COST.summarise(entries)
  return {"requests": c["requests"], "usd": c["usd"], "pkr": c["pkr"]}

def fmt(v, nd: int = 1) -> str:
  return "-" if v is None else (f"{v:.{nd}f}" if isinstance(v, float) else str(v))

def table(head: list, body: list) -> list:
  return ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"] + ["| " + " | ".join(str(c) for c in r) + " |" for r in body]

def render(ctx: dict) -> str:
  L = ["# Benchmark report", "", f"Commit `{ctx['commit']}`. rows.jsonl sha256 `{ctx['rows_sha']}`. {ctx['pdfs']} PDFs in {len(ctx['cases'])} case(s), {len(ctx['audit'])} audit set(s) without ledger rows ({', '.join(ctx['audit']) or 'none'}).", ""]
  L += ["Rows are ledger entries: one per catalogue item and floor. Coverage is the share of applicable entries (not NOT_APPLICABLE) that are not NOT_READ. The product run reads the PDFs with no case rules and no storeys, answers or decisions; the proof run adds the case's rules, storeys, answers and engine lines.", ""]
  L += ["## Sets", ""] + table(["Set", "PDFs", "Office", "Structure split", "Architecture and services split", "Answer file", "AI answers cached"],
    [[c["name"], ", ".join(c["pdfs"]), c["office"], c["splits"].get("structure"), c["splits"].get("architecture_and_services"), "yes" if c["has_answers"] else "no", c["ai"]["requests"]] for c in ctx["cases"]]) + [""]
  for run in (PRODUCT, PROOF):
    L += [f"## {run.title()}: every set, all sections", ""]
    body = []
    
    for c in ctx["cases"]:
      s = c["stats"][run]["all"]
      body.append([c["name"], c["office"], s["applicable"], fmt(s["coverage"]), fmt(s["assumed_pct"]), s["asked"], c["questions"][run], c["silent"][run], f"{s['within_10']} of {s['compared']}" + (f" (+{s['answer_no_number']} no number)" if s["answer_no_number"] else ""), fmt(c["ai"]["pkr"], 2)])
    L += table(["Set", "Office", "Applicable", "Coverage %", "Assumed %", "Asked", "Open questions", "Silent", "Within 10% of the answer file", "AI cost (PKR)"], body) + [""]
  L += ["## Product against proof", ""]
  L += table(["Set", "Coverage % product", "Coverage % proof", "Gap", "Assumed % product", "Assumed % proof", "Open questions product", "Open questions proof"],
    [[c["name"], fmt(c["stats"][PRODUCT]["all"]["coverage"]), fmt(c["stats"][PROOF]["all"]["coverage"]), fmt(None if c["stats"][PRODUCT]["all"]["coverage"] is None else round(c["stats"][PROOF]["all"]["coverage"] - c["stats"][PRODUCT]["all"]["coverage"], 1)),
      fmt(c["stats"][PRODUCT]["all"]["assumed_pct"]), fmt(c["stats"][PROOF]["all"]["assumed_pct"]), c["questions"][PRODUCT], c["questions"][PROOF]] for c in ctx["cases"]]) + [""]
  L += ["## By section group and split", ""]
  
  body = []
  for c in ctx["cases"]:
    for g in ctx["groups"]:
      for run in (PRODUCT, PROOF):
        s = c["stats"][run].get(g)
        if s is None:
          continue
        
        body.append([c["name"], g, c["splits"].get(g), run, s["applicable"], fmt(s["coverage"]), fmt(s["assumed_pct"]), s["asked"], f"{s['within_10']} of {s['compared']}"])
  L += table(["Set", "Section group", "Split", "Run", "Applicable", "Coverage %", "Assumed %", "Asked", "Within 10%"], body) + [""]
  L += ["## By catalogue section, all sets", ""]
  body = []
  for sec, per in ctx["by_section"].items():
    for run in (PRODUCT, PROOF):
      s = per[run]
      
      body.append([sec, run, s["applicable"], fmt(s["coverage"]), fmt(s["assumed_pct"]), s["asked"], f"{s['within_10']} of {s['compared']}"])
  L += table(["Section", "Run", "Applicable", "Coverage %", "Assumed %", "Asked", "Within 10%"], body) + [""]
  L += [f"## Failure groups ({ctx['failures_run'].lower()} run), ranked by offices, then money at risk, then sets, then items", ""]
  top = ctx["failures"][:ctx["top"]]
  L += table(["#", "Group", "Offices", "Sets", "Items", "Rows", "Money at risk", "Owner pack"],
    [[n, g["key"], f"{g['offices']} ({','.join(g['office_letters'])})", g["sets"], len(g["items"]), g["rows"], g["money"] if g["money_at_risk"] is None else f"{g['money_at_risk']:,.0f} ({g['money']})", g["suggested_owner"]] for n, g in enumerate(top, 1)]) + [""]
  L += [f"{len(ctx['failures'])} groups in all; the full list with items and example pages is in failures.json. Money is the answer-file quantity times a rate from `rates.yaml`; items with no rate are counted as unpriced, never guessed.", ""]
  L += ["## Checks", "", f"- Silent entries over all sets: product {ctx['silent_total'][PRODUCT]}, proof {ctx['silent_total'][PROOF]} (must be 0).",
    f"- Stages failed: {ctx['failed_stages'] or 'none'}.", f"- Answers whose element has no ledger entry: {ctx['lost_answers'] or 'none'}."]
  for name, a in ctx["agreement"].items():
    L.append(f"- {name}: {a['compared']} answers-pass line(s) compared with the bench rows, {a['identical']} identical, {a['not_compared']} not compared (several elements or lines per element; {a['no_floor_row']} on a floor the ledger holds no row for)" + (f"; differences: {'; '.join(a['differences'][:5])}" if a["differences"] else "") + ".")
  L += ["", ctx["notes"], ""]
  return "\n".join(L)

def write_rows(path: str, rows: list) -> str:
  rows = sorted(rows, key=lambda r: (r["set"], r["run"], r["element"], r["floor"]))
  body = "".join(json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n" for r in rows)
  with open(path, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(body)
  return hashlib.sha256(body.encode("utf-8")).hexdigest()

def append_history(path: str, lines: list) -> None:
  new = not os.path.isfile(path) or os.path.getsize(path) == 0
  with open(path, "a", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh, lineterminator="\n")
    if new:
      w.writerow(HISTORY_HEAD)
    for r in lines:
      w.writerow(r)

def run(out_dir: str, cases_dir: str | None = None, score_dir: str | None = None, product_score_dir: str | None = None, only: list | None = None, reads_cache: str | None = None,
  history: str | None = HISTORY, failures_run: str = PRODUCT, top: int = 20) -> int:
  doc = ST.load()
  bad = ST.problems(doc)
  
  if bad:
    for b in bad:
      print(b)
    return 1
  
  files_dir = CIO.cases_dir(cases_dir)
  splits_doc = ST.CEN.splits()
  groups = list((doc.get("section_groups") or {}).keys())
  group_of_section = {n: g for g, names in doc["section_groups"].items() for n in names}
  cases, all_rows, audit, failed, lost_answers = [], [], [], [], []
  silent_total = {PRODUCT: 0, PROOF: 0}
  agreements, pdfs = {}, 0
  for name in sorted(doc["sets"]):
    if only and name not in only:
      continue
    meta = doc["sets"][name]
    folder = os.path.join(CIO.HERE, name)
    if meta.get("audit"):
      audit.append(name)
      pdfs += len(RS._raw_case(folder).get("pdfs") or [])
      continue
    case = CIO.load_case(folder)
    pdfs += len(case["pdfs"])
    found, problems = CIO.find_files(case, files_dir)
    if problems:
      print(f"{name}: {'; '.join(problems)}")
      return 1
    
    office = meta["office"]
    splits = {g: ST.split_of(office, g, splits_doc) for g in groups}
    answers_doc = ANS.load(folder)
    decisions = AN.split_case(CIO.load_decisions(folder))[1]
    product_plain, proof_plain = RD.both(case, found, reads_cache)
    runs = {PRODUCT: run_once(product_plain, engine_lines(product_score_dir, name), [], {}), PROOF: run_once(proof_plain, engine_lines(score_dir, name), CR.storeys_of(name), decisions)}
    stats_by_run, questions, silent, rows_by_run = {}, {}, {}, {}
    for label, plain in ((PRODUCT, product_plain), (PROOF, proof_plain)):
      r = runs[label]
      failed += [f"{name} {label}: {s}" for s in r["failed"]]
      rows, info = RW.rows_of(name, office, splits, group_of_section, label, r["state"]["ledger"], answers_doc, plain, r["state"]["evidence"], case["pdfs"])
      lost_answers += [f"{name}: {e}" for e in info["answers_not_in_ledger"]]
      rows_by_run[label] = rows
      all_rows += rows
      per = {"all": stats(rows)}
      
      for g in groups:
        per[g] = stats([x for x in rows if x["group"] == g])
      stats_by_run[label] = per
      questions[label] = len(r["open"])
      silent[label] = len(r["silent"])
      silent_total[label] += len(r["silent"])
    if answers_doc and score_dir:
      path = os.path.join(score_dir, name, "score.json")
      if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
          table_rows = (json.load(fh).get("answers") or {}).get("table") or []
        agreements[name] = agreement(rows_by_run[PROOF], answers_doc, table_rows, engine_lines(score_dir, name))
        
    cases.append({"name": name, "pdfs": list(case["pdfs"]), "office": office, "splits": splits, "has_answers": bool(answers_doc), "stats": stats_by_run, "questions": questions, "silent": silent, "ai": ai_cost(folder)})
    print(f"{name}: product coverage {fmt(stats_by_run[PRODUCT]['all']['coverage'])}%, proof {fmt(stats_by_run[PROOF]['all']['coverage'])}%, silent {silent[PRODUCT]}/{silent[PROOF]}", flush=True)
  os.makedirs(out_dir, exist_ok=True)
  rows_sha = write_rows(os.path.join(out_dir, "rows.jsonl"), all_rows)
  
  by_section = {}
  for sec in sorted({r["section"] for r in all_rows}):
    by_section[sec] = {run_label: stats([r for r in all_rows if r["section"] == sec and r["run"] == run_label]) for run_label in (PRODUCT, PROOF)}
  failure_list = FL.groups([r for r in all_rows if r["run"] == failures_run])
  with open(os.path.join(out_dir, "failures.json"), "w", encoding="utf-8", newline="\n") as fh:
    json.dump(failure_list, fh, indent=1, sort_keys=True, ensure_ascii=False)
    fh.write("\n")
    
  notes = ("Product rows have an engine number only when `--product-score` points at a score run made with `--seed-rules`; without it the product run has coverage and states but no quantities, so no within-10% count. "
    "Sets with no answer file have no within-10% count. Scoring needs the answer file of BX-1; only the sets that have one can show accuracy.")
  commit = commit_id()
  ctx = {"commit": commit, "rows_sha": rows_sha, "pdfs": pdfs, "cases": cases, "audit": audit, "groups": groups, "by_section": by_section, "failures": failure_list, "failures_run": failures_run, "top": top,
    "silent_total": silent_total, "failed_stages": failed, "lost_answers": lost_answers, "agreement": agreements, "notes": notes}
  with open(os.path.join(out_dir, "bench.md"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write(render(ctx))
    
  if history:
    today = datetime.date.today().isoformat()
    append_history(history, [[today, commit, c["name"], run_label, fmt(c["stats"][run_label]["all"]["coverage"]), c["stats"][run_label]["all"]["within_10"], c["stats"][run_label]["all"]["compared"], c["silent"][run_label], c["ai"]["pkr"], rows_sha[:16]]
      for c in cases for run_label in (PRODUCT, PROOF)])
  print(f"{len(all_rows)} rows, rows.jsonl sha256 {rows_sha[:16]}, silent {silent_total[PRODUCT]}/{silent_total[PROOF]}, {len(failure_list)} failure groups; written to {out_dir}")
  return 1 if (silent_total[PRODUCT] or silent_total[PROOF] or failed or lost_answers) else 0
