from __future__ import annotations
import time
from app.modules.drawings_boq.takeoff.completeness import ledger as LG

STAGES = ("register", "profile", "scale", "read", "members", "ledger", "quantities", "boq", "questions")
RERUN_STAGES = ("ledger", "quantities", "boq", "questions")
DONE, FAILED, SKIPPED = "DONE", "FAILED", "SKIPPED"
STAGE_FAILED = "STAGE_FAILED"
UPSTREAM = ("register", "profile", "scale", "read", "members")

class Upstream(Exception):
  """Raised by a stage that cannot run because a stage before it gave it nothing: the stage is SKIPPED and counts as failed for the ledger."""

def _run_stage(name: str, fn, state: dict, clock) -> dict:
  start = clock()
  row = {"name": name, "status": DONE, "seconds": 0.0, "error": None, "blocked": False}
  try:
    fn(state)
    
  except Upstream as exc:
    row["status"], row["error"], row["blocked"] = SKIPPED, str(exc)[:300], True
  except Exception as exc:
    row["status"] = FAILED
    row["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
  row["seconds"] = round(clock() - start, 3)
  return row

def run(bindings: dict, state: dict, *, stages: tuple = STAGES, progress=None, clock=time.monotonic) -> dict:
  rows: list = []
  state.setdefault("failed", [])
  for n, name in enumerate(stages, 1):
    fn = bindings.get(name)
    
    if fn is None:
      row = {"name": name, "status": SKIPPED, "seconds": 0.0, "error": "no binding for this stage", "blocked": False}
    else:
      row = _run_stage(name, fn, state, clock)
    if row["status"] == FAILED or row["blocked"]:
      state["failed"].append(name)
    rows.append(row)
    if progress is not None:
      progress(name, n, len(stages), row["status"])
  state["stages"] = rows
  return {"stages": rows, "failed": list(state["failed"]), "seconds": round(sum(r["seconds"] for r in rows), 3)}

def affected(items: list, blocked_by: list) -> list:
  hit = set(blocked_by)
  grew = True
  derived = {it.id: list((it.derived or {}).get("from") or []) for it in items if it.derived}
  while grew:
    grew = False
    for iid, src in derived.items():
      if iid not in hit and any(s in hit for s in src):
        hit.add(iid)
        grew = True
  return sorted(hit)

def rerun(bindings: dict, state: dict, keys: list, *, progress=None, clock=time.monotonic) -> dict:
  from app.engine.catalogue import loader as CAT
  from app.modules.drawings_boq.takeoff.questions import engine as QE
  asked = {q["key"]: q for q in QE.build(state["bare"], state.get("answers") or {}, state.get("conventions") or [])}
  hit = affected(CAT.items(), [b for k in keys for b in (asked.get(k) or {}).get("blocks", [])])
  state["rerun_items"] = hit
  before: dict = {}
  
  for e in state["ledger"]:
    before.setdefault(e["element"], []).append(dict(e))
  out = run(bindings, state, stages=RERUN_STAGES, progress=progress, clock=clock)
  after = {}
  for e in state["ledger"]:
    after.setdefault(e["element"], []).append(e)
  moved = sorted(k for k in after if k not in hit and after[k] != before.get(k))
  return {**out, "items": hit, "moved_outside": moved}

def not_read_for(entries: list, stage: str) -> list:
  out = []
  for e in entries:
    if e["state"] == LG.NOT_APPLICABLE:
      out.append(e)
      continue
    out.append({**e, "state": LG.NOT_READ, "quantity": None, "members": [], "assumptions": [], "questions": [], "reasons": [f"{STAGE_FAILED}:{stage}"]})
  return out
