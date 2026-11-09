from __future__ import annotations
import asyncio
import copy
from app.modules.drawings_boq.takeoff.ai_reader.models import AiExample, AiShadowRead
from app.core.config import settings
import io
from app.modules.drawings_boq.takeoff.extract.extract_service import ExtractService
from uuid import UUID, uuid4
from sqlalchemy import select
from app.modules.ai_requests.service import AIOrchestratorService
from app.modules.drawings_boq.takeoff.crops import source
from app.core.exceptions import TraceException
from app.modules.drawings_boq.takeoff.ai_reader import jobs as JOBS
from app.modules.drawings_boq.takeoff.ai_reader import notes as NT
from app.modules.drawings_boq.takeoff.ai_reader import schedule as SCH
from app.modules.drawings_boq.takeoff.ai_reader import legend as LG
from app.modules.drawings_boq.takeoff.ai_reader import find as FD
from app.modules.drawings_boq.takeoff.ai_reader import examples as EX
from app.modules.drawings_boq.takeoff.ai_reader import prompts as P
from app.modules.drawings_boq.takeoff.ai_reader import compare as CMP
from app.modules.drawings_boq.takeoff.ai_reader import contract as C
from app.modules.drawings_boq.takeoff.ai_reader import cache as CACHE
from app.modules.drawings_boq.takeoff.ai_reader import cost as COST
from app.modules.drawings_boq.takeoff.ai_reader import regions as RG
from app.modules.drawings_boq.takeoff.ai_reader import tasks as TASKS
from app.modules.drawings_boq.takeoff.extract import sheet_identity as SID
from app.modules.drawings_boq.takeoff.prep import page_role as PRL
from app.modules.ai_requests.models import AIRequestPurpose, AIEntityType, AIRequest, AIResponse
from app.modules.drawings_boq.takeoff.ai_reader.reader import FAILED, OK, TASK, shadow_read
from app.shared.storage import download_bytes, upload_fileobj

NOTE = ("The AI reads the title-block strips and the whole page of a sheet, and only to be measured against the rule reader. Its role counts in a "
  "page's vote only for companies listed in ENGINE_AI_ROLE_VOTE_ORG_IDS. Nothing it reads reaches a measurement or the bill.")

def shadow_enabled(org_id) -> bool:
  ids = {s.strip() for s in (settings.engine_ai_shadow_org_ids or "").split(",") if s.strip()}
  return "*" in ids or str(org_id) in ids

def role_vote_enabled(org_id) -> bool:
  ids = {s.strip() for s in (settings.engine_ai_role_vote_org_ids or "").split(",") if s.strip()}
  return "*" in ids or str(org_id) in ids

def note_enabled(org_id) -> bool:
  ids = {s.strip() for s in (settings.engine_ai_note_org_ids or "").split(",") if s.strip()}
  return "*" in ids or str(org_id) in ids

def schedule_enabled(org_id) -> bool:
  ids = {s.strip() for s in (settings.engine_ai_schedule_org_ids or "").split(",") if s.strip()}
  return "*" in ids or str(org_id) in ids

def legend_enabled(org_id) -> bool:
  ids = {s.strip() for s in (settings.engine_ai_legend_org_ids or "").split(",") if s.strip()}
  return "*" in ids or str(org_id) in ids

def find_enabled(org_id) -> bool:
  ids = {s.strip() for s in (settings.engine_ai_find_org_ids or "").split(",") if s.strip()}
  return "*" in ids or str(org_id) in ids

def examples_enabled(org_id) -> bool:
  ids = {s.strip() for s in (settings.engine_ai_examples_org_ids or "").split(",") if s.strip()}
  return "*" in ids or str(org_id) in ids

def row_example(row: AiExample) -> EX.Example:
  return EX.Example(task=row.task, office=row.office, kind=row.kind, crop_ref=dict(row.crop_ref or {}), words=tuple(row.words or ()), answer=dict(row.answer or {}),
    checked_by=row.checked_by, date=row.checked_on, drawing=row.drawing, shared=bool(row.shared))

def reading_record(rec: dict) -> dict:
  t = rec.get("totals") or {}
  return {"accepted": int(t.get("accepted") or 0), "review": int(t.get("review") or 0), "escalated": int(t.get("escalated") or 0), "support": dict((rec.get("crop") or {}).get("support") or {}),
    "examples": len(((rec.get("crop") or {}).get("examples") or {}).get("ids") or [])}

