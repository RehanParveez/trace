from __future__ import annotations
import argparse
import collections
import json
import os
import re
import sys
import yaml
from app.modules.drawings_boq.takeoff.ai_reader import cache as CACHE
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.proof import final_report as FR
from app.modules.drawings_boq.takeoff.proof import h_numbers as HN
from app.modules.drawings_boq.takeoff.proof.bench import offices as OFF
from app.modules.drawings_boq.takeoff.proof.bench import report as RP
from app.modules.drawings_boq.takeoff.proof.bench import sets as ST
from app.modules.drawings_boq.takeoff.proof.reading import sets as RS

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "measure_i.yaml")
BEFORE_PATH = os.path.join(HERE, "before_i.yaml")
CONFIDENCE = os.path.join(HERE, "..", "..", "..", "..", "engine", "catalogue", "confidence.yaml")
DOCS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "..", "..", "docs", "packs"))
NO_STAGE = "no stage"

def load(path: str = PATH) -> dict:
  with open(path, encoding="utf-8") as fh:
    return yaml.safe_load(fh) or {}

def stages_of(doc: dict | None, splits: list) -> dict:
  if not doc:
    return {}
  out: dict = {s: {"truth": 0, "not_matched": 0, "by_stage": {}} for s in splits}
  for o in doc.get("outcomes") or []:
    s = str(o["split"]).lower()
    if o.get("side") != "truth" or s not in out:
      continue
    out[s]["truth"] += 1
    if o["outcome"] != "MATCHED_OK":
      out[s]["not_matched"] += 1
      k = o.get("stage") or NO_STAGE
      out[s]["by_stage"][k] = out[s]["by_stage"].get(k, 0) + 1
  return out

def offices_of(doc: dict | None, refs: dict) -> dict:
  if not doc:
    return {}
  office_by_alias = {s["alias"]: refs.get(str(s["key"]), RS.UNKNOWN_OFFICE) for s in doc.get("sets") or []}
  out: dict = {}
  
  for o in doc.get("outcomes") or []:
    slot = out.setdefault(office_by_alias.get(o["set"], RS.UNKNOWN_OFFICE), {"truth": 0, "matched": 0, "silent_wrong": 0, "sets": set()})
    slot["sets"].add(o["set"])
    if o.get("side") == "truth":
      slot["truth"] += 1
      slot["matched"] += 1 if o["outcome"] in ("MATCHED_OK", "MATCHED_WRONG_VALUE") else 0
    slot["silent_wrong"] += 1 if o["outcome"] in ("MATCHED_WRONG_VALUE", "INVENTED_SILENT") else 0
  return {k: {**v, "sets": sorted(v["sets"])} for k, v in sorted(out.items())}

def regions_of(doc: dict | None) -> dict:
  if not doc or not doc.get("regions"):
    return {}
  out: dict = {"by_text_type": {}, "by_kind": {}, "sets": 0}
  for r in doc["regions"].values():
    out["sets"] += 1
    for family in ("by_text_type", "by_kind"):
      for k, v in (r.get(family) or {}).items():
        slot = out[family].setdefault(k, {"truth": 0, "FOUND": 0, "MERGED": 0, "SPLIT": 0, "MISSED": 0})
        for f in slot:
          slot[f] += int(v.get(f) or 0)
  return {k: (dict(sorted(v.items())) if isinstance(v, dict) else v) for k, v in out.items()}

def truth_checked(doc: dict | None) -> dict:
  every = [s.get("truth_quality") for s in (doc or {}).get("sets") or []]
  rows = [r for r in every if r is not None]
  if not rows:
    return {}
  total, checked = sum(int(r.get("truth_rows") or 0) for r in rows), sum(int(r.get("checked_rows") or 0) for r in rows)
  return {"truth_rows": total, "checked_rows": checked, "checked_share": None if not total else round(checked / total, 4), "sets": len(rows), "sets_without": len(every) - len(rows),
    "status": dict(sorted(collections.Counter(str(r.get("status")) for r in rows).items()))}

