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
from app.modules.drawings_boq.takeoff.ai_reader import cache as CACHE
from app.modules.drawings_boq.takeoff.ai_reader import cost as COST
from app.modules.drawings_boq.takeoff.ai_reader import regions as RG
from app.modules.drawings_boq.takeoff.ai_reader import tasks as TASKS
from app.modules.ai_requests.models import AIRequestPurpose, AIEntityType, AIRequest, AIResponse
from app.modules.drawings_boq.takeoff.ai_reader.reader import FAILED, TASK, shadow_read
from app.shared.storage import download_bytes, upload_fileobj

NOTE = ("The AI reads only the title-block strips of a sheet, and only to be measured against the rule reader. Nothing it reads reaches a "
  "measurement or the bill.")

def shadow_enabled(org_id) -> bool:
  ids = {s.strip() for s in (settings.engine_ai_shadow_org_ids or "").split(",") if s.strip()}
  return "*" in ids or str(org_id) in ids

def _item(row: AiShadowRead) -> dict:
  return {"id": row.id, "sheet_id": row.sheet_id, "page_no": row.page_no, "status": row.status, "mode": row.mode, "prompt_version": row.prompt_version,
    "confidence": (row.ai_value or {}).get("confidence"), "comparison": list(row.comparison or []), "totals": dict(row.totals or {}),
    "problems": list(row.problems or []), "validators": list(row.validators or []), "model": row.model, "error": row.error, "created_at": row.created_at}

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
    if not TASKS.is_on(TASK):
      raise TraceException("The sheet task is switched off.", status_code=403, code="AI_TASK_OFF")
    if mode not in JOBS.MODES:
      raise TraceException("The mode is WEAK or ALL.", status_code=422, code="AI_SHADOW_MODE")
    orchestrator = AIOrchestratorService(self.session)
    state = await orchestrator.state(org)
    if not state.enabled or state.provider is None:
      raise TraceException("AI is off for this company: switch AI on and choose where it may run (consent LOCAL or OUTSIDE).", status_code=403, code="AI_CONSENT_OFF")
    drawing = await self.core._pdf_drawing(org, drawing_id)
    sheets = await self.core.repo.sheets(org, drawing_id)

    rows = await self._rows(org, drawing_id)
    done_keys = set() if force else {r.cache_key for r in rows if r.cache_key and r.status != FAILED}
    legacy = set() if force else {r.sheet_id for r in rows if not r.cache_key and r.prompt_version == C.PROMPT_VERSION and r.status != FAILED}
    wanted = [s for s in sheets if s.id not in legacy and JOBS.needs_reading((s.prep_meta or {}).get("identity"), mode)]
    contents = await asyncio.to_thread(source.drawing_bytes, drawing.storage_key) if wanted else b""
    sha = CACHE.pdf_sha256(contents) if wanted else ""
    region = RG.title_block_region()
    keys = {s.id: CACHE.key(sha, s.page_no, region, TASK, C.PROMPT_VERSION, state.model) for s in wanted}
    queue = [s for s in wanted if keys[s.id] not in done_keys]
    batch = queue[:limit]

    async def ask(prompt: str, png: bytes):
      return await orchestrator.run(organization_id=org, purpose=AIRequestPurpose.SHEET_CLASSIFICATION, entity_type=AIEntityType.DRAWING,
        entity_id=drawing.id, requested_by=user_id, prompt=prompt, image_bytes=png, image_mime_type="image/png")

    async def store_crop(png: bytes) -> str:
      key = f"{org}/{drawing.project_id}/ai-shadow/{uuid4().hex}.png"
      await asyncio.to_thread(upload_fileobj, key, io.BytesIO(png), "image/png")
      return key

    made: list[AiShadowRead] = []
    for sheet in batch:
      rec = await shadow_read(contents=contents, page_no=sheet.page_no, identity=(sheet.prep_meta or {}).get("identity"), mode=mode, ask=ask, store_crop=store_crop,
        cache_key=keys[sheet.id], model=state.model)
      if rec is None:
        continue

      row = AiShadowRead(id=uuid4(), organization_id=org, project_id=drawing.project_id, drawing_id=drawing.id, sheet_id=sheet.id, page_no=sheet.page_no,
        purpose=rec["purpose"], task=rec["task"], cache_key=rec["cache_key"], model=rec["model"], validators=rec["validators"], mode=mode, status=rec["status"],
        prompt_version=rec["prompt_version"], schema_version=rec["schema_version"], crop_key=rec["crop_key"],
        crop=rec["crop"], ai_request_id=rec["ai_request_id"], rule_value=rec["rule_value"], ai_value=rec["ai_value"], comparison=rec["comparison"], totals=rec["totals"],
        problems=rec["problems"], error=rec["error"], created_by_user_id=user_id)
      self.session.add(row)
      await self.session.commit()
      made.append(row)
    return {"drawing_id": drawing.id, "mode": mode, "read": sum(1 for r in made if r.status != FAILED), "failed": sum(1 for r in made if r.status == FAILED),
      "remaining": len(queue) - len(batch), "items": [_item(r) for r in made]}

  async def cost(self, org: UUID, rows: list[AiShadowRead]) -> dict:
    ids = [r.ai_request_id for r in rows if r.ai_request_id]
    if not ids:
      return COST.summarise([])
    found = (await self.session.execute(select(AIRequest.model, AIRequest.input_tokens, AIRequest.output_tokens, AIResponse.latency_ms)
      .outerjoin(AIResponse, AIResponse.ai_request_id == AIRequest.id).where(AIRequest.organization_id == org, AIRequest.id.in_(ids)))).all()
    return COST.summarise([{"model": m, "input_tokens": i, "output_tokens": o, "seconds": (ms or 0) / 1000.0} for m, i, o, ms in found])

  async def summary(self, org: UUID, drawing_id: UUID) -> dict:
    await self.core._pdf_drawing(org, drawing_id)
    sheets = await self.core.repo.sheets(org, drawing_id)
    rows = await self._rows(org, drawing_id)
    latest = [r for r in self._latest(rows) if r.status == "OK"]
    state = await AIOrchestratorService(self.session).state(org)
    totals = {k: 0 for k in CMP.AGREEMENTS}
    by_fact: dict = {}

    for r in latest:
      for rec in r.comparison or []:
        totals[rec["agreement"]] = totals.get(rec["agreement"], 0) + 1
        by_fact.setdefault(rec["fact_key"], {k: 0 for k in CMP.AGREEMENTS})[rec["agreement"]] += 1
    return {"drawing_id": drawing_id, "enabled": shadow_enabled(org), "sheets_total": len(sheets), "sheets_read": len(latest), "totals": totals,
      "by_fact": by_fact, "items": [_item(r) for r in self._latest(rows)], "note": NOTE, "consent": state.consent, "cost": await self.cost(org, rows)}

  async def crop(self, org: UUID, read_id: UUID) -> bytes:
    row = (await self.session.execute(select(AiShadowRead).where(AiShadowRead.id == read_id, AiShadowRead.organization_id == org))).scalar_one_or_none()
    if row is None:
      raise TraceException("That reading is not found.", status_code=404, code="AI_SHADOW_NOT_FOUND")
    return await asyncio.to_thread(download_bytes, row.crop_key)
