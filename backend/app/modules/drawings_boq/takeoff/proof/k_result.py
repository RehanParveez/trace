from __future__ import annotations
import argparse
import collections
import json
import os
import sys
import yaml
from app.core.config import settings
from app.modules.drawings_boq.takeoff.ai_reader import cache as CACHE
from app.modules.drawings_boq.takeoff.ai_reader import cost as COST
from app.modules.drawings_boq.takeoff.proof import final_report as FR
from app.modules.drawings_boq.takeoff.proof import h_numbers as HN
from app.modules.drawings_boq.takeoff.proof import i_result as IR
from app.modules.drawings_boq.takeoff.proof import standards_draft as SD
from app.modules.drawings_boq.takeoff.proof.bench import offices as OFF
from app.modules.drawings_boq.takeoff.proof.bench import report as RP
from app.modules.drawings_boq.takeoff.proof.bench import sets as ST
from app.modules.drawings_boq.takeoff.proof.reading import param_truth as PT

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "measure_k.yaml")
BEFORE_PATH = os.path.join(HERE, "before_k.yaml")
DOCS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "..", "..", "docs", "packs"))
STATES = ("MEASURED", "ASKED", "ASSUMED", "NOT_READ")
NOT_RECORDED = "not recorded"

def load(path: str = PATH) -> dict:
  with open(path, encoding="utf-8") as fh:
    return yaml.safe_load(fh) or {}

def _f(x):
  try:
    return None if x in (None, "") else float(x)
  except (TypeError, ValueError):
    return None

def pct(x, digits: int = 1) -> str:
  return "-" if x is None else f"{100.0 * x:.{digits}f}%"

def ratio(a, b):
  return None if not b else a / b

def arrow(was, now) -> str:
  return f"{'-' if was is None else was} -> {'-' if now is None else now}"

def history_split(rows: list, before_commit: str | None) -> tuple:
  if not before_commit:
    return None, None
  at = [i for i, r in enumerate(rows) if str(r.get("commit") or "").startswith(before_commit)]
  if not at:
    return None, None
  return rows[:at[-1] + 1], rows[at[-1] + 1:]

def first_sight(rows: list) -> dict:
  out: dict = {}
  for r in rows or []:
    if r.get("run") != OFF.FIRST_RUN:
      continue
    out[r["set"]] = {"commit": r.get("commit"), "date": r.get("date"), "money": _f(r.get("money_pkr")), "within": _f(r.get("within_pkr")), "confirmed": _f(r.get("confirmed_items")), "unpriced": _f(r.get("unpriced_items")),
      "drawn": _f(r.get("drawn_money_pkr")), "drawn_within": _f(r.get("drawn_within_pkr")), "assumed": _f(r.get("assumed_money_pkr")), "assumed_within": _f(r.get("assumed_within_pkr"))}
  for v in out.values():
    v["priced"] = None if v["confirmed"] is None or v["unpriced"] is None else int(v["confirmed"] - v["unpriced"])
  return out

def money_rows(before: dict, after: dict, offices: dict) -> list:
  rows = []
  for name in sorted(set(before) | set(after)):
    b, a = before.get(name), after.get(name)
    rows.append({"set": name, "office": offices.get(name, "-"), "before": b, "after": a})
  return rows

def money_by_office(rows: list) -> list:
  out: dict = {}
  for r in rows:
    for side in ("before", "after"):
      v = r[side]
      if not v or v["money"] is None:
        continue
      o = out.setdefault(r["office"], {"before": collections.Counter(), "after": collections.Counter()})[side]
      for k in ("money", "within"):
        o[k] += v[k] or 0.0
      if v["assumed"] is not None and v["drawn"] is not None:
        for k in ("drawn", "drawn_within", "assumed", "assumed_within"):
          o[k] += v[k] or 0.0
        o["split_money"] += v["money"]
      o["sets"] += 1
  return [{"office": k, "before": v["before"], "after": v["after"]} for k, v in sorted(out.items())]

def states_of(rows: list | None, run: str = RP.PRODUCT) -> dict:
  if rows is None:
    return {}
  out: dict = {}
  for r in rows:
    if r.get("run") != run or r.get("state") not in STATES:
      continue
    out.setdefault(r["set"], collections.Counter())[r["state"]] += 1
  return {k: dict(v) for k, v in sorted(out.items())}

