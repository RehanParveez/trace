from __future__ import annotations
import argparse
import json
import os
import sys
import yaml
from app.modules.drawings_boq.takeoff.proof import method_menu as MM

NEAR_PCT = 3.0
FAR_PCT = 10.0
INFERRED, STANDARD, DRAWING = "INFERRED", "STANDARD", "DRAWING"
FILE = "conventions.yaml"

def distance_pct(figure, qs) -> float | None:
  if figure is None or not qs:
    return None
  return abs(float(figure) - float(qs)) / abs(float(qs)) * 100.0

def rank(methods: list, qs: float) -> list:
  out = []
  for m in methods:
    d = distance_pct(m.get("figure"), qs)
    if d is not None:
      out.append({**m, "distance_pct": round(d, 2)})
  return sorted(out, key=lambda m: m["distance_pct"])

def passes(ranked: list) -> bool:
  return len(ranked) >= 2 and ranked[0]["distance_pct"] <= NEAR_PCT and ranked[1]["distance_pct"] >= FAR_PCT

def line_figures(result: dict, group: dict, line: str) -> list:
  base, out = result["baseline"], []
  for m in group["methods"]:
    src = base.get(line) if m["lines"] is None else (m["lines"].get(line) if "error" not in m["lines"] else None)
    if src and src.get("trace") is not None:
      out.append({"value": m["value"], "label": m["label"], "figure": round(float(src["trace"]), 3), "current": m["lines"] is None})
  return out

def rows_of(result: dict) -> list:
  base, out = result["baseline"], []
  for g in result["groups"]:
    moved: set = set()
    for m in g["methods"]:
      if m["lines"] is not None and "error" not in m["lines"]:
        moved |= MM.moved_lines(base, m["lines"])
        
    for line in sorted(moved):
      qs = (base.get(line) or {}).get("qs")
      if not qs:
        continue
      ranked = rank(line_figures(result, g, line), qs)
      ok = passes(ranked)
      out.append({"id": g["id"], "question": g["question"], "key": g["key"], "scope": dict(g["scope"]), "line": line, "qs": round(float(qs), 3), "basis": INFERRED if ok else STANDARD,
        "value": ranked[0]["value"] if ok else None, "margin_pct": round(ranked[1]["distance_pct"] - ranked[0]["distance_pct"], 2) if len(ranked) > 1 else None, "methods": ranked})
  return out

def adopted(rows: list) -> dict:
  by: dict = {}
  for r in rows:
    if r["basis"] == INFERRED:
      by.setdefault(r["id"], {})[json.dumps(r["value"])] = r
  return {qid: next(iter(v.values()))["value"] for qid, v in by.items() if len(v) == 1}

def labels(rows: list, lines: list) -> dict:
  win = adopted(rows)
  inferred = {r["line"] for r in rows if r["basis"] == INFERRED and r["id"] in win and r["value"] == win[r["id"]]}
  out = {}
  for l in lines:
    out[l["key"]] = INFERRED if l["key"] in inferred else (STANDARD if l.get("class") == "CONVENTION" else DRAWING)
  return out

def problems(rows: list, case_rules: list) -> list:
  out = []
  for r in rows:
    if r["basis"] == INFERRED and not passes(rank(r["methods"], r["qs"])):
      out.append(f"{r['line']} ({r['id']}): labelled {INFERRED} but the methods do not pass the test (one within {NEAR_PCT:g}%, the next {FAR_PCT:g}% or more away)")
      
  for qid, value in adopted(rows).items():
    g = next(x for x in rows if x["id"] == qid)
    have = [c for c in case_rules if c.get("key") == g["key"] and dict(c.get("scope") or {}) == dict(g["scope"])]
    if not have or not MM._same(have[-1].get("value"), value):
      out.append(f"{qid}: inferred {value} but the case rules do not carry it for {g['key']}")
  return out

def view(rows: list, case_rules: list, basis: dict) -> dict:
  by: dict = {}
  for b in basis.values():
    by[b] = by.get(b, 0) + 1
  return {"pairs": len(rows), "inferred": sum(1 for r in rows if r["basis"] == INFERRED), "near_pct": NEAR_PCT, "far_pct": FAR_PCT, "adopted": sorted(adopted(rows)), "by_basis": by, "problems": problems(rows, case_rules)}

def md_text(rows: list) -> str:
  out = ["| Question | Line | His figure | Method | Trace | Off | Rank |", "|---|---|---|---|---|---|---|"]
  for r in rows:
    for i, m in enumerate(r["methods"]):
      out.append(f"| {r['question'] if i == 0 else ''} | {r['line'] if i == 0 else ''} | {r['qs']:,.1f} | {m['label']} | {m['figure']:,.1f} | {m['distance_pct']:.1f}% | {i + 1} |")
    out.append(f"| | | | **{r['basis']}**" + (f": margin to the second {r['margin_pct']:.1f} points" if r["margin_pct"] is not None else "") + " | | | |")
  return "\n".join(out) + "\n"

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Rank the methods of each convention question by their distance to the QS total of each line they move and write conventions.yaml and the table.")
  ap.add_argument("menu_json")
  ap.add_argument("--out", default=".")
  a = ap.parse_args(argv)
  with open(a.menu_json, encoding="utf-8") as fh:
    result = json.load(fh)
  rows = rows_of(result)
  
  os.makedirs(a.out, exist_ok=True)
  with open(os.path.join(a.out, FILE), "w", encoding="utf-8") as fh:
    yaml.safe_dump(rows, fh, sort_keys=False, allow_unicode=True, width=200)
  with open(os.path.join(a.out, "conventions.md"), "w", encoding="utf-8") as fh:
    fh.write(md_text(rows))
  win = adopted(rows)
  print(f"{len(rows)} (question, line) pairs; {sum(1 for r in rows if r['basis'] == INFERRED)} inferred; questions adopted: {', '.join(sorted(win)) or 'none'}")
  return 0

if __name__ == "__main__":
  sys.exit(main())
