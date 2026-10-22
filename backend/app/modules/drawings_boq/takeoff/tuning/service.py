from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
from app.core.exceptions import TraceException
from app.modules.drawings_boq.takeoff.reading_score import service as RS
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.tuning import decide as D
from app.modules.drawings_boq.takeoff.tuning import ledger as LG
from app.modules.drawings_boq.takeoff.tuning import registry as R
from app.modules.drawings_boq.takeoff.tuning import report as RP
from app.modules.drawings_boq.takeoff.tuning import sweep as W
from app.modules.drawings_boq.takeoff.tuning.models import ReadingSweep
from app.modules.drawings_boq.takeoff.tuning.repository import SweepRepository

def param_out(p: R.Param, ledgered: set) -> dict:
  files = []
  for f, line, _, _ in p.uses:
    tag = f"{f}:{line}"
    if f not in {x.split(":")[0] for x in files}:
      files.append(tag)
  return {"key": p.key, "name": p.name, "rule_id": p.rule_id, "basis": p.basis, "families": list(p.families), "unit": p.unit, "kind": p.kind, "lo": p.lo, "hi": p.hi,
    "hand": p.hand, "live": p.live, "stage": p.stage, "status": p.status, "calibratable": p.calibratable, "reasons": list(p.reasons),
    "copies": [f"{m.rsplit('.', 1)[-1]}.{a}" for m, a in p.copies], "files": files, "reads": len(p.uses), "ledgered": p.key in ledgered}

def patch_of(result: dict, decided: dict) -> dict:
  ds = decided["decisions"]
  changes = [d for d in ds if d["action"] == D.CHANGE]
  hunks = RP.config_hunks(ds)
  version = RP.version_hunk() if changes else None
  ledger_json = LG.dumps(RP.ledger_entries(ds, result, (version or {}).get("new_version", C.EXTRACT_VERSION + 1))) if changes else None
  return {"hunks": hunks, "version": version, "ledger_json": ledger_json, "markdown": RP.render(result, decided, decided.get("joint"))}

def item_of(row: ReadingSweep) -> dict:
  return {"id": row.id, "drawing_id": row.drawing_id, "created_at": row.created_at, "extract_version": row.extract_version, "stale": row.extract_version != C.EXTRACT_VERSION,
    "ladder": row.ladder, "status": row.status, "constants": row.constants, "cells": row.cells, "changes": row.changes, "label_count": row.label_count, "seconds": float(row.seconds),
    "note": row.note, "counts": (row.decisions or {}).get("counts", {})}

class TuningService(RS.ReadingScoreService):
  def __init__(self, session):
    super().__init__(session)
    self.sweeps = SweepRepository(session)

  def registry(self) -> dict:
    entries = LG.load()
    led = {e["key"] for e in entries}
    return {"extract_version": C.EXTRACT_VERSION, "base_extract_version": LG.BASE_EXTRACT_VERSION, "rules": R.rules(), "params": [param_out(p, led) for p in R.params()],
      "unregistered": R.unregistered(), "ledger": {"entries": entries, "drift": LG.drift(entries)}}

  async def plan(self, org: UUID, drawing_id: UUID, payload) -> dict:
    await self._drawing(org, drawing_id)
    for c in payload.copies:
      await self._drawing(org, c)
    try:
      keys = W.select(payload.rules, payload.keys, payload.include_unswept)
      plan = W.plan(keys, payload.ladder, payload.control_seconds, 1 + len(payload.copies))
    except (ValueError, KeyError) as e:
      raise TraceException(f"Not a rule or constant of the register: {e.args[0] if e.args else e}", status_code=422, code="TUNING_SELECTION_INVALID")
    summary = await self.labels_summary(org, drawing_id)
    complete = sum(1 for s in summary["sheets"] if s["complete"])
    warnings = []
    
    if not summary["positive"]:
      warnings.append("The drawing has no labels. Derive them from the register or import a ground-truth file first.")
    elif not complete:
      warnings.append("No sheet is labelled completely (every member of it). Without one a sweep cannot show that a looser value finds wrong things, so no value will be changed.")
    elif summary["positive"] < D.Policy().min_labels:
      warnings.append(f"The drawing has {summary['positive']} labelled members; the rule asks for {D.Policy().min_labels} of the kinds a constant is for before it changes one.")
    parts = ["python scripts/tune_sweep.py run", f"--org {org}", f"--drawing {drawing_id}"]
    parts += [f"--copy {c}" for c in payload.copies]
    if payload.keys:
      parts.append("--keys " + " ".join(payload.keys))
    elif payload.rules:
      parts.append("--rules " + " ".join(payload.rules))
    parts.append(f"--ladder {payload.ladder}")
    return {"drawing_id": drawing_id, "ladder": plan["ladder"], "constants": plan["constants"], "n_cells": plan["n_cells"], "cells": plan["cells"], "left_out": plan["left_out"],
      "estimate_seconds": plan["estimate_seconds"], "labels": summary["positive"], "complete_sheets": complete, "warnings": warnings, "command": " ".join(parts)}

  async def keep_sweep(self, org: UUID, drawing_id: UUID, result: dict, decided: dict, note: str | None = None, user_id: UUID | None = None) -> ReadingSweep:
    drawing = await self._drawing(org, drawing_id)
    labels = sum(c["labels"] for c in result["cases"] if c["role"] == W.BASE)
    row = ReadingSweep(organization_id=org, project_id=drawing.project_id, drawing_id=drawing_id, extract_version=result["extract_version"], ladder=result["ladder"],
      status="PARTIAL" if result.get("partial") else "COMPLETE", constants=len(result["params"]), cells=sum(len(p["values"]) for p in result["params"]),
      changes=decided["counts"].get(D.CHANGE, 0), label_count=labels, labels_stamp=result.get("labels_stamp"), seconds=Decimal(str(round(result["seconds"], 1))),
      result=result, decisions=decided, note=note, created_by_user_id=user_id, created_at=datetime.now(timezone.utc))
    
    self.sweeps.add(row)
    await self.session.flush()
    await self.session.commit()
    await self.session.refresh(row)
    return row

  async def list_sweeps(self, org: UUID, drawing_id: UUID, limit: int = 50) -> dict:
    await self._drawing(org, drawing_id)
    rows = await self.sweeps.list(org, drawing_id, limit)
    return {"drawing_id": drawing_id, "current_extract_version": C.EXTRACT_VERSION, "sweeps": [item_of(r) for r in rows]}

  async def _row(self, org: UUID, sweep_id: UUID) -> ReadingSweep:
    row = await self.sweeps.get(org, sweep_id)
    if row is None:
      raise TraceException("Sweep not found.", status_code=404, code="SWEEP_NOT_FOUND")
    return row

  async def detail(self, org: UUID, sweep_id: UUID) -> dict:
    row = await self._row(org, sweep_id)
    return {**item_of(row), "result": row.result, "decisions": row.decisions, "patch": patch_of(row.result, row.decisions)}

  async def decide_again(self, org: UUID, sweep_id: UUID, payload) -> dict:
    row = await self._row(org, sweep_id)
    over = {k: v for k, v in payload.model_dump().items() if v is not None}
    decided = D.decide(row.result, D.Policy.for_sweep(row.result, **over))
    return {"sweep_id": row.id, "decisions": decided, "patch": patch_of(row.result, decided)}

  async def delete_sweep(self, org: UUID, sweep_id: UUID) -> dict:
    await self._row(org, sweep_id)
    n = await self.sweeps.delete(org, sweep_id)
    await self.session.commit()
    return {"deleted": n}