def param_of(doc: dict | None) -> dict:
  if not doc:
    return {}
  sets, offices = [], {}
  for s in doc.get("sets") or []:
    t = s["score"]["total"]
    sets.append({"set": s["set"], "office": s["office"], "unseen": bool(s.get("unseen")), "printed": t["printed"], "hit": t["hit"], "wrong": t["wrong"], "missed": t["missed"], "vector": t["vector"],
      "not_printed": t["not_printed"], "clean": t["clean"], "invented": t["invented"], "unchecked": s["score"]["unchecked"]})
    o = offices.setdefault(s["office"], collections.Counter())
    for k in ("printed", "hit", "not_printed", "clean", "invented", "unchecked"):
      o[k] += sets[-1][k]
  return {"sets": sets, "offices": {k: dict(v) for k, v in sorted(offices.items())}, "verdict": doc.get("verdict") or PT.verdict(doc["sets"])}

def sanity_of(doc: dict | None) -> dict:
  return {k: {"covered_sft": v.get("covered_sft"), "ratios": {r["id"]: {k2: r[k2] for k2 in ("name", "unit", "trace", "workbook", "range", "trace_flag", "workbook_flag")} for r in v.get("ratios") or []}} for k, v in sorted((doc or {}).items())}

def ai_of(sets_doc: dict) -> dict:
  cases = IR.ai_answers(sets_doc)
  drafts = CACHE.read_all(SD.AI_CASE)
  d = COST.summarise(drafts)
  searches = sum(int(e.get("searches") or 0) for e in drafts)
  usd = d["usd"] + searches * SD.SEARCH_USD
  return {"cases": {"requests": cases["requests"], "accepted": cases["accepted"], "pkr": cases["pkr"], "pkr_per_accepted": cases["pkr_per_accepted"]},
    "drafts": {"requests": d["requests"], "searches": searches, "usd": round(usd, 4), "pkr": round(usd * float(settings.ai_usd_to_pkr), 2)}, "unpriced_models": sorted(set(cases["unpriced_models"]) | set(d["unpriced_models"]))}

def snapshot(bench: str | None, param: str | None, reading: str | None, commit: str, sets_doc: dict | None = None) -> dict:
  sets_doc = ST.load() if sets_doc is None else sets_doc
  rdoc = HN.read_json(os.path.join(reading, "reading_score.json")) if reading else None
  return {"commit": commit, "states": states_of(HN.bench_rows(bench)), "param": param_of(HN.read_json(param) if param else None),
    "sanity": sanity_of(HN.read_json(os.path.join(bench, "sanity.json")) if bench else None), "truth_checked": IR.truth_checked(rdoc), "ai": ai_of(sets_doc), "rows_sha": IR.rows_sha_of(bench)}

def stored_before(path: str | None = None) -> dict | None:
  path = path or BEFORE_PATH
  if not os.path.isfile(path):
    return None
  with open(path, encoding="utf-8") as fh:
    return yaml.safe_load(fh) or None

def collect(bench, param, reading, score, history_path, before_commit, before_dirs: dict | None, cfg: dict | None = None, commit: str | None = None) -> dict:
  cfg = load() if cfg is None else cfg
  sets_doc = ST.load()
  commit = commit or RP.commit_id()
  after = snapshot(bench, param, reading, commit, sets_doc)
  if before_dirs:
    was = snapshot(before_dirs.get("bench"), before_dirs.get("param"), before_dirs.get("reading"), before_commit or NOT_RECORDED, sets_doc)
    was_from = "folders " + ", ".join(str(v) for v in before_dirs.values() if v)
  else:
    was, was_from = stored_before(), "before_k.yaml"
  hist = OFF.history_rows(history_path)
  hb, ha = history_split(hist, before_commit)
  offices = {n: (r or {}).get("office") for n, r in (sets_doc.get("sets") or {}).items()}
  fs_before, fs_after = first_sight(hb or []), first_sight(ha if ha is not None else hist)
  try:
    packs = FR.pack_summary()
  except (OSError, KeyError, ValueError):
    packs = {"packs": []}
  check = HN.gates(HN.read_json(os.path.join(score, "check.json")) if score else None, cfg["required_gates"])
  return {"cfg": cfg, "commit": commit, "before_commit": before_commit, "after": after, "before": was, "before_from": was_from, "history_lines": len(hist), "history_split": hb is not None,
    "money": money_rows(fs_before, fs_after, offices), "check": check, "k_packs": [k for k in cfg["k_packs"] if k in packs["packs"]], "packs": packs}

