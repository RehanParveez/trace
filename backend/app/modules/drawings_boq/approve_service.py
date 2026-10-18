from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract.floor_sources_service import FloorSourceService
from uuid import UUID
from app.modules.drawings_boq.takeoff import approve_pick as AP
from app.modules.drawings_boq.takeoff.extract.crosschecks_service import CrossCheckService
from app.modules.drawings_boq.takeoff.extract.extract_schemas import AcceptRequest
from app.core.exceptions import TraceException
from pydantic import ValidationError
from app.modules.drawings_boq.models import TakeoffMeasurement
from sqlalchemy import select
from app.modules.drawings_boq.takeoff.register_service import RegisterService

CHUNK = 200

class ApproveService(FloorSourceService):

  async def approve(self, org: UUID, user_id: UUID, drawing_id: UUID, payload) -> dict:
    await self.core._pdf_drawing(org, drawing_id)
    steps = _Steps(self, org, user_id, drawing_id)
    out = await AP.run(steps, accept_assumed=payload.accept_assumed, accept_warned=payload.accept_warned, typed=dict(payload.typed),
      exclude={str(i) for i in payload.exclude_ids}, batch=payload.batch, confirm=payload.confirm, dry_run=payload.dry_run)
    return {"drawing_id": drawing_id, **out}

class _Steps:
  def __init__(self, svc: ApproveService, org: UUID, user_id: UUID, drawing_id: UUID):
    self.svc, self.org, self.user_id, self.drawing_id = svc, org, user_id, drawing_id

  async def floors_pending(self) -> int:
    view = await self.svc.floor_sources(self.org, self.drawing_id)
    return sum(1 for f in view["floors"] if f["state"] == "DOUBLE" and f["suggested_sheet_id"])

  async def choose_floors(self) -> list:
    return await self.svc._default_floors(self.org, self.user_id, self.drawing_id)

  async def ready(self) -> dict:
    return await CrossCheckService(self.svc.session).ready_to_accept(self.org, self.drawing_id)

  async def accept(self, ids: list, typed: dict) -> dict:
    accepted: list = []
    failed: list = []
    
    for start in range(0, len(ids), CHUNK):
      try:
        body = AcceptRequest(ids=[UUID(i) for i in ids[start:start + CHUNK]], **typed)
      except ValidationError as exc:
        raise TraceException(f"A typed size cannot be used: {exc.errors()[0]['msg']}", status_code=422, code="APPROVE_BAD_SIZE")
      got = await self.svc.accept(self.org, self.user_id, body)
      accepted += got["accepted"]
      failed += got["failed"]
    return {"accepted": accepted, "failed": failed}

  async def _measurements(self) -> list:
    sheets = await self.svc.core.repo.sheets(self.org, self.drawing_id)
    ids = [s.id for s in sheets]
    if not ids:
      return []
    return list((await self.svc.session.execute(select(TakeoffMeasurement.id, TakeoffMeasurement.status).where(TakeoffMeasurement.organization_id == self.org,
      TakeoffMeasurement.sheet_id.in_(ids)))).all())

  async def draft_measurements(self) -> list:
    sheets = await self.svc.core.repo.sheets(self.org, self.drawing_id)
    cands = await self.svc.repo.candidates(self.org, [s.id for s in sheets])
    made = {c.measurement_id for c in cands if c.decision == "ACCEPTED" and c.measurement_id}
    return [mid for mid, status in await self._measurements() if status != "CONFIRMED" and mid in made]

  async def confirm(self, ids: list) -> dict:
    confirmed: list = []
    failed: list = []
    for start in range(0, len(ids), CHUNK):
      got = await self.svc.core.bulk_confirm(self.org, ids[start:start + CHUNK], self.user_id)
      confirmed += got["confirmed"]
      failed += got["failed"]
    return {"confirmed": confirmed, "failed": failed}

  async def resync(self) -> dict:
    return await RegisterService(self.svc.session).sync_and_commit(self.org, self.drawing_id)

  async def counts(self) -> dict:
    rows = await self._measurements()
    return {"confirmed": sum(1 for _, s in rows if s == "CONFIRMED"), "draft": sum(1 for _, s in rows if s != "CONFIRMED")}
