from __future__ import annotations
import argparse
import collections
import json
import os
import sys
import yaml
from app.modules.drawings_boq.takeoff.proof.reading import formats as F
from app.modules.drawings_boq.takeoff.proof.reading import sets as S

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "mep_result.yaml")
DOCS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "..", "..", "docs", "packs"))

def load(path: str = PATH) -> dict:
  with open(path, encoding="utf-8") as fh:
    return yaml.safe_load(fh) or {}

def pct(x, digits: int = 1) -> str:
  return "-" if x is None else f"{100.0 * x:.{digits}f}%"

def truth_status(cfg: dict, cases_dir: str | None = None, root: str | None = None) -> list:
  refs = S.find_sets(cases_dir, root) if root else S.find_sets(cases_dir)
  out = []
  for ref in refs:
    if ref.link:
      continue
    ts = F.load_set(ref.truth_folder)
    per = {}
    for c in cfg["classes"]:
      rows = [e for e in ts.elements if getattr(e.cls, "value", e.cls) == c and e.truth is not None]
      truth = [e for e in rows if not F.is_draft(e.truth)]
      checked = sum(1 for e in truth if e.truth.checked is True)
      per[c] = {"rows": len(rows), "truth": len(truth), "draft": len(rows) - len(truth), "checked": checked, "share": None if not truth else round(checked / len(truth), 4)}
    out.append({"set": ts.document.alias, "office": ref.office, "split": ts.document.split.value.lower(), "classes": per})
  return sorted(out, key=lambda s: s["set"])

def fixture_rows(score: dict | None, status: list, cfg: dict) -> list:
  by_set = ((score or {}).get("metrics") or {}).get("by_set") or {}
  cls, need = cfg["fixture_class"], float(cfg["min_checked_share"])
  out = []
  for s in status:
    c = s["classes"].get(cls) or {}
    if not c.get("truth"):
      continue
    m = by_set.get(f"{s['set']}|{cls}")
    scored = bool(m) and c["share"] is not None and c["share"] >= need - 1e-9
    out.append({"set": s["set"], "office": s["office"], "truth": c["truth"], "checked": c["checked"], "share": c["share"], "scored": scored, "recall": m.get("recall") if scored else None,
      "ci": m.get("recall_ci") if scored else None, "in_score": bool(m)})
  return out

def verdict(fixtures: list, legend: dict | None, cfg: dict) -> dict:
  hit = sorted({f["office"] for f in fixtures if f["scored"] and f["recall"] is not None and f["recall"] >= float(cfg["fixture_recall_target"])})
  return {"fixture_offices": hit, "fixture_met": len(hit) >= int(cfg["fixture_offices_needed"]), "legend_met": None if not legend else legend["counted"] >= int(cfg["legend_rows_target"])}

def legend_of(coverage: str | None, counted: int | None, rows: int | None) -> dict | None:
  if coverage:
    with open(coverage, encoding="utf-8") as fh:
      c = json.load(fh)
    return {"counted": int(c["counted"]), "rows": int(c["legend_symbols"]), "reasons": dict(c.get("reasons") or {}), "from": coverage}
  if counted is not None and rows is not None:
    return {"counted": int(counted), "rows": int(rows), "reasons": {}, "from": "--legend-counted and --legend-rows"}
  return None