def money_table(rows: list) -> list:
  head = ["Set", "Office", "Items priced", "Money accuracy", "Drawn money accuracy", "Assumed money accuracy", "Assumed share of money", "Commit"]
  body = []
  for r in rows:
    b, a = r["before"], r["after"]
    def acc(v, k, w):
      return None if not v or v.get(k) is None else ratio(v[w], v[k])
    body.append([r["set"], r["office"], arrow(None if not b else b["priced"], None if not a else a["priced"]),
      arrow(*[None if x is None else pct(x) for x in (acc(b, "money", "within"), acc(a, "money", "within"))]),
      arrow(*[None if x is None else pct(x) for x in (acc(b, "drawn", "drawn_within"), acc(a, "drawn", "drawn_within"))]),
      arrow(*[None if x is None else pct(x) for x in (acc(b, "assumed", "assumed_within"), acc(a, "assumed", "assumed_within"))]),
      arrow(*[None if x is None else pct(x) for x in (None if not b or not b["money"] or b["assumed"] is None else b["assumed"] / b["money"], None if not a or not a["money"] or a["assumed"] is None else a["assumed"] / a["money"])]),
      f"{(b or {}).get('commit', '-')} -> {(a or {}).get('commit', '-')}"])
  return FR.table(head, body)

def office_table(rows: list) -> list:
  def cell(v, k, w):
    return "-" if not v or not v.get(k) else pct(v[w] / v[k])
  def both(o, k, w):
    return f"{cell(o['before'], k, w)} -> {cell(o['after'], k, w)}"
  body = [[o["office"], f"{o['before'].get('sets', 0)} -> {o['after'].get('sets', 0)}", both(o, "money", "within"), both(o, "drawn", "drawn_within"), both(o, "assumed", "assumed_within"), both(o, "split_money", "assumed")] for o in rows]
  return FR.table(["Office", "Sets scored", "Money accuracy", "Drawn money accuracy", "Assumed money accuracy", "Assumed share of money"], body)

def states_table(was: dict, now: dict) -> list:
  body = []
  for name in sorted(set(was) | set(now)):
    b, a = was.get(name), now.get(name)
    body.append([name, *[arrow(None if b is None else b.get(s, 0), None if a is None else a.get(s, 0)) for s in STATES]])
  return FR.table(["Set (product run)", *STATES], body)

def param_table(p: dict) -> list:
  body = [[s["set"], s["office"] + (" unseen" if s["unseen"] else ""), f"{s['hit']} of {s['printed']}", pct(ratio(s["hit"], s["printed"])), s["wrong"], s["missed"], f"{s['clean']} of {s['not_printed']}", s["invented"], s["unchecked"]] for s in p.get("sets") or []]
  return FR.table(["Set", "Office", "PRINTED hit", "Recall", "Wrong", "Missed", "NOT_PRINTED clean", "Invented", "Rows unchecked (not scored)"], body)

def param_offices(was: dict, now: dict) -> list:
  body = []
  for off in sorted(set((was or {}).get("offices") or {}) | set((now or {}).get("offices") or {})):
    b, a = ((was or {}).get("offices") or {}).get(off), ((now or {}).get("offices") or {}).get(off)
    r = lambda v: None if not v or not v["printed"] else pct(v["hit"] / v["printed"])
    q = lambda v: None if not v or not v["not_printed"] else pct(v["clean"] / v["not_printed"])
    body.append([off, arrow(r(b), r(a)), arrow(q(b), q(a)), arrow(None if not b else b["printed"], None if not a else a["printed"]), arrow(None if not b else b["unchecked"], None if not a else a["unchecked"])])
  return FR.table(["Office", "Recall on PRINTED rows", "Precision on NOT_PRINTED rows", "PRINTED rows scored", "Rows unchecked"], body)

def sanity_table(was: dict, now: dict) -> list:
  body = []
  for name in sorted(now):
    for rid, r in now[name]["ratios"].items():
      w = ((was or {}).get(name) or {}).get("ratios", {}).get(rid)
      rng = "-" if not r["range"] else f"{r['range'][0]:g} to {r['range'][1]:g}"
      g = lambda x: "-" if x is None else f"{x:g}"
      body.append([name, f"{rid} {r['name']}", r["unit"], arrow(None if not w else w["trace"], r["trace"]), g(r["workbook"]), rng, r["trace_flag"] if r["range"] else "no range yet", r["workbook_flag"] if r["range"] else "no range yet"])
  return FR.table(["Set", "Ratio", "Unit", "Trace (before -> after)", "Workbook", "His range", "Trace against range", "Workbook against range"], body)