def bench_sides(rows: list | None, groups: list, only: list | None = None) -> list:
  if rows is None:
    return []
  if only is not None:
    rows = [r for r in rows if r["set"] in only]
  out = []
  
  sets, sections = sorted({r["set"] for r in rows}), sorted({r["section"] for r in rows})
  for run in (RP.PRODUCT, RP.PROOF):
    for name in sets:
      out.append({"kind": "set", "set": name, "run": run, "stats": HN.side(rows, run, lambda r, n=name: r["set"] == n)})
      for g in groups:
        out.append({"kind": "group", "set": name, "group": g, "run": run, "stats": HN.side(rows, run, lambda r, n=name, gg=g: r["set"] == n and r["group"] == gg)})
    for sec in sections:
      out.append({"kind": "section", "section": sec, "run": run, "stats": HN.side(rows, run, lambda r, s=sec: r["section"] == s)})
  return [e for e in out if e["stats"] is not None]

def rows_sha_of(bench: str | None) -> str | None:
  path = os.path.join(bench or "", "bench.md")
  if not bench or not os.path.isfile(path):
    return None
  with open(path, encoding="utf-8") as fh:
    m = re.search(r"rows\.jsonl sha256 `([0-9a-f]{64})`", fh.read(2000))
  return m.group(1) if m else None

def snapshot(score: str | None, bench: str | None, reading: str | None, cfg: dict, sets_doc: dict | None = None) -> dict:
  sets_doc = ST.load() if sets_doc is None else sets_doc
  doc = HN.read_json(os.path.join(reading, "reading_score.json")) if reading else None
  rows = HN.bench_rows(bench)
  splits = cfg["reading_splits"]
  
  refs = {r.pdf_key: r.office for r in RS.find_sets()} if doc else {}
  check = HN.gates(HN.read_json(os.path.join(score, "check.json")) if score else None, cfg["required_gates"])
  return {"check": {k: check[k] for k in ("found", "passed", "checks", "failed", "by_gate", "missing", "red", "green")},
    "scores": FR.score_summary(score) if score and os.path.isdir(score) else {},
    "reading": HN.reading_rows(doc, splits), "stages": stages_of(doc, splits), "offices": offices_of(doc, refs), "regions": regions_of(doc), "truth_checked": truth_checked(doc),
    "bench": bench_sides(rows, list((sets_doc.get("section_groups") or {}).keys())), "rows_sha": rows_sha_of(bench)}

def stored_before(path: str = BEFORE_PATH) -> dict | None:
  if not os.path.isfile(path):
    return None
  with open(path, encoding="utf-8") as fh:
    return yaml.safe_load(fh) or None

def ai_answers(sets_doc: dict, root: str = CIO.HERE) -> dict:
  from app.modules.drawings_boq.takeoff.ai_reader import cost as COST
  tasks: dict = {}
  
  for name in sorted(sets_doc.get("sets") or {}):
    for e in CACHE.read_all(os.path.join(root, name)):
      t = str(e.get("task") or "-")
      slot = tasks.setdefault(t, {"entries": [], "accepted": 0})
      slot["entries"].append(e)
      slot["accepted"] += 1 if e.get("status") == "OK" and all(v.get("passed") for v in e.get("validators") or []) else 0
  out, unpriced = {}, set()
  for t, slot in sorted(tasks.items()):
    c = COST.summarise(slot["entries"])
    unpriced.update(c["unpriced_models"])
    out[t] = {"requests": c["requests"], "accepted": slot["accepted"], "usd": round(c["usd"], 6), "pkr": round(c["pkr"], 4), "pkr_per_accepted": None if not slot["accepted"] else round(c["pkr"] / slot["accepted"], 4)}
  total_pkr, accepted = round(sum(v["pkr"] for v in out.values()), 4), sum(v["accepted"] for v in out.values())
  return {"tasks": out, "requests": sum(v["requests"] for v in out.values()), "accepted": accepted, "pkr": total_pkr, "pkr_per_accepted": None if not accepted else round(total_pkr / accepted, 4), "unpriced_models": sorted(unpriced)}

def calibration(path: str = CONFIDENCE) -> dict:
  with open(path, encoding="utf-8") as fh:
    d = yaml.safe_load(fh) or {}
  return {"shown": bool(d.get("shown")), "show_when": d.get("show_when"), "kill": d.get("kill"), "calibrated": d.get("calibrated") or {}, "classes": len(d.get("classes") or {})}

