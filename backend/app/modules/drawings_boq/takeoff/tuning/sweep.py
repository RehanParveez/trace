from __future__ import annotations
from dataclasses import dataclass, field
from app.modules.drawings_boq.takeoff.reading_score import reading_score as S
from typing import Callable
import time
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.tuning import registry as R
from app.modules.drawings_boq.takeoff.tuning import override as O

SWEEP_VERSION = 1
BASE, PERTURBED = "BASE", "PERTURBED"
COMPLETE, OPEN = "COMPLETE", "OPEN"
FAMILY_FIELDS = ("family", "labels", "found", "tp", "fp", "fn", "wrong_confirmed", "unlabelled", "precision", "recall", "f1")

class NotDeterministic(RuntimeError):
  """Two runs of the reader with nothing changed gave different scores, so the effect of a value cannot be told from noise."""

@dataclass
class SweepSheet:
  page_no: int
  labels: list                    
  read: Callable[[], list]        
  title: str | None = None

@dataclass
class Case:
  name: str
  role: str                       
  rule: S.MatchRule
  sheets: list = field(default_factory=list)
  drawing_id: str | None = None
  label_drawing_id: str | None = None

def pool_key(role: str, basis: str) -> str:
  return f"{role}:{COMPLETE if basis == 'COMPLETE' else OPEN}"

def _trim(row: dict) -> dict:
  out = {k: row.get(k) for k in FAMILY_FIELDS}
  s = row.get("size") or {}
  out["size"] = {k: s.get(k, 0) for k in ("checked", "ok", "wrong", "unread")}
  return out

def _pool(sheets: list) -> dict:
  fams = S.by_family(sheets)
  tot = S.totals_of(fams) if fams else S.totals_of([])
  return {"sheets": len(sheets), "totals": {k: tot.get(k) for k in ("labels", "found", "tp", "fp", "fn", "wrong_confirmed", "unlabelled", "precision", "recall", "f1")},
    "families": [_trim(f) for f in fams]}

def evaluate(cases: list) -> dict:
  t0 = time.monotonic()
  scored: dict = {}
  failed = []
  for case in cases:
    for sh in case.sheets:
      try:
        reads = sh.read()
      except Exception as e:                        
        failed.append({"case": case.name, "page_no": sh.page_no, "error": type(e).__name__})
        continue
      res = S.score_sheet(sh.labels, reads, case.rule)
      scored.setdefault(pool_key(case.role, res["basis"]), []).append(res)
  return {"pools": {k: _pool(v) for k, v in sorted(scored.items())}, "failed": failed, "seconds": round(time.monotonic() - t0, 3)}

def _fam_tuple(row: dict) -> tuple:
  return tuple(row.get(k) for k in ("family", "labels", "found", "tp", "fp", "fn", "wrong_confirmed", "unlabelled")) + tuple((row.get("size") or {}).get(k, 0) for k in ("ok", "wrong"))

def same_scores(a: dict, b: dict) -> bool:
  """Do two evaluations give the same counts in every pool and every kind of member?"""
  if set(a["pools"]) != set(b["pools"]) or len(a["failed"]) != len(b["failed"]):
    return False
  return all(a["pools"][k]["sheets"] == b["pools"][k]["sheets"] and [_fam_tuple(r) for r in a["pools"][k]["families"]] == [_fam_tuple(r) for r in b["pools"][k]["families"]]
    for k in a["pools"])

def select(rules: list | None = None, keys: list | None = None, include_unswept: bool = False) -> list:
  allp = R.params()
  if keys:
    chosen = [R.get(k) for k in keys]
  elif rules:
    known = {p.rule_id for p in alp} | {r["id"] for r in R.rules()}
    bad = sorted(set(rules) - known)
    if bad:
      raise ValueError(f"Not a rule of the register: {', '.join(bad)}.")
    chosen = [p for p in allp if p.rule_id in set(rules)]
  else:
    chosen = [p for p in allp if p.calibratable]
  return [p.key for p in chosen if include_unswept or p.status == R.SWEEPABLE]

