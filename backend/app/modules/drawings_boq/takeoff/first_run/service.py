from __future__ import annotations
import asyncio
import os
import tempfile
from datetime import datetime, timezone
from uuid import UUID
from app.core.exceptions import TraceException
from app.engine.catalogue import conventions as CV
from app.modules.audit.models import AuditAction
from app.modules.drawings_boq import company_conventions as CCV
from app.modules.drawings_boq.takeoff.first_run import job as JB
from app.modules.drawings_boq.takeoff.first_run import report as RP
from app.modules.drawings_boq.takeoff.first_run import stages as ST
from app.modules.drawings_boq.takeoff.run import first_run_bindings as FR
from app.modules.drawings_boq.takeoff.questions import answers as AN
from app.modules.drawings_boq.takeoff.service import TakeoffService
from app.shared.storage import download_to_path

META_REPORT = "first_run"

def snapshot_of(state: dict, now: datetime | None = None) -> dict:
  """What the questions service rebuilds the ledger from: the facts and evidence the reading left, the methods and the conventions in force, and when."""
  return {"facts": state["facts"], "evidence": state["evidence"], "methods": state.get("methods") or {}, "conventions": list(state.get("conventions") or []),
    "at": (now or datetime.now(timezone.utc)).isoformat()}

def read_plains(files: list) -> tuple:
  from app.modules.drawings_boq.takeoff.run import completeness as CR
  from app.modules.drawings_boq.takeoff.run import reading_adapter as AD
  from app.modules.drawings_boq.takeoff.profile import run as PRUN
  plains, unread, facts = [], [], []
  with tempfile.TemporaryDirectory() as tmp:
    for n, (name, key) in enumerate(files):
      path = os.path.join(tmp, f"{n}.pdf")
      try:
        download_to_path(key, path)
        plain = CR.plain_read(AD.read_items(path))
        facts.extend(PRUN.facts_of_pdf(path, len(plains) * CR.SHEET_SHIFT))
        plains.append(plain)
      except Exception as exc:
        unread.append({"file": name, "error": f"{type(exc).__name__}: {str(exc)[:200]}"})
  return plains, unread, facts

class FirstRunService(TakeoffService):
  async def _drawings(self, org: UUID, project_id: UUID) -> list:
    drawings = await self.repo.project_pdf_drawings(org, project_id)
    if not drawings:
      raise TraceException("This project has no PDF drawings to read.", status_code=409, code="NO_PDF")
    return drawings

  async def _conventions(self, org: UUID) -> list:
    return CV.on_ids(await CCV.in_force(self.session, org))

  async def run(self, org: UUID, user_id: UUID | None, project_id: UUID, progress=None) -> dict:
    """The first-upload job over every PDF of the project: read, ledger, BOQ draft, questions. The snapshot goes on the first drawing and the report with it."""
    drawings = await self._drawings(org, project_id)
    files = [(d.original_filename, d.storage_key) for d in drawings]
    plains, unread, facts = await asyncio.to_thread(read_plains, files)
    state = {"conventions": await self._conventions(org), "answers": AN.merge([d.ingestion_meta for d in drawings]), "unread": unread}
    out = JB.run(FR.offline_bindings(plains=plains, page_facts=facts), state, progress=progress)
    report = RP.build(state, out)
    home = drawings[0]
    meta = dict(home.ingestion_meta or {})
    if "facts" in state and "evidence" in state:
      meta[AN.META_LEDGER] = snapshot_of(state)
    meta[META_REPORT] = {**report, "at": datetime.now(timezone.utc).isoformat()}
    home.ingestion_meta = meta
    if user_id is not None:
      await self._log(org, user_id, home.id, AuditAction.UPDATE, f"First-upload job: {report['items']}, {report['questions']['open']} question(s) open", commit=False)
    await self.session.commit()
    return report

  async def report(self, org: UUID, project_id: UUID) -> dict:
    """The stored report, brought up to date with the answers given since: the ledger, the draft and the questions are recomputed from the stored snapshot; nothing is read again."""
    drawings = await self._drawings(org, project_id)
    held = [d for d in drawings if (d.ingestion_meta or {}).get(AN.META_LEDGER)]
    if not held:
      return {"project_id": project_id, "has_ledger": False}
    home = max(held, key=lambda d: str(d.ingestion_meta[AN.META_LEDGER].get("at") or ""))
    snap, stored = home.ingestion_meta[AN.META_LEDGER], home.ingestion_meta.get(META_REPORT) or {}
    state = {"facts": snap["facts"], "evidence": snap["evidence"], "methods": snap.get("methods") or {}, "conventions": await self._conventions(org),
      "answers": AN.merge([d.ingestion_meta for d in drawings]), "failed": [], "unread": stored.get("unread") or []}
    out = JB.run({"ledger": ST.ledger_stage, "boq": ST.boq_stage, "questions": ST.questions_stage}, state, stages=JB.RERUN_STAGES)
    out["stages"] = [s for s in out["stages"] if s["name"] != "quantities"]
    return {"project_id": project_id, "has_ledger": True, "snapshot_at": snap.get("at"), "ran_at": stored.get("at"), **RP.build(state, out)}