def apply_vote(sheet, ai_value: dict | None) -> bool:
  meta = copy.deepcopy(sheet.prep_meta or {})
  identity = meta.get("identity") or {}
  if not identity.get("role_vote") or not PRL.apply_ai(identity, ai_value):
    return False
  identity["read_as"] = SID.read_as(identity)
  sheet.prep_meta = meta
  return True

def _item(row: AiShadowRead) -> dict:
  return {"id": row.id, "sheet_id": row.sheet_id, "page_no": row.page_no, "status": row.status, "mode": row.mode, "prompt_version": row.prompt_version,
    "confidence": (row.ai_value or {}).get("confidence"), "comparison": list(row.comparison or []), "totals": dict(row.totals or {}),
    "problems": list(row.problems or []), "validators": list(row.validators or []), "model": row.model, "error": row.error, "created_at": row.created_at,
    "support": dict((row.crop or {}).get("support") or {}), "review": list((row.crop or {}).get("review") or [])}

class AiShadowService(ExtractService):
  async def _bank(self, org: UUID, task: str) -> list:
    rows = (await self.session.execute(select(AiExample).where(AiExample.task == task, (AiExample.organization_id == org) | (AiExample.shared.is_(True))))).scalars().all()
    return [row_example(r) for r in rows]

  async def add_example(self, org: UUID, *, task: str, office, kind, crop_ref: dict, text, row: dict, corrected: dict | None, checked_by: str, date: str, drawing: str, shared: bool = False) -> AiExample:
    ex = EX.from_review(task=task, office=office, kind=kind, crop_ref=crop_ref, text=text, row=row, corrected=corrected, checked_by=checked_by, date=date, drawing=drawing, shared=shared)
    entity = AiExample(id=uuid4(), organization_id=org, task=ex.task, office=ex.office, kind=ex.kind, crop_ref=ex.crop_ref, words=list(ex.words), answer=ex.answer,
      checked_by=ex.checked_by, checked_on=ex.date, drawing=ex.drawing, shared=ex.shared)
    self.session.add(entity)
    await self.session.commit()
    return entity

  async def _shown(self, org: UUID, task: str, name: str, wanted: list, contents: bytes, sha: str) -> dict:
    if not wanted or not examples_enabled(org):
      return {}
    bank = await self._bank(org, task)
    return {s.id: await asyncio.to_thread(EX.for_page, bank=bank, task=task, name=name, contents=contents, page=s.page_no, office=None, drawing=sha) for s in wanted} if bank else {}

  async def _rows(self, org: UUID, drawing_id: UUID, task: str = TASK) -> list[AiShadowRead]:
    return list((await self.session.execute(select(AiShadowRead).where(AiShadowRead.organization_id == org, AiShadowRead.drawing_id == drawing_id, AiShadowRead.task == task)
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

  async def run(self, org: UUID, user_id: UUID, drawing_id: UUID, mode: str, limit: int, force: bool, task: str = TASK) -> dict:
    if task == NT.TASK:
      return await self.run_notes(org, user_id, drawing_id, limit, force)
    if task == SCH.TASK:
      return await self.run_schedules(org, user_id, drawing_id, limit, force)
    if task == LG.TASK:
      return await self.run_legends(org, user_id, drawing_id, mode, limit, force)
    if task == FD.TASK:
      return await self.run_find(org, user_id, drawing_id, limit, force)
    if task != TASK:
      raise TraceException("The task is SHEET, NOTE_FACT, SCHEDULE_ROW, LEGEND_ENTRY or FIND.", status_code=422, code="AI_SHADOW_TASK")
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
    region = RG.sheet_region()
    keys = {s.id: CACHE.key(sha, s.page_no, region, TASK, C.PROMPT_VERSION, state.model) for s in wanted}
    queue = [s for s in wanted if keys[s.id] not in done_keys]
    batch = queue[:limit]

    async def ask(prompt: str, png: bytes, images: list):
      return await orchestrator.run(organization_id=org, purpose=AIRequestPurpose.SHEET_CLASSIFICATION, entity_type=AIEntityType.DRAWING,
        entity_id=drawing.id, requested_by=user_id, prompt=prompt, image_bytes=png, image_mime_type="image/png", images=images)

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
      if rec["status"] == OK and role_vote_enabled(org):
        apply_vote(sheet, rec["ai_value"])
      await self.session.commit()
      made.append(row)
      
    if role_vote_enabled(org):
      stored = {r.sheet_id: r for r in reversed(rows) if r.status == OK and r.cache_key}
      again = [s for s in wanted if s.id not in {m.sheet_id for m in made} and stored.get(s.id) is not None and stored[s.id].cache_key == keys[s.id]]
      if any([apply_vote(s, stored[s.id].ai_value) for s in again]):
        await self.session.commit()
    return {"drawing_id": drawing.id, "mode": mode, "read": sum(1 for r in made if r.status != FAILED), "failed": sum(1 for r in made if r.status == FAILED),
      "remaining": len(queue) - len(batch), "items": [_item(r) for r in made]}

  async def run_notes(self, org: UUID, user_id: UUID, drawing_id: UUID, limit: int, force: bool) -> dict:
    if not shadow_enabled(org):
      raise TraceException("AI shadow reading is not switched on for this company.", status_code=403, code="AI_SHADOW_OFF")
    if not TASKS.is_on(NT.TASK):
      raise TraceException("The note task is switched off.", status_code=403, code="AI_TASK_OFF")
    orchestrator = AIOrchestratorService(self.session)
    state = await orchestrator.state(org)
    if not state.enabled or state.provider is None:
      raise TraceException("AI is off for this company: switch AI on and choose where it may run (consent LOCAL or OUTSIDE).", status_code=403, code="AI_CONSENT_OFF")
    
    drawing = await self.core._pdf_drawing(org, drawing_id)
    sheets = await self.core.repo.sheets(org, drawing_id)
    rows = await self._rows(org, drawing_id, NT.TASK)
    done_keys = set() if force else {r.cache_key for r in rows if r.cache_key and r.status != FAILED}
    wanted = [s for s in sheets if JOBS.note_page(s.prep_meta)]
    contents = await asyncio.to_thread(source.drawing_bytes, drawing.storage_key) if wanted else b""
    sha = CACHE.pdf_sha256(contents) if wanted else ""
    region = RG.note_region()
    name = TASKS.prompt_name(NT.TASK)
    shown = await self._shown(org, NT.TASK, name, wanted, contents, sha)
    keys = {s.id: CACHE.key(sha, s.page_no, region, NT.TASK, P.load(name)["version"], state.model, EX.state(shown.get(s.id, []))) for s in wanted}
    queue = [s for s in wanted if keys[s.id] not in done_keys]
    batch = queue[:limit]
    async def ask(prompt: str, png: bytes, images: list, model: str | None = None):
      return await orchestrator.run(organization_id=org, purpose=AIRequestPurpose.NOTE_FACT, entity_type=AIEntityType.DRAWING,
        entity_id=drawing.id, requested_by=user_id, prompt=prompt, image_bytes=png, image_mime_type="image/png", images=images, model=model)

    async def store_crop(png: bytes) -> str:
      key = f"{org}/{drawing.project_id}/ai-shadow/{uuid4().hex}.png"
      await asyncio.to_thread(upload_fileobj, key, io.BytesIO(png), "image/png")
      return key

    made: list[AiShadowRead] = []
    for sheet in batch:
      rule_items = ((sheet.prep_meta or {}).get("facts") or {}).get("items") or []
      rec = await NT.read_notes(contents=contents, page_no=sheet.page_no, ask=ask, store_crop=store_crop, cache_key=keys[sheet.id], model=state.model, rule_items=rule_items, prompt_name=name, examples=shown.get(sheet.id, []))
      row = AiShadowRead(id=uuid4(), organization_id=org, project_id=drawing.project_id, drawing_id=drawing.id, sheet_id=sheet.id, page_no=sheet.page_no,
        purpose=rec["purpose"], task=rec["task"], cache_key=rec["cache_key"], model=rec["model"], validators=rec["validators"], mode="ALL", status=rec["status"],
        prompt_version=rec["prompt_version"], schema_version=rec["schema_version"], crop_key=rec["crop_key"],
        crop=rec["crop"], ai_request_id=rec["ai_request_id"], rule_value=rec["rule_value"], ai_value=rec["ai_value"], comparison=rec["comparison"], totals=rec["totals"],
        problems=rec["problems"], error=rec["error"], created_by_user_id=user_id)
      self.session.add(row)
      
      if rec["status"] == OK and note_enabled(org):
        sheet.prep_meta = {**(sheet.prep_meta or {}), "ai_facts": rec["items"], "ai_reading": {**((sheet.prep_meta or {}).get("ai_reading") or {}), NT.TASK: reading_record(rec)}}
      await self.session.commit()
      made.append(row)
      
    if note_enabled(org):
      stored = {r.sheet_id: r for r in reversed(rows) if r.status == OK and r.cache_key}
      again = [s for s in wanted if s.id not in {m.sheet_id for m in made} and stored.get(s.id) is not None and stored[s.id].cache_key == keys[s.id]]
      for s in again:
        s.prep_meta = {**(s.prep_meta or {}), "ai_facts": NT.accepted_from(stored[s.id].ai_value, ((s.prep_meta or {}).get("facts") or {}).get("items") or [])}
      if again:
        await self.session.commit()
    return {"drawing_id": drawing.id, "mode": "ALL", "read": sum(1 for r in made if r.status != FAILED), "failed": sum(1 for r in made if r.status == FAILED),
      "remaining": len(queue) - len(batch), "items": [_item(r) for r in made]}

  async def run_schedules(self, org: UUID, user_id: UUID, drawing_id: UUID, limit: int, force: bool) -> dict:
    """Reads the schedules of the pages that carry them, a few pages a request, records every read beside the rule reader's, and, for a company listed in ENGINE_AI_SCHEDULE_ORG_IDS, keeps the rows that passed on the sheet."""
    if not shadow_enabled(org):
      raise TraceException("AI shadow reading is not switched on for this company.", status_code=403, code="AI_SHADOW_OFF")
    if not TASKS.is_on(SCH.TASK):
      raise TraceException("The schedule task is switched off.", status_code=403, code="AI_TASK_OFF")
    orchestrator = AIOrchestratorService(self.session)
    state = await orchestrator.state(org)
    if not state.enabled or state.provider is None:
      raise TraceException("AI is off for this company: switch AI on and choose where it may run (consent LOCAL or OUTSIDE).", status_code=403, code="AI_CONSENT_OFF")
    drawing = await self.core._pdf_drawing(org, drawing_id)
    sheets = await self.core.repo.sheets(org, drawing_id)
    rows = await self._rows(org, drawing_id, SCH.TASK)
    done_keys = set() if force else {r.cache_key for r in rows if r.cache_key and r.status != FAILED}
    wanted = [s for s in sheets if JOBS.schedule_page(s.prep_meta)]
    contents = await asyncio.to_thread(source.drawing_bytes, drawing.storage_key) if wanted else b""
    sha = CACHE.pdf_sha256(contents) if wanted else ""
    region = RG.schedule_region()
    name = TASKS.prompt_name(SCH.TASK)
    shown = await self._shown(org, SCH.TASK, name, wanted, contents, sha)
    keys = {s.id: CACHE.key(sha, s.page_no, region, SCH.TASK, P.load(name)["version"], state.model, EX.state(shown.get(s.id, []))) for s in wanted}
    queue = [s for s in wanted if keys[s.id] not in done_keys]
    batch = queue[:limit]

    async def ask(prompt: str, png: bytes, images: list, model: str | None = None):
      return await orchestrator.run(organization_id=org, purpose=AIRequestPurpose.SCHEDULE_ROW, entity_type=AIEntityType.DRAWING,
        entity_id=drawing.id, requested_by=user_id, prompt=prompt, image_bytes=png, image_mime_type="image/png", images=images, model=model)

    async def store_crop(png: bytes) -> str:
      key = f"{org}/{drawing.project_id}/ai-shadow/{uuid4().hex}.png"
      await asyncio.to_thread(upload_fileobj, key, io.BytesIO(png), "image/png")
      return key

    made: list[AiShadowRead] = []
    for sheet in batch:
      tables = (sheet.prep_meta or {}).get("structure_tables") or {}
      rec = await SCH.read_schedules(contents=contents, page_no=sheet.page_no, ask=ask, store_crop=store_crop, cache_key=keys[sheet.id], model=state.model, tables=tables, prompt_name=name, examples=shown.get(sheet.id, []))
      row = AiShadowRead(id=uuid4(), organization_id=org, project_id=drawing.project_id, drawing_id=drawing.id, sheet_id=sheet.id, page_no=sheet.page_no,
        purpose=rec["purpose"], task=rec["task"], cache_key=rec["cache_key"], model=rec["model"], validators=rec["validators"], mode="ALL", status=rec["status"],
        prompt_version=rec["prompt_version"], schema_version=rec["schema_version"], crop_key=rec["crop_key"],
        crop=rec["crop"], ai_request_id=rec["ai_request_id"], rule_value=rec["rule_value"], ai_value=rec["ai_value"], comparison=rec["comparison"], totals=rec["totals"],
        problems=rec["problems"], error=rec["error"], created_by_user_id=user_id)
      self.session.add(row)
      
      if rec["status"] == OK and schedule_enabled(org):
        sheet.prep_meta = {**(sheet.prep_meta or {}), "ai_schedule": rec["items"], "ai_reading": {**((sheet.prep_meta or {}).get("ai_reading") or {}), SCH.TASK: reading_record(rec)}}
      await self.session.commit()
      made.append(row)
      
    if schedule_enabled(org):
      stored = {r.sheet_id: r for r in reversed(rows) if r.status == OK and r.cache_key}
      again = [s for s in wanted if s.id not in {m.sheet_id for m in made} and stored.get(s.id) is not None and stored[s.id].cache_key == keys[s.id]]
      for s in again:
        s.prep_meta = {**(s.prep_meta or {}), "ai_schedule": SCH.accepted_from(stored[s.id].ai_value, (s.prep_meta or {}).get("structure_tables") or {})}
      if again:
        await self.session.commit()
    return {"drawing_id": drawing.id, "mode": "ALL", "read": sum(1 for r in made if r.status != FAILED), "failed": sum(1 for r in made if r.status == FAILED),
      "remaining": len(queue) - len(batch), "items": [_item(r) for r in made]}

  async def run_find(self, org: UUID, user_id: UUID, drawing_id: UUID, limit: int, force: bool) -> dict:
    if not shadow_enabled(org):
      raise TraceException("AI shadow reading is not switched on for this company.", status_code=403, code="AI_SHADOW_OFF")
    if not TASKS.is_on(FD.TASK):
      raise TraceException("The find task is switched off.", status_code=403, code="AI_TASK_OFF")
    orchestrator = AIOrchestratorService(self.session)
    state = await orchestrator.state(org)
    if not state.enabled or state.provider is None:
      raise TraceException("AI is off for this company: switch AI on and choose where it may run (consent LOCAL or OUTSIDE).", status_code=403, code="AI_CONSENT_OFF")
    drawing = await self.core._pdf_drawing(org, drawing_id)
    sheets = await self.core.repo.sheets(org, drawing_id)
    rows = await self._rows(org, drawing_id, FD.TASK)
    done_keys = set() if force else {r.cache_key for r in rows if r.cache_key and r.status != FAILED}
    wanted = [s for s in sheets if JOBS.find_page(s.prep_meta)]
    contents = await asyncio.to_thread(source.drawing_bytes, drawing.storage_key) if wanted else b""
    sha = CACHE.pdf_sha256(contents) if wanted else ""
    region = RG.page_region()
    keys = {s.id: CACHE.key(sha, s.page_no, region, FD.TASK, FD.PROMPT_VERSION, state.model) for s in wanted}
    queue = [s for s in wanted if keys[s.id] not in done_keys]
    batch = queue[:limit]

    async def ask(prompt: str, png: bytes, images: list, model: str | None = None):
      return await orchestrator.run(organization_id=org, purpose=AIRequestPurpose.REGION_FIND, entity_type=AIEntityType.DRAWING,
        entity_id=drawing.id, requested_by=user_id, prompt=prompt, image_bytes=png, image_mime_type="image/png", images=images, model=model)

    async def store_crop(png: bytes) -> str:
      key = f"{org}/{drawing.project_id}/ai-shadow/{uuid4().hex}.png"
      await asyncio.to_thread(upload_fileobj, key, io.BytesIO(png), "image/png")
      return key

    made: list[AiShadowRead] = []
    for sheet in batch:
      rec = await FD.read_find(contents=contents, page_no=sheet.page_no, ask=ask, store_crop=store_crop, cache_key=keys[sheet.id], model=state.model)
      row = AiShadowRead(id=uuid4(), organization_id=org, project_id=drawing.project_id, drawing_id=drawing.id, sheet_id=sheet.id, page_no=sheet.page_no,
        purpose=rec["purpose"], task=rec["task"], cache_key=rec["cache_key"], model=rec["model"], validators=rec["validators"], mode="ALL", status=rec["status"],
        prompt_version=rec["prompt_version"], schema_version=rec["schema_version"], crop_key=rec["crop_key"],
        crop=rec["crop"], ai_request_id=rec["ai_request_id"], rule_value=rec["rule_value"], ai_value=rec["ai_value"], comparison=rec["comparison"], totals=rec["totals"],
        problems=rec["problems"], error=rec["error"], created_by_user_id=user_id)
      self.session.add(row)
      
      if rec["status"] == OK and rec["proposals"] and find_enabled(org):
        meta = {**(sheet.prep_meta or {}), "ai_find": rec["proposals"]}
        meta.pop("analysis_version", None)
        sheet.prep_meta = meta
      await self.session.commit()
      made.append(row)
    return {"drawing_id": drawing.id, "mode": "ALL", "read": sum(1 for r in made if r.status != FAILED), "failed": sum(1 for r in made if r.status == FAILED),
      "remaining": len(queue) - len(batch), "items": [_item(r) for r in made]}

  async def run_legends(self, org: UUID, user_id: UUID, drawing_id: UUID, mode: str, limit: int, force: bool) -> dict:
    if not shadow_enabled(org):
      raise TraceException("AI shadow reading is not switched on for this company.", status_code=403, code="AI_SHADOW_OFF")
    if not TASKS.is_on(LG.TASK):
      raise TraceException("The legend task is switched off.", status_code=403, code="AI_TASK_OFF")
    if mode not in JOBS.MODES:
      raise TraceException("The mode is WEAK or ALL.", status_code=422, code="AI_SHADOW_MODE")
    orchestrator = AIOrchestratorService(self.session)
    state = await orchestrator.state(org)
    if not state.enabled or state.provider is None:
      raise TraceException("AI is off for this company: switch AI on and choose where it may run (consent LOCAL or OUTSIDE).", status_code=403, code="AI_CONSENT_OFF")
    drawing = await self.core._pdf_drawing(org, drawing_id)
    sheets = await self.core.repo.sheets(org, drawing_id)
    rows = await self._rows(org, drawing_id, LG.TASK)
    done_keys = set() if force else {r.cache_key for r in rows if r.cache_key and r.status != FAILED}
    wanted = [s for s in sheets if JOBS.legend_page(s.prep_meta)]
    contents = await asyncio.to_thread(source.drawing_bytes, drawing.storage_key) if wanted else b""
    sha = CACHE.pdf_sha256(contents) if wanted else ""
    region = LG.region(mode)
    keys = {s.id: CACHE.key(sha, s.page_no, region, LG.TASK, LG.PROMPT_VERSION, state.model) for s in wanted}
    queue = [s for s in wanted if keys[s.id] not in done_keys]
    batch = queue[:limit]

    async def ask(prompt: str, png: bytes, images: list):
      return await orchestrator.run(organization_id=org, purpose=AIRequestPurpose.LEGEND_ENTRY, entity_type=AIEntityType.DRAWING,
        entity_id=drawing.id, requested_by=user_id, prompt=prompt, image_bytes=png, image_mime_type="image/png", images=images)

    async def store_crop(png: bytes) -> str:
      key = f"{org}/{drawing.project_id}/ai-shadow/{uuid4().hex}.png"
      await asyncio.to_thread(upload_fileobj, key, io.BytesIO(png), "image/png")
      return key

    made: list[AiShadowRead] = []
    for sheet in batch:
      legend_rows = (sheet.prep_meta or {}).get("electrical_legend") or []
      rec = await LG.read_legends(contents=contents, page_no=sheet.page_no, rows=legend_rows, mode=mode, ask=ask, store_crop=store_crop, cache_key=keys[sheet.id], model=state.model)
      row = AiShadowRead(id=uuid4(), organization_id=org, project_id=drawing.project_id, drawing_id=drawing.id, sheet_id=sheet.id, page_no=sheet.page_no,
        purpose=rec["purpose"], task=rec["task"], cache_key=rec["cache_key"], model=rec["model"], validators=rec["validators"], mode=mode, status=rec["status"],
        prompt_version=rec["prompt_version"], schema_version=rec["schema_version"], crop_key=rec["crop_key"],
        crop=rec["crop"], ai_request_id=rec["ai_request_id"], rule_value=rec["rule_value"], ai_value=rec["ai_value"], comparison=rec["comparison"], totals=rec["totals"],
        problems=rec["problems"], error=rec["error"], created_by_user_id=user_id)
      self.session.add(row)
      
      if rec["status"] == OK and legend_enabled(org):
        sheet.prep_meta = {**(sheet.prep_meta or {}), "ai_legend": rec["items"]}
      await self.session.commit()
      made.append(row)
      
    if legend_enabled(org):
      stored = {r.sheet_id: r for r in reversed(rows) if r.status == OK and r.cache_key}
      again = [s for s in wanted if s.id not in {m.sheet_id for m in made} and stored.get(s.id) is not None and stored[s.id].cache_key == keys[s.id]]
      for s in again:
        s.prep_meta = {**(s.prep_meta or {}), "ai_legend": LG.accepted_from(stored[s.id].ai_value, (s.prep_meta or {}).get("electrical_legend") or [])}
      if again:
        await self.session.commit()
    return {"drawing_id": drawing.id, "mode": mode, "read": sum(1 for r in made if r.status != FAILED), "failed": sum(1 for r in made if r.status == FAILED),
      "remaining": len(queue) - len(batch), "items": [_item(r) for r in made]}

  async def cost(self, org: UUID, rows: list[AiShadowRead]) -> dict:
    ids = [r.ai_request_id for r in rows if r.ai_request_id]
    if not ids:
      return COST.summarise([])
    found = (await self.session.execute(select(AIRequest.model, AIRequest.input_tokens, AIRequest.output_tokens, AIResponse.latency_ms)
      .outerjoin(AIResponse, AIResponse.ai_request_id == AIRequest.id).where(AIRequest.organization_id == org, AIRequest.id.in_(ids)))).all()
    return COST.summarise([{"model": m, "input_tokens": i, "output_tokens": o, "seconds": (ms or 0) / 1000.0} for m, i, o, ms in found])

  async def summary(self, org: UUID, drawing_id: UUID, task: str = TASK) -> dict:
    await self.core._pdf_drawing(org, drawing_id)
    sheets = await self.core.repo.sheets(org, drawing_id)
    rows = await self._rows(org, drawing_id, task)
    latest = [r for r in self._latest(rows) if r.status == "OK"]
    state = await AIOrchestratorService(self.session).state(org)
    totals = {k: 0 for k in CMP.AGREEMENTS}
    by_fact: dict = {}

    for r in latest:
      for rec in r.comparison or []:
        totals[rec["agreement"]] = totals.get(rec["agreement"], 0) + 1
        by_fact.setdefault(rec["fact_key"], {k: 0 for k in CMP.AGREEMENTS})[rec["agreement"]] += 1
    return {"drawing_id": drawing_id, "enabled": shadow_enabled(org), "sheets_total": len(sheets), "sheets_read": len(latest), "totals": totals,
      "by_fact": by_fact, "items": [_item(r) for r in self._latest(rows)], "note": NOTE, "consent": state.consent, "cost": await self.cost(org, rows),
      "cost_per_accepted": COST.per_accepted([self.cost_record(r, str(drawing_id), self.page_accepted(sheets, r)) for r in rows if r.status != FAILED or (r.crop or {}).get("reads")])}

  @staticmethod
  def page_accepted(sheets: list, row: AiShadowRead) -> int | None:
    if row.task != FD.TASK:
      return None
    sheet = next((s for s in sheets if s.id == row.sheet_id), None)
    return int((((sheet.prep_meta if sheet else None) or {}).get("page_model") or {}).get("proposed", {}).get("accepted") or 0)

  @staticmethod
  def cost_record(row: AiShadowRead, set_name: str, accepted: int | None = None) -> dict:
    t = row.totals or {}
    return {"task": row.task, "set": set_name, "accepted": int(t.get("accepted") or 0) if accepted is None else accepted, "review": int(t.get("review") or 0), "escalated": int(t.get("escalated") or 0), "reads": list((row.crop or {}).get("reads") or [])}

  async def crop(self, org: UUID, read_id: UUID) -> bytes:
    row = (await self.session.execute(select(AiShadowRead).where(AiShadowRead.id == read_id, AiShadowRead.organization_id == org))).scalar_one_or_none()
    if row is None:
      raise TraceException("That reading is not found.", status_code=404, code="AI_SHADOW_NOT_FOUND")
    return await asyncio.to_thread(download_bytes, row.crop_key)