def render(d: dict) -> str:
  cfg, a, b, chk = d["cfg"], d["after"], d["before"], d["check"]
  L = ["# K result", "",
    f"After: commit `{d['commit']}`. Before: " + (f"commit `{b['commit']}`" if b and b.get("commit") else "no before was found") + f", read from {d['before_from']}"
    + (f"; history lines up to commit `{d['before_commit']}` are before, those after it are after." if d["history_split"] else (f"; no history line has commit `{d['before_commit']}`, so the money table has no before." if d["before_commit"] else "; no --before-commit was given, so every history line counts as after and the money table has no before.")),
    "Every number below is read from the folders and the history file named at the end and is reproduced by the command at the end. A cell reads `before -> after`; a dash is a figure that was not recorded.", ""]
  L += ["## Gates", ""]
  if not chk["found"]:
    L += [f"No check.json in the score folder: the check was not run, so no gate is shown green. Required: {', '.join(str(g) for g in cfg['required_gates'])}.", ""]
  else:
    L += FR.table(["Gate", "Result", "Checks under it"], [[g, "green" if chk["by_gate"][g]["ok"] else "RED", chk["by_gate"][g]["checks"]] if g in chk["by_gate"] else [g, "NOT RUN", 0] for g in cfg["required_gates"]])
    L += ["", f"Gates {', '.join(str(g) for g in cfg['required_gates'])}: **{'green' if chk['green'] else 'NOT green'}**. The whole check ran {chk['checks']} checks, {chk['failed']} failed.", ""]
    L += [f"- Gate {g}: {n}" for g in chk["red"] for n in chk["by_gate"][g]["notes"]] + ([""] if chk["red"] else [])
  L += ["## Packs", "", f"K packs with a generality record: {', '.join(d['k_packs']) or 'none'} (of {', '.join(cfg['k_packs'])}). " + cfg["packs_note"], ""]
  L += ["## Parameter reading (K-3)", "", "Recall on the PRINTED rows and precision on the NOT_PRINTED rows of the parameter truth, counted on rows a person has checked; unchecked rows are counted apart and never scored.", ""]
  if not a["param"]:
    L += ["No parameter score was given (`--param`, the file written by `param_truth score --json`).", ""]
  else:
    L += param_offices(b.get("param") if b else None, a["param"]) + [""] + param_table(a["param"]) + [""]
    v = a["param"].get("verdict") or {}
    if v:
      L += [f"K-3 targets: recall on {PT.MIN_OFFICES} offices {'met' if v['recall_offices_met'] else 'NOT met'} ({', '.join(v['recall_offices']) or 'none'}); on an unseen set {'met' if v['recall_unseen_met'] else 'NOT met'}; precision " + ("no NOT_PRINTED rows yet" if v["precision"] is None else f"{v['precision']:.1%} {'met' if v['precision_met'] else 'NOT met'}") + ".", ""]

  L += ["## Items priced, first-sight money accuracy, drawn and assumed (K-2, K-4, K-6)", "",
    "Items priced is the confirmed items of the workbook that bench.rates gave a rate. Money accuracy is the money within tolerance over the money of the confirmed items, on the first (product) run of each set, split by what Trace's number rests on. "
    "The assumed share is assumed money over all money: a pack that raised accuracy by assuming more shows here.", ""]
  if not d["money"]:
    L += ["The history file holds no first-run line.", ""]
  else:
    L += money_table(d["money"]) + [""] + ["Per office, money-weighted:", ""] + office_table(money_by_office(d["money"])) + [""]
  L += ["## Lines by ledger state (K-5)", "", "Entries of each set's product run by state; NOT_APPLICABLE entries are not lines of the project and are left out.", ""]
  if not a["states"]:
    L += ["No benchmark rows in the bench folder.", ""]
  else:
    L += states_table((b or {}).get("states") or {}, a["states"]) + [""]
  L += ["## Sanity ratios against his ranges (K-6)", ""]
  if not a["sanity"]:
    L += ["No sanity.json in the bench folder: the benchmark was run before K-9 or the sanity ratios have no schedule.", ""]
  else:
    L += sanity_table((b or {}).get("sanity") or {}, a["sanity"]) + [""]
  tc, tb = a["truth_checked"], (b or {}).get("truth_checked") or {}
  L += ["## Checked truth rows", ""]
  L += [("Element truth rows a person has checked: " + (f"{tb['checked_rows']} of {tb['truth_rows']}" if tb else "not recorded") + " -> " + (f"{tc['checked_rows']} of {tc['truth_rows']} ({pct(tc['checked_share'])})" if tc else "-") + ".")]
  p = a["param"]
  if p:
    chk_rows = sum(s["printed"] + s["vector"] + s["not_printed"] for s in p["sets"])
    L += [f"Parameter truth rows a person has checked and scored: {chk_rows}; rows not yet checked and not scored: {sum(s['unchecked'] for s in p['sets'])}."]
  L += ["", "A recall figure is only as good as this share.", ""]
  ai = a["ai"]
  L += ["## AI spend", "", f"Case folders' AI answers: {ai['cases']['requests']} request(s), {ai['cases']['accepted']} accepted, {ai['cases']['pkr']:.2f} PKR" + ("" if ai["cases"]["pkr_per_accepted"] is None else f", {ai['cases']['pkr_per_accepted']:.2f} PKR per accepted answer")
    + f". K-8 web drafts: {ai['drafts']['requests']} request(s), {ai['drafts']['searches']} search(es), {ai['drafts']['usd']:.4f} USD ({ai['drafts']['pkr']:.2f} PKR)." + (f" Models with no price (cost counted as 0): {', '.join(ai['unpriced_models'])}." if ai["unpriced_models"] else "")
    + f" Before: " + (f"{b['ai']['cases']['pkr']:.2f} PKR in the case folders" if b and b.get("ai") else "not recorded") + ".", ""]
  L += ["## How to reproduce", "", "From `backend/`, with `PYTHONPATH=.` and `TRACE_CASES_DIR` set:", "",
    "`python -m app.modules.drawings_boq.takeoff.proof.k_result --bench bench_out --param param_score.json --reading reading_out --score score_out --before-commit <commit before K-1> --publish`", "",
    "`--before <folder>` reads a before laid out like `bench_out`, `reading_out` and `param_score.json` inside it; without it `proof/before_k.yaml` is used, written once at the commit before K-1 by `--record-before` with the same three arguments. "
    "The money table reads `bench/history.csv` (`--history`), cut after the last line of `--before-commit`.", ""]
  return "\n".join(L)