def plan(keys: list, ladder: str = "standard", control_seconds: float | None = None, cases: int = 1) -> dict:
  cells, left_out = [], []
  
  for k in keys:
    p = R.get(k)
    if p.status != R.SWEEPABLE:
      left_out.append({"key": k, "reason": p.reasons[0] if p.reasons else p.status})
      continue
  
    vals = []
    for v in R.candidates(p, ladder):
      try:
        O.check({k: v})
      except O.BadValue as e:
        left_out.append({"key": k, "value": v, "reason": str(e)})
        continue
      vals.append(v)
    cells += [{"key": k, "value": v} for v in vals]
  est = None if control_seconds is None else round(control_seconds * (len(cells) + 2), 1)
  return {"ladder": ladder, "constants": len({c["key"] for c in cells}), "cells": cells, "n_cells": len(cells), "left_out": left_out, "estimate_seconds": est, "cases": cases}

def run_sweep(cases: list, keys: list, ladder: str = "standard", max_seconds: float | None = None, check_repeat: bool = True,
  progress: Callable[[str], None] | None = None) -> dict:
  if not O.is_isolated():
    raise O.NotIsolated("A sweep sets constants, so it runs only in the sweep tool's own process.")

  say = progress or (lambda m: None)
  t0 = time.monotonic()
  say("control run")
  control = evaluate(cases)
  
  if control["failed"]:
    raise RuntimeError(f"The reader failed on {len(control['failed'])} sheet(s) with nothing changed ({control['failed'][0]['error']}); fix that before sweeping.")
  if not control["pools"]:
    raise RuntimeError("No sheet was scored: there is nothing to sweep against.")
  if check_repeat:
    say("control run again, to check the reader gives the same result twice")
    again = evaluate(cases)
    if not same_scores(control, again):
      raise NotDeterministic("The reader gave different scores in two runs with nothing changed, so a sweep could not tell the effect of a value from noise.")
  
  out_params, skipped = [], []
  stopped = None
  for key in keys:
    p = R.get(key)
    if p.status != R.SWEEPABLE:
      skipped.append({"key": key, "reason": p.reasons[0] if p.reasons else p.status})
      continue
    if max_seconds is not None and time.monotonic() - t0 > max_seconds:
      stopped = "TIME_LIMIT"
      skipped.append({"key": key, "reason": "The time allowed ran out before this constant."})
      continue
  
    values, rejected = [], []
    for v in R.candidates(p, ladder):
      try:
        O.check({key: v})
      except O.BadValue as e:
        rejected.append({"value": v, "reason": str(e)})
        continue
      say(f"{key} = {v:g}")
      with O.overridden({key: v}):
        ev = evaluate(cases)
        
      values.append({"value": v, "pools": ev["pools"], "failed": ev["failed"], "seconds": ev["seconds"], "moved": not same_scores(control, ev)})
    out_params.append({"key": key, "hand": p.hand, "current": p.live, "rule_id": p.rule_id, "basis": p.basis, "families": list(p.families), "values": values,
      "rejected": rejected, "inert": bool(values) and not any(x["moved"] for x in values)})
  return {"sweep_version": SWEEP_VERSION, "extract_version": C.EXTRACT_VERSION, "ladder": ladder, "design": "ONE_AT_A_TIME",
    "cases": [{"name": c.name, "role": c.role, "drawing_id": c.drawing_id, "label_drawing_id": c.label_drawing_id, "rule": c.rule.as_dict(), "sheets": len(c.sheets),
      "labels": sum(len(s.labels) for s in c.sheets)} for c in cases],
    "control": {"pools": control["pools"], "seconds": control["seconds"]}, "params": out_params, "skipped": skipped, "partial": stopped is not None, "stopped": stopped,
    "seconds": round(time.monotonic() - t0, 1)}

def run_joint(cases: list, changes: dict) -> dict:
  if not O.is_isolated():
    raise O.NotIsolated("A sweep sets constants, so it runs only in the sweep tool's own process.")
  with O.overridden(changes):
    return evaluate(cases)