def curve(history: list, sets_doc: dict, log: dict) -> list:
  seen, out = set(), []
  for r in sorted(history, key=lambda r: (r["date"], r["set"])):
    if r["run"] != OFF.FIRST_RUN or r["set"] in seen:
      continue
    seen.add(r["set"])
    out.append({**r, "office": ((sets_doc.get("sets") or {}).get(r["set"]) or {}).get("office"), "first_sight_set": r["set"] in log})
  return out

def collect(score: str | None, bench: str | None, reading: str | None, before: str | None = None, cfg: dict | None = None) -> dict:
  cfg = load() if cfg is None else cfg
  sets_doc = ST.load()
  after = snapshot(score, bench, reading, cfg, sets_doc)
  if before:
    there = {k: os.path.join(before, v) for k, v in cfg["folders"].items()}
    was, was_from = snapshot(there["score"], there["bench"], there["reading"], cfg, sets_doc), f"folder {before}"
  else:
    was, was_from = stored_before(), "before_i.yaml"
    
  if was and was.get("bench"):
    common = sorted({e["set"] for e in was["bench"] if e["kind"] == "set"} & {e["set"] for e in after["bench"] if e["kind"] == "set"})
    after["bench"] += [{**e, "kind": "section_common"} for e in bench_sides(HN.bench_rows(bench), list((sets_doc.get("section_groups") or {}).keys()), only=common) if e["kind"] == "section"]
    after["common_sets"] = common
  history, reg = OFF.history_rows(), OFF.load()
  packs = FR.pack_summary()
  rules = FR.registry_summary()
  return {"cfg": cfg, "commit": RP.commit_id(), "after": after, "before": was, "before_from": was_from, "cal": calibration(), "ai": ai_answers(sets_doc), "history": len(history),
    "curve": curve(history, sets_doc, reg.get("set_log") or {}), "first_sight_line": FR.OFC.first_sight_line(reg, sets_doc, history), "registry": rules,
    "overrides": [{**o, "delivered": o["until"] in packs["packs"]} for o in HN.overrides_left()], "gate17": HN.gate17_exceptions(), "hit_line": FR.EXD.hit_line(FR.EXD.load()),
    "open": HN.open_groups(HN.bench_rows(bench), cfg["failures_run"], cfg["top_groups"]), "packs": packs}

def pct(x) -> str:
  return "-" if x is None else f"{100.0 * x:.1f}%"

def recall_text(r: dict | None) -> str:
  return "-" if not r else f"{r['recall']:.1%} of {r['truth']:,} truth items, {r['silent_wrong']} silent wrong"

def side_by_side(was: dict | None, now: dict | None, key: str, name) -> tuple:
  return (name(was[key]) if was and key in was else "-"), (name(now[key]) if now and key in now else "-")

def staged(s: dict | None, stage: str, cfg: dict):
  if not s:
    return "-"
  if not any(k in s["by_stage"] for k in cfg["stages"]) and s["not_matched"]:
    return "not recorded then"
  return s["by_stage"].get(stage, 0)

