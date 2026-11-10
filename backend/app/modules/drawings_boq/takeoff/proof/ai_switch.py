from __future__ import annotations
import argparse
import datetime
import json
import os
import sys
import yaml
from app.modules.ai_requests import cap as CAP
from app.modules.drawings_boq.takeoff.ai_reader import cost as COST
from app.modules.drawings_boq.takeoff.ai_reader import switch as SW
from app.modules.drawings_boq.takeoff.proof import ai_gate as AG
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.proof.bench import ai_money as AM

def pct(within: float, money: float) -> float | None:
  return round(100.0 * within / money, 1) if money else None

def by_office(records: list) -> dict:
  out: dict = {}
  for r in records:
    off, on = r.get("off") or {}, r.get("on") or {}
    if not off.get("defined") or not on.get("defined"):
      continue
    
    o = out.setdefault(r["office"], {"sets": [], "off_money": 0.0, "off_within": 0.0, "on_money": 0.0, "on_within": 0.0})
    o["sets"].append(r["set"])
    o["off_money"] += float(off["money_pkr"])
    o["off_within"] += float(off["within_pkr"])
    o["on_money"] += float(on["money_pkr"])
    o["on_within"] += float(on["within_pkr"])
    
  rows = {}
  for office, o in sorted(out.items()):
    a, b = pct(o["off_within"], o["off_money"]), pct(o["on_within"], o["on_money"])
    rows[office] = {"sets": o["sets"], "off_pct": a, "on_pct": b, "change": None if a is None or b is None else round(b - a, 1), "off_money_pkr": round(o["off_money"], 2), "on_money_pkr": round(o["on_money"], 2)}
  return rows

def judge(offices: dict, stops: list) -> tuple:
  rose = [o for o, c in offices.items() if (c["change"] or 0) > 0]
  fell = [o for o, c in offices.items() if (c["change"] or 0) < 0]
  if fell:
    return SW.OFF, f"money accuracy fell on {', '.join(fell)}"
  if stops:
    return SW.UNDECIDED, f"more than a third of the answers fail their checks on {', '.join(stops)}; the prompts come first"
  if len(rose) >= 2:
    return SW.ON, f"money accuracy rose on {', '.join(rose)} and fell on none"
  return SW.UNDECIDED, f"money accuracy rose on {len(rose)} office(s); two are needed" if offices else "no set has money both with the answers off and on"

def verdict_of(doc: dict, stops: list) -> dict:
  offices = by_office(doc["records"])
  verdict, why = judge(offices, stops)
  return {"task": doc["task"], "variant": doc.get("variant"), "verdict": verdict, "why": why, "offices": offices, "date": doc.get("date"), "commit": doc.get("commit")}

def compete(docs: list, stops: list) -> tuple:
  got = [verdict_of(d, stops) for d in docs]
  passing = [g for g in got if g["verdict"] == SW.ON]
  rank = lambda g: (-sum(c["change"] or 0 for c in g["offices"].values()), str(g["variant"]))
  pick = sorted(passing, key=rank)[0] if passing else None
  return got, pick

def stops_for(root: str, task: str) -> list:
  return sorted(f"{r['office']}" for r in AG.table(root) if r["task"] == task and r["stop"])

def spend_line(root: str) -> str:
  return f"spend kept in the case folders {COST.cache_spent_usd(root):.4f} USD against a monthly cap of {CAP.settings.ai_monthly_cap_usd:.2f} USD"

def lines(got: list, pick: dict | None, root: str) -> list:
  out = []
  for g in got:
    out.append(f"{g['task']} variant {g['variant'] or 'latest'}: {g['verdict']}; {g['why']}")
    for office, c in g["offices"].items():
      out.append(f"  office {office}: {c['off_pct']}% off, {c['on_pct']}% on ({c['change']:+.1f}) over {', '.join(c['sets'])}")
  out.append("winner: " + (f"variant {pick['variant'] or 'latest'}" if pick else "none; the task stays as it was"))
  out.append(spend_line(root))
  return out

def write(path: str, got: list, pick: dict | None) -> None:
  with open(path, encoding="utf-8") as fh:
    doc = yaml.safe_load(fh) or {}
  task = got[0]["task"]
  row = pick or {"task": task, "variant": None, "verdict": SW.OFF if any(g["verdict"] == SW.OFF for g in got) else SW.UNDECIDED, "offices": got[0]["offices"], "date": got[0]["date"], "commit": got[0]["commit"]}
  doc.setdefault("tasks", {})[task] = {"verdict": row["verdict"], "variant": row["variant"], "date": row["date"] or datetime.date.today().isoformat(), "commit": row["commit"], "offices": row["offices"]}
  with open(path, "w", encoding="utf-8", newline="\n") as fh:
    yaml.safe_dump(doc, fh, sort_keys=False, default_flow_style=False, width=1000)

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Judge an AI task by money: read the ai_money.json of one bench run per variant (bench --ai TASK[:VARIANT]) and say ON only if first-sight money accuracy rises on two offices and falls on none. --write records the verdict in ai_reader/task_verdicts.yaml; nothing else switches a task on.")
  ap.add_argument("money", nargs="+", help="ai_money.json files, one per variant of the same task")
  ap.add_argument("--root", default=CIO.HERE, help="the folder of case folders, for the spend and the check-failure stop")
  ap.add_argument("--out", default=SW.PATH)
  ap.add_argument("--write", action="store_true")
  a = ap.parse_args(argv)
  docs = []
  
  for path in a.money:
    with open(path, encoding="utf-8") as fh:
      docs.append(json.load(fh))
  if len({d["task"] for d in docs}) != 1:
    print("the files name different tasks; judge one task at a time", file=sys.stderr)
    return 2
  if docs[0]["task"] not in SW.JUDGED:
    print(f"{docs[0]['task']} is not judged by money yet", file=sys.stderr)
    return 2
  got, pick = compete(docs, stops_for(a.root, docs[0]["task"]))
  print("\n".join(lines(got, pick, a.root)))
  if a.write:
    write(a.out, got, pick)
    print(f"written to {a.out}")
  else:
    print("nothing written; add --write")
  return 0

if __name__ == "__main__":
  sys.exit(main())
