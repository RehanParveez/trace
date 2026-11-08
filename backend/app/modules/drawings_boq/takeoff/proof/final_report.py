from __future__ import annotations
import argparse
import collections
import json
import os
import sys
import yaml
from app.engine.measure import rule_registry as RR
from app.modules.drawings_boq.takeoff.proof import h_numbers as HN
from app.modules.drawings_boq.takeoff.proof.bench import explained as EXD
from app.modules.drawings_boq.takeoff.proof.bench import offices as OFF
from app.modules.drawings_boq.takeoff.proof.bench import report as RP
from app.modules.drawings_boq.takeoff.proof.bench import sets as ST
from app.modules.drawings_boq.takeoff.proof import offices as OFC

HERE = os.path.dirname(os.path.abspath(__file__))
PACKS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "..", "..", "docs", "packs", "generality.yaml"))

def registry_summary(rules: list | None = None) -> dict:
  rules = RR.load() if rules is None else rules
  by_status = collections.Counter(r.get("status") for r in rules)
  by_default = collections.Counter(r.get("default") for r in rules)
  by_kind = collections.Counter(r.get("kind") for r in rules)
  ready = sorted(r["id"] for r in rules if r.get("status") == "CANDIDATE" and len(RR.offices_met(r)) >= RR.MIN_OFFICES)
  one = sorted(r["id"] for r in rules if r.get("status") == "CANDIDATE" and len(RR.offices_met(r)) == 1)
  none = sorted(r["id"] for r in rules if r.get("status") == "CANDIDATE" and not RR.offices_met(r))
  return {"rules": len(rules), "status": dict(by_status), "default": dict(by_default), "kind": dict(by_kind),
    "two_offices_met_still_candidate": ready, "one_office_met": one, "no_evidence_met": none}

def pack_summary(path: str = PACKS) -> dict:
  with open(path, encoding="utf-8") as fh:
    rows = yaml.safe_load(fh) or []
  recs = [r["generality"] for r in rows if isinstance(r, dict) and "generality" in r]
  first = [r["pack"] for r in recs if not str(r.get("first_sight", "")).lower().startswith("none")]
  return {"records": len(recs), "packs": [r["pack"] for r in recs], "with_first_sight": first, "without_first_sight": len(recs) - len(first)}

def score_summary(folder: str) -> dict:
  out: dict = {}
  for name in sorted(os.listdir(folder)):
    p = os.path.join(folder, name, "score.json")
    if not os.path.isfile(p):
      continue
    with open(p, encoding="utf-8") as fh:
      d = json.load(fh)
    s = d.get("summary") or {}
    sf = d.get("safe") or {}
    out[name] = {"status": d.get("status"), "lines": s.get("lines"), "with_a_number": s.get("with_a_number"), "within_10": s.get("within_10"),
      "within_5": s.get("within_5"), "line_status": s.get("status"), "safe_rows": sf.get("safe_rows"), "safe_precision_pct": sf.get("safe_precision_pct"),
      "safe_coverage_pct": sf.get("safe_coverage_pct"), "hash": str(d.get("hash", ""))[:16], "engine_digest": str(d.get("engine_digest", ""))[:16],
      "invariants_failing": sum(1 for i in d.get("invariants") or [] if i.get("status") != "PASS")}
  return out

def collect(score: str | None = None, bench: str | None = None, reading: str | None = None, before: str | None = None, cfg: dict | None = None) -> dict:
  """Gathers every number of the report from the folders given: this run's score, benchmark and reading folders, and the before_H folder laid out the same way."""
  cfg = HN.load() if cfg is None else cfg
  folders = cfg["folders"]
  there = lambda sub: os.path.join(before, folders[sub]) if before else None
  sets_doc = ST.load()
  history = OFF.history_rows()
  after_rows, before_rows = HN.bench_rows(bench), HN.bench_rows(there("bench"))
  score_before = there("score") if before and os.path.isdir(there("score")) else None
  packs = pack_summary()
  return {"cfg": cfg, "commit": RP.commit_id(), "folders": {"score": score, "bench": bench, "reading": reading, "before": before},
    "scores": score_summary(score) if score and os.path.isdir(score) else None, "scores_before": score_summary(score_before) if score_before else None,
    "check": HN.gates(HN.read_json(os.path.join(score or "", "check.json")) if score else None, cfg["required_gates"]),
    "reading": HN.reading_rows(HN.read_json(os.path.join(reading or "", "reading_score.json")) if reading else None, cfg["reading_splits"]),
    "reading_before": HN.reading_rows(HN.read_json(os.path.join(there("reading") or "", "reading_score.json")) if before else None, cfg["reading_splits"]),
    "bench": HN.bench_pairs(before_rows, after_rows, list(sets_doc.get("section_groups") or {})), "bench_found": {"before": before_rows is not None, "after": after_rows is not None},
    "rows_sha": {"before": HN.file_sha(os.path.join(there("bench") or "", "rows.jsonl")), "after": HN.file_sha(os.path.join(bench or "", "rows.jsonl"))},
    "cost": HN.cost_rows(sets_doc), "hit_line": EXD.hit_line(EXD.load()), "registry": registry_summary(), "overrides": [{**o, "delivered": o["until"] in packs["packs"]} for o in HN.overrides_left()], "gate17": HN.gate17_exceptions(),
    "first_sight": HN.first_sight(sets_doc, OFF.load(), history, after_rows, cfg["first_sight_floor_pct"]), "first_sight_line": OFC.first_sight_line(OFF.load(), sets_doc, history),
    "open": HN.open_groups(after_rows, cfg["failures_run"], cfg["top_groups"]), "packs": packs}