def render(cfg: dict, status: list, fixtures: list, legend: dict | None, v: dict) -> str:
  L = ["# MEP result", "",
    "Read from the truth folders (what a person has checked) and from the files named at the end. A figure that rests on unchecked truth is not printed as a score.", "",
    "## Checked truth by class", "", "| Set | Office | " + " | ".join(f"{c} checked / truth (drafts)" for c in cfg["classes"]) + " |", "|---|---|" + "---|" * len(cfg["classes"])]

  for s in status:
    L.append(f"| {s['set']} | {s['office']} | " + " | ".join(f"{s['classes'][c]['checked']} / {s['classes'][c]['truth']} ({s['classes'][c]['draft']})" for c in cfg["classes"]) + " |")
  tot = collections.Counter()
  for s in status:
    for c in cfg["classes"]:
      tot[c + "|checked"] += s["classes"][c]["checked"]
      tot[c + "|truth"] += s["classes"][c]["truth"]
  L += ["", "Total checked of truth rows: " + ", ".join(f"{c} {tot[c + '|checked']} of {tot[c + '|truth']}" for c in cfg["classes"]) + ".", ""]
  L += ["## Electrical legend rows counted", ""]
  if not legend:
    L += ["No coverage was given (`--coverage` with the dictionary `extract.electrical.coverage(rows)` returns, as JSON, or `--legend-counted N --legend-rows M`).", ""]
  else:
    pc = [s["classes"][cfg["point_class"]] for s in status if s["classes"][cfg["point_class"]]["truth"]]
    checked = sum(p["checked"] for p in pc)
    truth = sum(p["truth"] for p in pc)
    L += [f"{legend['counted']} of {legend['rows']} legend rows are counted on the plan pages; target {cfg['legend_rows_target']}: **{'met' if v['legend_met'] else 'NOT met'}**."
      + (" Reasons for the rest: " + ", ".join(f"{k} {n}" for k, n in sorted(legend["reasons"].items())) + "." if legend["reasons"] else ""),
      f"The count is a count of rows that found a hit; it is not confirmed against truth until the {cfg['point_class']} rows are checked: {checked} of {truth} are.", ""]
  L += [f"## {cfg['fixture_class']} recall", "", "| Set | Office | Truth rows | Checked | Result |", "|---|---|---|---|---|"]
  for f in fixtures:
    res = (f"{pct(f['recall'])} (95% interval {pct(f['ci'][0])} to {pct(f['ci'][1])})" if f["scored"] and f["ci"] else pct(f["recall"]) if f["scored"] else
      f"not scored: {f['checked']} of {f['truth']} rows checked, {pct(cfg['min_checked_share'], 0)} needed" + ("" if f["in_score"] else "; and no score row for this set"))
    L.append(f"| {f['set']} | {f['office']} | {f['truth']} | {f['checked']} | {res} |")
  if not fixtures:
    L.append("| none | | | | no set has fixture truth |")
  L += ["", f"Target {pct(cfg['fixture_recall_target'], 0)} on {cfg['fixture_offices_needed']} offices: **{'met' if v['fixture_met'] else 'NOT met'}** (offices at target: {', '.join(v['fixture_offices']) or 'none'}).", ""]
  L += ["## How to reproduce", "", "From `backend/`, with `PYTHONPATH=.` and `TRACE_CASES_DIR` set: `python -m app.modules.drawings_boq.takeoff.proof.mep_result --score reading_out --coverage coverage.json --publish`. "
    "`reading_out` is the folder `proof.reading score` wrote (it holds `reading_score.json`).", ""]
  return "\n".join(L)

def main(argv: list | None = None) -> int:
  cfg = load()
  ap = argparse.ArgumentParser(description="MEP result: checked truth by class, electrical legend rows counted, plumbing fixture recall on checked truth, against the K-7 targets.")
  ap.add_argument("--score", help="the folder written by proof.reading score (reading_score.json)")
  ap.add_argument("--coverage", help="the electrical coverage dictionary as a JSON file")
  ap.add_argument("--legend-counted", type=int)
  ap.add_argument("--legend-rows", type=int)
  ap.add_argument("--cases-dir")
  ap.add_argument("--out")
  ap.add_argument("--publish", action="store_true", help="write docs/packs/" + cfg["result_file"])
  ap.add_argument("--require", action="store_true", help="exit 1 unless both targets are met")
  a = ap.parse_args(argv)
  
  score = None
  if a.score:
    with open(os.path.join(a.score, "reading_score.json"), encoding="utf-8") as fh:
      score = json.load(fh)
  status = truth_status(cfg, a.cases_dir)
  fixtures = fixture_rows(score, status, cfg)
  legend = legend_of(a.coverage, a.legend_counted, a.legend_rows)
  v = verdict(fixtures, legend, cfg)
  text = render(cfg, status, fixtures, legend, v)
  out = a.out or (os.path.join(DOCS, cfg["result_file"]) if a.publish else None)
  if out:
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
      fh.write(text)
  else:
    sys.stdout.write(text + "\n")
  return 1 if a.require and not (v["fixture_met"] and v["legend_met"]) else 0

if __name__ == "__main__":
  sys.exit(main())