def measures(d: dict) -> list:
  a, b, cfg, rows = d["after"], d["before"] or {}, d["cfg"], []
  chk, chb = a["check"], (b.get("check") or {})
  rows.append(["Checks", f"{chb['checks'] - chb['failed']} of {chb['checks']} pass" if chb.get("found") else "-", f"{chk['checks'] - chk['failed']} of {chk['checks']} pass" if chk["found"] else "check not run"])
  for case, now in (a["scores"] or {}).items():
    was = (b.get("scores") or {}).get(case)
    rows.append([f"Engine hash {case}", (was or {}).get("engine_digest", "-")[:8] or "-", now["engine_digest"][:8]])
    rows.append([f"QS lines within 10% {case}", f"{was['within_10']} of {was['lines']}" if was else "-", f"{now['within_10']} of {now['lines']}"])
    
  for split in cfg["reading_splits"]:
    now, was = (a["reading"].get("splits") or {}).get(split), ((b.get("reading") or {}).get("splits") or {}).get(split)
    rows.append([f"Reading recall, {split} split", recall_text(was), recall_text(now)])
    rows.append([f"Reading hash, {split} split", (was or {}).get("hash", "-"), (now or {}).get("hash", "-")])
    sa, sb = (a["stages"] or {}).get(split), (b.get("stages") or {}).get(split)
    for stage in cfg["stages"]:
      rows.append([f"Misses at {stage}, {split} split", staged(sb, stage, cfg), "-" if not sa else sa["by_stage"].get(stage, 0)])
      
  tc, tb = a["truth_checked"], b.get("truth_checked") or {}
  rows.append(["Truth rows a person has checked", "not measured then" if not tb else f"{tb['checked_rows']} of {tb['truth_rows']}", "-" if not tc else f"{tc['checked_rows']} of {tc['truth_rows']} ({pct(tc['checked_share'])})"])
  reg = d["registry"]
  rows.append(["Rules in the registry", cfg["ix1_registry"], f"{reg['rules']} rules; status {json.dumps(reg['status'])}; default {json.dumps(reg['default'])}"])
  rows.append(["Proof overrides", cfg["ix1_overrides"], len(d["overrides"])])
  rows.append(["Gate 17 exceptions", cfg["ix1_gate17_exceptions"], d["gate17"]])
  return rows

def bench_pairs(a: dict, b: dict, kind: str, before_kind: str | None = None) -> list:
  def key(e):
    return (e["run"], e.get("set", ""), e.get("group", ""), e.get("section", ""))
  mine = {key(e): e["stats"] for e in a["bench"] if e["kind"] == kind}
  was = {key(e): e["stats"] for e in (b or {}).get("bench") or [] if e["kind"] == (before_kind or kind)}
  out = []
  for k in sorted(set(mine) | set(was)):
    now, old = mine.get(k), was.get(k)
    both = now is not None and old is not None and now["coverage"] is not None and old["coverage"] is not None
    out.append({"run": k[0], "set": k[1], "group": k[2], "section": k[3], "before": old, "after": now, "coverage_change": round(now["coverage"] - old["coverage"], 1) if both else None})
  return out

def bench_table(pairs: list, keys: list, labels: list) -> list:
  head = [*labels, "Run", "Coverage % before", "Coverage % after", "Change", "Within 10% before", "Within 10% after", "Assumed % before", "Assumed % after"]
  body = []
  for r in pairs:
    b, a = r["before"], r["after"]
    body.append([*[r[k] for k in keys], r["run"].title(), RP.fmt(None if b is None else b["coverage"]), RP.fmt(None if a is None else a["coverage"]), RP.fmt(r["coverage_change"]),
      FR.counted(b), FR.counted(a), RP.fmt(None if b is None else b["assumed_pct"]), RP.fmt(None if a is None else a["assumed_pct"])])
  return FR.table(head, body)

