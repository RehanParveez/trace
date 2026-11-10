from __future__ import annotations
from app.engine.catalogue import loader as CAT
from app.modules.drawings_boq.takeoff.completeness import facts as F
from app.modules.drawings_boq.takeoff.completeness import ledger as LG
from app.modules.drawings_boq.takeoff.completeness import self_check as SC
from app.modules.drawings_boq.takeoff.first_run import job as JB
from app.modules.drawings_boq.takeoff.questions import engine as QE

def _failed_upstream(state: dict) -> str | None:
  return next((s for s in JB.UPSTREAM if s in state.get("failed", [])), None)

def _empty_evidence() -> dict:
  return LG.empty_evidence()

def ledger_stage(state: dict, build_evidence=None) -> None:
  """The ledger from the evidence the reading left, with the project's conventions and answers. When a stage the reading depends on failed, every item that applies is NOT_READ and says which stage."""
  facts = state.get("facts")
  if facts is None:
    facts = F.project_facts([], state.get("decisions"), state.get("storeys"), [])
  evidence = state.get("evidence") or _empty_evidence()
  items = CAT.items()
  bare = LG.build(items, facts, evidence, state.get("conventions"), state.get("methods"), None)
  full = LG.build(items, facts, evidence, state.get("conventions"), state.get("methods"), state.get("answers"))
  stage = _failed_upstream(state)
  if stage:
    bare, full = JB.not_read_for(bare, stage), JB.not_read_for(full, stage)
  state["bare"], state["ledger"] = bare, full

def boq_stage(state: dict) -> None:
  """The BOQ draft: the ledger's quantified entries, each with its state and range, and the total by unit measured and assumed. A money total only when a rate per item is given; none is loaded yet."""
  rows, totals = [], {}
  rates = state.get("rates") or {}
  for e in state["ledger"]:
    q = e.get("quantity")
    if e["state"] not in (LG.MEASURED, LG.ASSUMED) or not q:
      continue
    rate = rates.get(e["element"])
    rows.append({"element": e["element"], "name": e["name"], "floor": e["floor"], "state": e["state"], "quantity": q["value"], "unit": q["unit"], "range": q.get("range"),
      "rate": rate, "amount": None if rate is None else round(float(q["value"]) * float(rate), 2)})
    t = totals.setdefault(q["unit"], {LG.MEASURED: 0.0, LG.ASSUMED: 0.0})
    t[e["state"]] = round(t[e["state"]] + float(q["value"]), 3)
  state["boq"] = {"rows": rows, "totals": totals, "money": None if not rates else round(sum(r["amount"] or 0.0 for r in rows), 2), "rates_loaded": bool(rates)}

def questions_stage(state: dict) -> None:
  state["questions"] = QE.build(state["bare"], state.get("answers"), state.get("conventions"), state.get("rates"))

def self_check_stage(state: dict) -> None:
  """The self-checks on the reading: each compares two things the drawings say twice. A check that cannot run says why; none is guessed. Runs on what the reading left, so a failed reading stage leaves every check NOT_CHECKABLE."""
  state["checks"] = SC.run(state.get("ledger") or [], state.get("evidence") or _empty_evidence())