def table(head: list, body: list) -> list:
  """Builds a Markdown table; a pipe inside a cell is written as a slash."""
  return ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"] + ["| " + " | ".join(str(c).replace("|", "/") for c in r) + " |" for r in body]

def counted(s: dict | None) -> str:
  """Writes the within-10% count of a benchmark side, or a dash."""
  return "-" if s is None else f"{s['within_10']} of {s['compared']}"

def measures(d: dict) -> list:
  """Builds the rows of the before-and-after table: the checks, the engine hash and the QS lines within 10% of each scored case, the reading recall and hash, the registry, the overrides and the gate 17 exceptions."""
  seven, rows = d["cfg"]["seven_nov"], []
  chk = d["check"]
  rows.append(["Checks", seven["checks"], "7 Nov", f"{chk['checks'] - chk['failed']} of {chk['checks']} pass" if chk["found"] else "check not run"])
  for case, now in (d["scores"] or {}).items():
    was = (d["scores_before"] or {}).get(case)
    rows.append([f"Engine hash {case}", (was or {}).get("engine_digest", "")[:8] or seven["engine_digest"].get(case, "-"), "before_H" if was else "7 Nov", now["engine_digest"][:8]])
    old = seven["qs_within_10"].get(case)
    rows.append([f"QS lines within 10% {case}", f"{was['within_10']} of {was['lines']}" if was else (f"{old['within']} of {old['of']}" if old else "-"), "before_H" if was else "7 Nov", f"{now['within_10']} of {now['lines']}"])
  for split in d["cfg"]["reading_splits"]:
    now, was = d["reading"].get("splits", {}).get(split), d["reading_before"].get("splits", {}).get(split)
    old = seven["reading"].get(split)
    after = "-" if not now else f"{now['recall']:.1%} of {now['truth']:,} truth items, {now['silent_wrong']} silent wrong"
    before = f"{was['recall']:.1%} of {was['truth']:,} truth items, {was['silent_wrong']} silent wrong" if was else (f"{old['recall_pct']:.1f}% of {old['truth']:,} truth items" if old else "-")
    if after != "-" or before != "-":
      rows.append([f"Reading recall, {split} split", before, "before_H" if was else ("7 Nov" if old else "-"), after])
    old_hash, new_hash = (was or {}).get("hash") or (old or {}).get("hash") or "-", (now or {}).get("hash", "-")
    if old_hash != "-" or new_hash != "-":
      rows.append([f"Reading hash, {split} split", old_hash, "before_H" if was else ("7 Nov" if old else "-"), new_hash])
  reg = d["registry"]
  rows.append(["Rules in the registry", seven["registry"], "7 Nov", f"{reg['rules']} rules; status {json.dumps(reg['status'])}; default {json.dumps(reg['default'])}"])
  rows.append(["Proof overrides", seven["overrides"], "7 Nov", len(d["overrides"])])
  rows.append(["Gate 17 exceptions", seven["gate17_exceptions"], "7 Nov", d["gate17"]])
  return rows

def bench_table(rows: list, keys: list, labels: list) -> list:
  """Sets before and after side by side for one family of pair rows: coverage, its change, the within-10% count and the assumed share."""
  head = [*labels, "Run", "Coverage % before", "Coverage % after", "Change", "Within 10% before", "Within 10% after", "Assumed % before", "Assumed % after"]
  body = []
  for r in rows:
    b, a = r["before"], r["after"]
    if b is None and a is None:
      continue
    body.append([*[r[k] for k in keys], r["run"].title(), RP.fmt(None if b is None else b["coverage"]), RP.fmt(None if a is None else a["coverage"]), RP.fmt(r["coverage_change"]),
      counted(b), counted(a), RP.fmt(None if b is None else b["assumed_pct"]), RP.fmt(None if a is None else a["assumed_pct"])])
  return table(head, body)