def render(d: dict) -> str:
  cfg, a, b = d["cfg"], d["after"], d["before"]
  chk, L = a["check"], []
  L += ["# I result", "", (f"Commit `{d['commit']}`." if d["commit"] != "no-git" else "Made from the pack tree in a workspace that is not a git checkout, so no commit is printed here; the command at the end prints it when run in the repository.") + f" Every number below is read from the folders named at the end and is reproduced by the command at the end. Build File I is the build; the before is the tree at the IX-1 commit.", ""]
  L += ["## Gates", ""]

  if not chk["found"]:
    L += [f"No check.json in the score folder: the check was not run, so no gate is shown green. Required: {', '.join(str(g) for g in cfg['required_gates'])}.", ""]
  else:
    L += FR.table(["Gate", "Result", "Checks under it"], [[g, "green" if chk["by_gate"][g]["ok"] else "RED", chk["by_gate"][g]["checks"]] if g in chk["by_gate"] else [g, "NOT RUN", 0] for g in cfg["required_gates"]])
    L += ["", f"Gates {', '.join(str(g) for g in cfg['required_gates'])}: **{'green' if chk['green'] else 'NOT green'}**." + (f" Not run: {', '.join(str(g) for g in chk['missing'])}." if chk["missing"] else "") + (f" Red: {', '.join(str(g) for g in chk['red'])}." if chk["red"] else "") + f" The whole check ran {chk['checks']} checks, {chk['failed']} failed.", ""]
    L += [f"- Gate {g}: {n}" for g in chk["red"] for n in chk["by_gate"][g]["notes"]] + ([""] if chk["red"] else [])
  L += ["## Before and after", "", f"Before: {cfg['before_note']} Read from {d['before_from']}." if b else "No before was found: the before column is dashes.", ""]
  L += FR.table(["Measure", "Before (IX-1 commit)", "After"], measures(d)) + [""]
  L += ["## By stage", "", "Truth items the reading did not match, charged to the stage that lost them (FIND the place, READ the value, JOIN the parts, MEASURE the number).", ""]
  body = []

  for split in cfg["reading_splits"]:
    now, was = (a["stages"] or {}).get(split), (b or {}).get("stages", {}).get(split) if b else None
    for label, s in (("before", was), ("after", now)):
      body.append([split, label] + (["-"] * (len(cfg["stages"]) + 3) if not s else [s["truth"], s["not_matched"], *[staged(s, st, cfg) for st in cfg["stages"]], s["by_stage"].get(NO_STAGE, 0)]))
  L += FR.table(["Split", "Run", "Truth items", "Not matched", *cfg["stages"], NO_STAGE], body) + [""]
  L += ["## By office", "", "Truth items matched (right or wrong value) over truth items, and silent-wrong reads, per design office. An office with several sets is the sum of its sets.", ""]
  body = []

  for off in sorted(set(a["offices"]) | set((b or {}).get("offices") or {})):
    now, was = a["offices"].get(off), ((b or {}).get("offices") or {}).get(off)
    rec = lambda s: "-" if not s or not s["truth"] else f"{s['matched']} of {s['truth']} ({s['matched'] / s['truth']:.1%})"
    body.append([off, ", ".join((now or was)["sets"]), rec(was), "-" if not was else was["silent_wrong"], rec(now), "-" if not now else now["silent_wrong"]])
  L += FR.table(["Office", "Sets", "Matched before", "Silent wrong before", "Matched after", "Silent wrong after"], body) + [""]
  L += ["## By text type (the region score)", ""]
  rg, rb = a["regions"], (b or {}).get("regions") or {}
  if not rg:
    L += ["No reading score with a region score in the reading folder, so there is nothing to show.", ""]
  else:
    for family, label in (("by_text_type", "Text type"), ("by_kind", "Kind of region")):
      body = []
      for k, v in rg[family].items():
        w = (rb.get(family) or {}).get(k)
        share = lambda s: "-" if not s or not s["truth"] else f"{s['FOUND']} of {s['truth']} ({s['FOUND'] / s['truth']:.1%})"
        body.append([k, share(w), share(v), v["MERGED"], v["SPLIT"], v["MISSED"]])
      L += FR.table([label, "Found before", "Found after", "Merged after", "Split after", "Missed after"], body) + [""]
    if not rb:
      L += ["The region score did not exist at the IX-1 commit, so the before column is dashes.", ""]

  tc = a["truth_checked"]
  L += ["## Truth checked", ""]
  L += ([f"{tc['checked_rows']} of {tc['truth_rows']} truth rows are checked by a person ({pct(tc['checked_share'])}) in {tc['sets']} sets{f" ({tc['sets_without']} more set carries no truth quality and is not counted)" if tc.get('sets_without') else ""}; sets by status: {json.dumps(tc['status'])}. A recall figure is only as good as this share: until it rises the reading score measures agreement with a draft truth, not accuracy."] if tc else ["The reading score carries no truth quality."]) + [""]
  L += ["## Benchmark before and after", ""]
  if not a["bench"]:
    L += ["No benchmark rows for this run: the bench folder has no rows.jsonl.", ""]
  else:
    L += [f"After: rows.jsonl sha256 `{(a['rows_sha'] or '')[:16]}`." + (f" Before: `{((b or {}).get('rows_sha') or '')[:16]}`." if b and b.get("bench") else " **No before benchmark was found**: the before columns are dashes."), ""]
    L += ["### Every set, all sections", ""] + bench_table(bench_pairs(a, b, "set"), ["set"], ["Set"]) + [""]
    L += ["### Every set by section group", ""] + bench_table(bench_pairs(a, b, "group"), ["set", "group"], ["Set", "Section group"]) + [""]
    if a.get("common_sets"):
      L += [f"### Every catalogue section, on the sets both runs have ({', '.join(a['common_sets'])})", "", "The same sets on both sides, so a change here is a change in the reading and not in which sets were run.", ""]
      L += bench_table(bench_pairs(a, b, "section_common", "section"), ["section"], ["Section"]) + [""]
    L += ["### Every catalogue section, all sets of this run", "", "The before benchmark covered fewer sets, so its columns are dashes here." if a.get("common_sets") else "", ""]
    L += bench_table(bench_pairs(a, None, "section"), ["section"], ["Section"]) + [""]
    
  cal = d["cal"]
  c = cal["calibrated"]
  L += ["## Calibration", ""]
  L += ([f"The confidence table was calibrated on {c.get('sets')} sets and {c.get('items')} items (reading hash `{str(c.get('reading_hash'))[:8]}`): High was right {pct(c.get('high_right_out_of_sample'))} out of sample on {c.get('high_items')} items ({pct(c.get('high_right_in_sample'))} in sample). Shown to clients: **{'yes' if cal['shown'] else 'no'}**; the rule is {cal['show_when']['min_items']} High items at {pct(cal['show_when']['high_right'])} out of sample, killed below {pct(cal['kill']['high_right'])}. {cal['classes']} classes have a cell."] if c else ["The confidence table is not calibrated."])
  L += ["", "The calibration did not exist at the IX-1 commit.", ""]
  ai = d["ai"]
  L += ["## AI cost per accepted answer", ""]
  if not ai["requests"]:
    L += ["No AI answer is kept in any set's ai_cache: no request was made, so the cost is 0 and the cost of an accepted answer is not defined.", ""]
  else:
    L += FR.table(["Task", "Requests", "Accepted", "PKR", "PKR per accepted"], [[t, v["requests"], v["accepted"], f"{v['pkr']:.2f}", "-" if v["pkr_per_accepted"] is None else f"{v['pkr_per_accepted']:.2f}"] for t, v in ai["tasks"].items()])
    L += ["", f"Total {ai['requests']} request(s), {ai['accepted']} accepted, {ai['pkr']:.2f} PKR" + ("" if ai["pkr_per_accepted"] is None else f", {ai['pkr_per_accepted']:.2f} PKR per accepted answer") + "." + (f" Models with no price (their cost counts as 0): {', '.join(ai['unpriced_models'])}." if ai["unpriced_models"] else ""), ""]
  L += [d["hit_line"], ""]
  L += ["## First sight", "", d["first_sight_line"], ""]
  if not d["curve"]:
    L += [f"The benchmark history holds {d['history']} line(s), none of the first (product) run of a set, so there is no curve: nothing has been scored before anyone looked at it.", ""]
  else:
    L += FR.table(["Date", "Commit", "Set", "Office", "Coverage %", "Within 10%", "In the offices register as first sight"], [[r["date"], r["commit"], r["set"], r["office"], r["coverage_pct"], f"{r['within_10']} of {r['compared']}", "yes" if r["first_sight_set"] else "no"] for r in d["curve"]]) + [""]
  reg = d["registry"]

  L += ["## Rules and overrides by status", "",
    f"- {reg['rules']} rules; status {json.dumps(reg['status'])}; default {json.dumps(reg['default'])}; kind {json.dumps(reg['kind'])}.",
    f"- Candidates whose evidence meets two offices: {', '.join(reg['two_offices_met_still_candidate']) or 'none'}; met on one office: {len(reg['one_office_met'])}; with no met evidence: {len(reg['no_evidence_met'])}.",
    f"- {len(d['overrides'])} proof override(s) left, {sum(1 for o in d['overrides'] if o['delivered'])} naming a pack that is already delivered (to settle) and {sum(1 for o in d['overrides'] if not o['delivered'])} naming one that is not:", ""]
  L += FR.table(["Set", "Rule", "Value", "Until", "Pack delivered", "Date", "Reason"], [[o["set"], o["rule"], o["value"], o["until"], "yes" if o["delivered"] else "no", o["date"], o["reason"]] for o in d["overrides"]]) + [""]
  o = d["open"]
  L += [f"## What is open: the top {len(o['shown'])} failure groups of {o['groups']} ({o['run'].lower()} run)", ""]
  if not o["groups"]:
    L += ["No failure group: the benchmark rows have none, or the benchmark was not run.", ""]
  else:
    L += FR.table(["#", "Group", "Offices", "Sets", "Items", "Rows", "Money at risk", "Owner pack"],
      [[n, g["key"], f"{g['offices']} ({','.join(g['office_letters'])})", g["sets"], len(g["items"]), g["rows"], g["money"] if g["money_at_risk"] is None else f"{g['money_at_risk']:,.0f} ({g['money']})", g["suggested_owner"]] for n, g in enumerate(o["shown"], 1)])
    L += ["", "Groups by owner: " + ", ".join(f"{k} {v}" for k, v in o["by_owner"].items()) + ".", ""]
  p = d["packs"]
  L += ["## Pack records", "", f"- {p['records']} generality records; {p['without_first_sight']} name no first-sight set; with a first-sight set: {', '.join(p['with_first_sight']) or 'none'}.", ""]
  L += ["## How to reproduce", "", "From `backend/`, with `PYTHONPATH=.` and `TRACE_CASES_DIR` set:", "", "`python -m app.modules.drawings_boq.takeoff.proof.measure_i`", "",
    "It runs the check (the gates and the scores of the checked cases), the product score, the reading score, the benchmark and this report, in that order, into " + ", ".join(cfg["folders"].values()) +
    " under `--work` (default i_out); a step whose output is there is not run again, `--fresh` runs every step again, and `python -m app.modules.drawings_boq.takeoff.proof.i_result --score ... --bench ... --reading ...` rewrites this page from the folders alone. "
    "The before column is read from `proof/before_i.yaml` (the IX-1 commit, recorded) or, with `--before <folder>`, from a folder laid out the same way.", ""]
  return "\n".join(L)

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="The numbers of Build File I's result: gates, before and after by stage, office and text type, truth checked, benchmark, calibration, AI cost per accepted answer, first sight, rules and overrides.")
  ap.add_argument("--score", help="the folder written by proof.check or proof.score --out")
  ap.add_argument("--bench", help="the folder written by the benchmark (rows.jsonl)")
  ap.add_argument("--reading", help="the folder written by proof.reading score (reading_score.json)")
  ap.add_argument("--before", help="a folder laid out like the three above, recorded at the IX-1 commit; without it before_i.yaml is used")
  ap.add_argument("--out", help="write the markdown here instead of printing it")
  ap.add_argument("--publish", action="store_true", help="write docs/packs/I_RESULT.md")
  ap.add_argument("--record-before", action="store_true", help="write the figures of --score, --bench and --reading as before_i.yaml (the IX-1 commit's figures)")
  ap.add_argument("--require-gates", action="store_true", help="exit 1 unless the required gates are green")
  a = ap.parse_args(argv)
  cfg = load()

  if a.record_before:
    snap = snapshot(a.score, a.bench, a.reading, cfg)
    with open(BEFORE_PATH, "w", encoding="utf-8", newline="\n") as fh:
      fh.write("# The figures of the IX-1 commit, written by i_result --record-before from the score, benchmark and reading folders recorded then.\n" + yaml.safe_dump(snap, sort_keys=True, default_flow_style=False, allow_unicode=True, width=200))
    print(f"wrote {BEFORE_PATH}: {len(snap['bench'])} benchmark figures, rows sha {str(snap['rows_sha'])[:16]}")
    return 0

  d = collect(a.score, a.bench, a.reading, a.before, cfg)
  text = render(d)
  out = a.out or (os.path.join(DOCS, cfg["result_file"]) if a.publish else None)
  if out:
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
      fh.write(text)
  else:
    sys.stdout.write(text + "\n")
  chk = d["after"]["check"]
  return 1 if (a.require_gates and not chk["green"]) or (chk["found"] and chk["red"]) else 0

if __name__ == "__main__":
  sys.exit(main())
