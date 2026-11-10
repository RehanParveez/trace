from __future__ import annotations
import os
import yaml

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "task_verdicts.yaml")
JUDGED = ("NOTE_FACT",)
NOT_JUDGED = ("SCHEDULE_ROW", "LEGEND_ENTRY")
ON, OFF, UNDECIDED, NOT_JUDGE = "ON", "OFF", "UNDECIDED", "NOT_JUDGED"
VERDICTS = (ON, OFF, UNDECIDED)
RULE = "first-sight money accuracy rises on two offices and falls on none"
_seen: dict = {}

def load(path: str | None = None) -> dict:
  target = path or PATH
  if not os.path.isfile(target):
    return {}
  stamp = os.path.getmtime(target)
  hit = _seen.get(target)
  if hit and hit[0] == stamp:
    return hit[1]
  with open(target, encoding="utf-8") as fh:
    doc = yaml.safe_load(fh) or {}
  _seen[target] = (stamp, doc)
  return doc

def verdict(task: str, doc: dict | None = None) -> str:
  row = ((doc if doc is not None else load()).get("tasks") or {}).get(task) or {}
  return str(row.get("verdict") or UNDECIDED)

def on(task: str, doc: dict | None = None) -> bool:
  if task not in JUDGED:
    return True
  return verdict(task, doc) == ON

def problems(doc: dict | None = None) -> list:
  doc = load() if doc is None else doc
  out = []
  tasks = doc.get("tasks") or {}
  for name in (*JUDGED, *NOT_JUDGED):
    if name not in tasks:
      out.append(f"{name}: no entry in task_verdicts.yaml")
  for name, row in tasks.items():
    v = str((row or {}).get("verdict") or "")
    if name in JUDGED and v not in VERDICTS:
      out.append(f"{name}: verdict {v!r} is not one of {', '.join(VERDICTS)}")
    if name in NOT_JUDGED and v != NOT_JUDGE:
      out.append(f"{name}: the money judge does not cover it yet, so its verdict is {NOT_JUDGE}, not {v!r}")
    if name in JUDGED and v == ON:
      offices = (row or {}).get("offices") or {}
      rose = [o for o, c in offices.items() if (c.get("change") or 0) > 0]
      fell = [o for o, c in offices.items() if (c.get("change") or 0) < 0]
      if len(rose) < 2 or fell:
        out.append(f"{name}: ON needs money accuracy up on two offices and down on none; the file shows up on {len(rose)} and down on {len(fell)}")
      if not row.get("date") or not row.get("commit"):
        out.append(f"{name}: ON needs the date and commit of the bench run that earned it")
        
  return out