def main(argv: list | None = None) -> int:
  cfg = load()
  ap = argparse.ArgumentParser(description="The numbers of Build File K's result: gates, parameter recall and precision, items priced, first-sight money accuracy drawn and assumed, lines by ledger state, sanity ratios, checked truth, AI spend; each before and after.")
  ap.add_argument("--bench", help="the folder written by the benchmark (rows.jsonl, sanity.json)")
  ap.add_argument("--param", help="the file written by param_truth score --json")
  ap.add_argument("--reading", help="the folder written by proof.reading score (reading_score.json)")
  ap.add_argument("--score", help="the folder written by proof.check (check.json)")
  ap.add_argument("--history", default=OFF.HISTORY_PATH, help="the benchmark's history.csv")
  ap.add_argument("--before-commit", help="the commit before K-1: history lines up to its last line are before, later lines are after")
  ap.add_argument("--before", help="a folder laid out like the ones above, recorded at the commit before K-1; without it before_k.yaml is used")
  ap.add_argument("--out", help="write the markdown here instead of printing it")
  ap.add_argument("--publish", action="store_true", help="write docs/packs/" + cfg["result_file"])
  ap.add_argument("--record-before", action="store_true", help="write the figures of --bench, --param and --reading as before_k.yaml (run this at the commit before K-1)")
  ap.add_argument("--require-gates", action="store_true", help="exit 1 unless the required gates are green")
  a = ap.parse_args(argv)
  
  if a.record_before:
    snap = snapshot(a.bench, a.param, a.reading, RP.commit_id())
    with open(BEFORE_PATH, "w", encoding="utf-8", newline="\n") as fh:
      fh.write("# The figures of the commit before K-1, written by k_result --record-before from the bench, parameter and reading folders recorded then.\n" + yaml.safe_dump(snap, sort_keys=True, default_flow_style=False, allow_unicode=True, width=200))
    print(f"wrote {BEFORE_PATH}: commit {snap['commit']}, {len(snap['states'])} set(s) with ledger states, {len(snap['param'].get('sets') or [])} set(s) with a parameter score")
    return 0
  before_dirs = None
  if a.before:
    before_dirs = {"bench": os.path.join(a.before, "bench_out"), "reading": os.path.join(a.before, "reading_out"), "param": os.path.join(a.before, "param_score.json")}
  d = collect(a.bench, a.param, a.reading, a.score, a.history, a.before_commit, before_dirs, cfg)
  text = render(d)
  out = a.out or (os.path.join(DOCS, cfg["result_file"]) if a.publish else None)
  if out:
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
      fh.write(text)
  else:
    sys.stdout.write(text + "\n")
  chk = d["check"]
  return 1 if (a.require_gates and not chk["green"]) or (chk["found"] and chk["red"]) else 0

if __name__ == "__main__":
  sys.exit(main())