def render(d: dict) -> str:
  """Writes the whole report: the gates, the before-and-after measures, the benchmark before and after, the AI cost, the registry and overrides, first sight, what is open, the pack records and the command that reproduces it."""
  cfg, chk, L = d["cfg"], d["check"], []
  L += ["# H result", "", f"Commit `{d['commit']}`. Every number below is read from the folders named at the end and is reproduced by the command at the end.", ""]
  L += ["## Gates 14 to 18", ""]
  if not chk["found"]:
    L += [f"No check.json in the score folder: the check was not run, so no gate is shown green. Required: {', '.join(str(g) for g in cfg['required_gates'])}.", ""]
  else:
    L += table(["Gate", "Result", "Checks under it"], [[g, "green" if chk["by_gate"][g]["ok"] else "RED", chk["by_gate"][g]["checks"]] if g in chk["by_gate"] else [g, "NOT RUN", 0] for g in cfg["required_gates"]])
    L += ["", f"Gates {', '.join(str(g) for g in cfg['required_gates'])}: **{'green' if chk['green'] else 'NOT green'}**." + (f" Not run: {', '.join(str(g) for g in chk['missing'])}." if chk["missing"] else "") + (f" Red: {', '.join(str(g) for g in chk['red'])}." if chk["red"] else "") + f" The whole check ran {chk['checks']} item(s), {chk['failed']} failed.", ""]
    L += [f"- Gate {g}: {n}" for g in chk["red"] for n in chk["by_gate"][g]["notes"]] + ([""] if chk["red"] else [])
  L += ["## Before and after", "", f"Before values come from the before_H folder where it holds them, otherwise from the values recorded on {cfg['seven_nov']['recorded']}.", ""]
  L += table(["Measure", "Before", "Source", "After"], measures(d)) + [""]
  found = d["bench_found"]
  L += ["## Benchmark before and after", ""]
  if not found["after"]:
    L += ["No benchmark rows for this run: the bench folder has no rows.jsonl.", ""]
    
  else:
    L += [f"After: rows.jsonl sha256 `{(d['rows_sha']['after'] or '')[:16]}`." + (f" Before: `{(d['rows_sha']['before'] or '')[:16]}`." if found["before"] else " **No before benchmark was found**: the before columns are dashes. Make it by running the benchmark on the pre-H tree with the measuring packs applied, into before_H/bench_out."), ""]
    L += ["### Every set, all sections", ""] + bench_table(d["bench"]["by_set"], ["set"], ["Set"]) + [""]
    L += ["### Every set by section group", ""] + bench_table(d["bench"]["by_group"], ["set", "group"], ["Set", "Section group"]) + [""]
    L += ["### Every catalogue section, all sets", ""] + bench_table(d["bench"]["by_section"], ["section"], ["Section"]) + [""]
  c = d["cost"]
  L += ["## AI cost per set and task", ""]
  if not c["rows"]:
    L += ["No AI answer is kept in any set's ai_cache: no request was made, so the cost is 0.", ""]
  else:
    L += table(["Set", "Task", "Requests", "Input tokens", "Output tokens", "USD", "PKR"], [[r["set"], r["task"], r["requests"], r["input_tokens"], r["output_tokens"], f"{r['usd']:.4f}", f"{r['pkr']:.2f}"] for r in c["rows"]])
    L += ["", f"Total {c['requests']} request(s), {c['usd']:.4f} USD, {c['pkr']:.2f} PKR. By task: " + "; ".join(f"{t} {v['requests']} request(s), {v['pkr']:.2f} PKR" for t, v in sorted(c["by_task"].items())) + "."]
    L += ([f"Models with no price in the price table (their cost counts as 0): {', '.join(c['unpriced_models'])}."] if c["unpriced_models"] else []) + [""]
  L += [d["hit_line"], ""]
  
  reg = d["registry"]
  L += ["## Rule registry and overrides left", "",
    f"- {reg['rules']} rules; status {json.dumps(reg['status'])}; default {json.dumps(reg['default'])}; kind {json.dumps(reg['kind'])}.",
    f"- Candidates whose evidence meets two offices: {', '.join(reg['two_offices_met_still_candidate']) or 'none'}.",
    f"- Candidates met on one office: {len(reg['one_office_met'])}; with no met evidence: {len(reg['no_evidence_met'])}.",
    f"- {len(d['overrides'])} proof override(s) left, each forced on or off in one set until the pack named settles it; {sum(1 for o in d['overrides'] if o['delivered'])} of them name a pack that is already delivered:", ""]
  L += table(["Set", "Rule", "Value", "Until", "Pack delivered", "Date", "Reason"], [[o["set"], o["rule"], o["value"], o["until"], "yes" if o["delivered"] else "no", o["date"], o["reason"]] for o in d["overrides"]]) + [""]
  L += ["## First sight on new sets", "", d["first_sight_line"], ""]
  fs = d["first_sight"]
  
  if not fs:
    L += ["No set has entered through the offices register yet, so there is no first score to set beside a current one.", ""]
  else:
    body = [[s["set"], s["office"], "/".join(str(v) for v in s["labels"].values()), (s["first"] or {}).get("date", "-"), (s["first"] or {}).get("commit", "-"), (s["first"] or {}).get("coverage_pct", "-"),
      f"{(s['first'] or {}).get('within_10', '-')} of {(s['first'] or {}).get('compared', '-')}", RP.fmt(None if s["now"] is None else s["now"]["coverage"]), counted(s["now"]), "UNDER FLOOR" if s["below_floor"] else ""] for s in fs]
    L += table(["Set", "Office", "Split (structure/architecture)", "First scored", "Commit", "First coverage %", "First within 10%", "Current coverage %", "Current within 10%", f"Floor {cfg['first_sight_floor_pct']}%"], body) + [""]
  o = d["open"]
  L += [f"## What is open: the top {len(o['shown'])} failure groups of {o['groups']} ({o['run'].lower()} run)", ""]
  if not o["groups"]:
    L += ["No failure group: the latest benchmark rows have none, or the benchmark was not run.", ""]
  else:
    L += table(["#", "Group", "Offices", "Sets", "Items", "Rows", "Money at risk", "Owner pack"],
      [[n, g["key"], f"{g['offices']} ({','.join(g['office_letters'])})", g["sets"], len(g["items"]), g["rows"], g["money"] if g["money_at_risk"] is None else f"{g['money_at_risk']:,.0f} ({g['money']})", g["suggested_owner"]] for n, g in enumerate(o["shown"], 1)])
    L += ["", "Groups by owner: " + ", ".join(f"{k} {v}" for k, v in o["by_owner"].items()) + ".", ""]
  p = d["packs"]
  L += ["## Pack records", "", f"- {p['records']} generality records; {p['without_first_sight']} name no first-sight set; with a first-sight set: {', '.join(p['with_first_sight']) or 'none'}.", ""]
  if d["scores"]:
    L += ["## Scored sets", ""] + table(["set", "lines", "with a number", "within 10%", "within 5%", "safe rows", "safe precision %", "invariants failing", "hash"],
      [[k, v["lines"], v["with_a_number"], v["within_10"], v["within_5"], v["safe_rows"], v["safe_precision_pct"], v["invariants_failing"], v["hash"]] for k, v in d["scores"].items()]) + [""]
    
  f = d["folders"]
  L += ["## How to reproduce", "", "From `backend/`, with `PYTHONPATH=.` and `TRACE_CASES_DIR` set:", "",
    f"`python -m app.modules.drawings_boq.takeoff.proof.measure --before {f['before'] or '<before_H>'}`", "",
    f"It runs the check (the gates and the scores of the checked cases), the reading score, the benchmark and this report, in that order, into the folders {', '.join(v for k, v in cfg['folders'].items())} under `--work` (default h_out); a step whose output is there is not run again, `--fresh` runs every step again, and `final_report --score <work>/{cfg['folders']['score']} --bench <work>/{cfg['folders']['bench']} --reading <work>/{cfg['folders']['reading']} --before {f['before'] or '<before_H>'} --publish` writes this report again from those folders alone.", ""]
  return "\n".join(L)

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="The numbers of the final report: gates, before and after, benchmark, AI cost, registry and overrides, first sight and what is open.")
  ap.add_argument("--score", help="the folder written by proof.check or proof.score --out")
  ap.add_argument("--bench", help="the folder written by the benchmark (rows.jsonl)")
  ap.add_argument("--reading", help="the folder written by proof.reading score (reading_score.json)")
  ap.add_argument("--before", help="the before_H folder, laid out like the three folders above")
  ap.add_argument("--out", help="write the markdown here instead of printing it")
  ap.add_argument("--publish", action="store_true", help="write docs/packs/H_RESULT.md")
  ap.add_argument("--require-gates", action="store_true", help="exit 1 unless the required gates are green")
  a = ap.parse_args(argv)
  d = collect(a.score, a.bench, a.reading, a.before)
  text = render(d)
  out = a.out or (os.path.join(os.path.dirname(PACKS), d["cfg"]["result_file"]) if a.publish else None)
  if out:
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
      fh.write(text)
  else:
    sys.stdout.write(text + "\n")
  return 1 if (a.require_gates and not d["check"]["green"]) or (d["check"]["found"] and d["check"]["red"]) else 0

if __name__ == "__main__":
  raise SystemExit(main())
