from __future__ import annotations
import asyncio
from app.modules.drawings_boq.takeoff.ai_reader.models import AiShadowRead
from app.core.config import settings
import io
from app.modules.drawings_boq.takeoff.extract.extract_service import ExtractService
from uuid import UUID, uuid4
from sqlalchemy import select
from app.modules.ai_requests.service import AIOrchestratorService
from app.modules.drawings_boq.takeoff.crops import source
from app.core.exceptions import TraceException
from app.modules.drawings_boq.takeoff.ai_reader import jobs as JOBS
from app.modules.drawings_boq.takeoff.ai_reader import compare as CMP
from app.modules.drawings_boq.takeoff.ai_reader import contract as C
from app.modules.ai_requests.models import AIRequestPurpose, AIEntityType
from app.modules.drawings_boq.takeoff.ai_reader.reader import FAILED, shadow_read
from app.shared.storage import download_bytes, upload_fileobj

NOTE = ("The AI reads only the title-block strips of a sheet, and only to be measured against the rule reader. Nothing it reads reaches a "
  "measurement or the bill.")

def shadow_enabled(org_id) -> bool:
  ids = {s.strip() for s in (settings.engine_ai_shadow_org_ids or "").split(",") if s.strip()}
  return "*" in ids or str(org_id) in ids

def _item(row: AiShadowRead) -> dict:
  return {"id": row.id, "sheet_id": row.sheet_id, "page_no": row.page_no, "status": row.status, "mode": row.mode, "prompt_version": row.prompt_version,
    "confidence": (row.ai_value or {}).get("confidence"), "comparison": list(row.comparison or []), "totals": dict(row.totals or {}),
    "problems": list(row.problems or []), "error": row.error, "created_at": row.created_at}

class AiShadowService(ExtractService):
  async def _rows(self, org: UUID, drawing_id: UUID) -> list[AiShadowRead]:
    return list((await self.session.execute(select(AiShadowRead).where(AiShadowRead.organization_id == org, AiShadowRead.drawing_id == drawing_id)
      .order_by(AiShadowRead.created_at.desc()))).scalars().all())

  @staticmethod
  def _latest(rows: list[AiShadowRead]) -> list[AiShadowRead]:
    seen: set = set()
    out: list[AiShadowRead] = []
    for r in rows:
      if r.sheet_id not in seen:
        seen.add(r.sheet_id)
        out.append(r)
    return sorted(out, key=lambda r: r.page_no)

  async def run(self, org: UUID, user_id: UUID, drawing_id: UUID, mode: str, limit: int, force: bool) -> dict:
    if not shadow_enabled(org):
      raise TraceException("AI shadow reading is not switched on for this company.", status_code=403, code="AI_SHADOW_OFF")
    if mode not in JOBS.MODES:
      raise TraceException("The mode is WEAK or ALL.", status_code=422, code="AI_SHADOW_MODE")
    drawing = await self.core._pdf_drawing(org, drawing_id)
    sheets = await self.core.repo.sheets(org, drawing_id)

    done = set() if force else {r.sheet_id for r in await self._rows(org, drawing_id) if r.prompt_version == C.PROMPT_VERSION and r.status != FAILED}
    queue = [s for s in sheets if s.id not in done and JOBS.needs_reading((s.prep_meta or {}).get("identity"), mode)]
    batch = queue[:limit]
    contents = await asyncio.to_thread(source.drawing_bytes, drawing.storage_key) if batch else b""
    orchestrator = AIOrchestratorService(self.session)

    async def ask(prompt: str, png: bytes):
      return await orchestrator.run(organization_id=org, purpose=AIRequestPurpose.SHEET_CLASSIFICATION, entity_type=AIEntityType.DRAWING,
        entity_id=drawing.id, requested_by=user_id, prompt=prompt, image_bytes=png, image_mime_type="image/png")

    async def store_crop(png: bytes) -> str:
      key = f"{org}/{drawing.project_id}/ai-shadow/{uuid4().hex}.png"
      await asyncio.to_thread(upload_fileobj, key, io.BytesIO(png), "image/png")
      return key

    made: list[AiShadowRead] = []
    for sheet in batch:
      rec = await shadow_read(contents=contents, page_no=sheet.page_no, identity=(sheet.prep_meta or {}).get("identity"), mode=mode, ask=ask, store_crop=store_crop)
      if rec is None:
        continue

      row = AiShadowRead(id=uuid4(), organization_id=org, project_id=drawing.project_id, drawing_id=drawing.id, sheet_id=sheet.id, page_no=sheet.page_no,
        purpose=rec["purpose"], mode=mode, status=rec["status"], prompt_version=rec["prompt_version"], schema_version=rec["schema_version"], crop_key=rec["crop_key"],
        crop=rec["crop"], ai_request_id=rec["ai_request_id"], rule_value=rec["rule_value"], ai_value=rec["ai_value"], comparison=rec["comparison"], totals=rec["totals"],
        problems=rec["problems"], error=rec["error"], created_by_user_id=user_id)
      self.session.add(row)
      await self.session.commit()
      made.append(row)
    return {"drawing_id": drawing.id, "mode": mode, "read": sum(1 for r in made if r.status != FAILED), "failed": sum(1 for r in made if r.status == FAILED),
      "remaining": len(queue) - len(batch), "items": [_item(r) for r in made]}

  async def summary(self, org: UUID, drawing_id: UUID) -> dict:
    await self.core._pdf_drawing(org, drawing_id)
    sheets = await self.core.repo.sheets(org, drawing_id)
    latest = [r for r in self._latest(await self._rows(org, drawing_id)) if r.status == "OK"]
    totals = {k: 0 for k in CMP.AGREEMENTS}
    by_fact: dict = {}

    for r in latest:
      for rec in r.comparison or []:
        totals[rec["agreement"]] = totals.get(rec["agreement"], 0) + 1
        by_fact.setdefault(rec["fact_key"], {k: 0 for k in CMP.AGREEMENTS})[rec["agreement"]] += 1
    return {"drawing_id": drawing_id, "enabled": shadow_enabled(org), "sheets_total": len(sheets), "sheets_read": len(latest), "totals": totals,
      "by_fact": by_fact, "items": [_item(r) for r in self._latest(await self._rows(org, drawing_id))], "note": NOTE}

  async def crop(self, org: UUID, read_id: UUID) -> bytes:
    row = (await self.session.execute(select(AiShadowRead).where(AiShadowRead.id == read_id, AiShadowRead.organization_id == org))).scalar_one_or_none()
    if row is None:
      raise TraceException("That reading is not found.", status_code=404, code="AI_SHADOW_NOT_FOUND")
    return await asyncio.to_thread(download_bytes, row.crop_key)
