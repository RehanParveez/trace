from __future__ import annotations
import asyncio
import hashlib
import os
import tempfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import PurePosixPath
from uuid import UUID, uuid4
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import TraceException
from app.modules.ai_requests.models import AIEntityType, AIRequestPurpose
from app.modules.ai_requests.service import AIOrchestratorService
from app.modules.drawings_boq.models import (AssemblyRecipeComponent, BOQItem, BOQItemRateSource, BOQItemSourceElement, BOQItemStatus, BOQItemType, BOQVersion, Drawing, DrawingElement, DrawingFormat, 
  DrawingStatus, LabourRate, MaterialLibrary, MaterialNormalizationCache, MeasurementRuleSet, ModelAuditResult
)
from app.modules.drawings_boq.pdf_extraction import build_schedule_extraction_prompt, extract_pdf_text, parse_schedule_extraction_response
from app.modules.drawings_boq.repository import ( AssemblyRecipeRepository, BOQItemRepository, BOQVersionRepository, DrawingElementRepository, DrawingRepository, ElementTypeMappingRepository, LabourRateRepository,
  MaterialLibraryRepository, MaterialNormalizationCacheRepository, MeasurementRuleSetRepository, ModelAuditResultRepository,
)
from app.modules.drawings_boq.schemas import BOQCustomItemCreateRequest, BOQItemUpdateRequest, BOQVersionCreateRequest, BOQVersionUpdateRequest, LabourRateCreateRequest, LabourRateUpdateRequest, MaterialLibraryCreateRequest, MaterialLibraryUpdateRequest
from app.modules.projects.repository import ProjectRepository
from app.modules.subscriptions.service import SubscriptionService
from app.shared.idempotency import get_cached_response, store_response
from app.shared.storage import MAX_UPLOAD_BYTES, build_storage_key, delete_object, download_to_path, format_bytes, upload_fileobj
from sqlalchemy import select
from app.modules.drawings_boq.export import build_boq_pdf, build_boq_xlsx
from app.modules.drawings_boq.words import rupees_in_words
from app.modules.identity.models import Organization
from app.modules.audit.models import AuditAction, AuditEntityType
from app.modules.audit.service import AuditLogService
from decimal import Decimal
from app.core.redis import redis_client
from app.modules.identity.rate_limit import RateLimiter
from app.core.config import settings
from app.modules.drawings_boq.ifc_extraction import aggregate_drawing_elements, extract_quantity, resolve_material_name
from app.modules.drawings_boq.ifc_types import TARGET_IFC_TYPES
from app.modules.drawings_boq.ifc_extraction import AggregatedGroup, aggregate_drawing_elements

SUPPORTED_UPLOAD_FORMATS = {".ifc": DrawingFormat.IFC}

REFERENCE_ONLY_FORMATS = {".pdf": DrawingFormat.PDF}

FILE_MEDIA_TYPES = {
  ".pdf": "application/pdf",
}

UNSUPPORTED_FORMAT_GUIDANCE = {
  ".rvt": (
    "RVT files can't be parsed directly. Export an IFC file from Revit "
    "(File > Export > IFC) for automatic BOQ generation, or upload a PDF "
    "to keep this drawing as a reference."
  ),
  ".dwg": (
    "DWG isn't parsed automatically yet — export to IFC for automatic "
    "BOQ generation, or upload a PDF to keep this drawing as a reference."
  ),
  ".dxf": (
    "DXF isn't parsed automatically yet — export to IFC for automatic "
    "BOQ generation, or upload a PDF to keep this drawing as a reference."
  ),
}

def _looks_like_ifc(contents: bytes) -> bool:
  header = contents[:200].lstrip(b"\xef\xbb\xbf \t\r\n")
  return header.startswith(b"ISO-10303-21;")

class DrawingBOQService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.drawings = DrawingRepository(session)
    self.elements = DrawingElementRepository(session)
    self.boq_versions = BOQVersionRepository(session)
    self.boq_items = BOQItemRepository(session)
    self.material_library = MaterialLibraryRepository(session)
    self.material_cache = MaterialNormalizationCacheRepository(session)
    self.labour_rates = LabourRateRepository(session)
    self.projects = ProjectRepository(session)
    self.subscriptions = SubscriptionService(session)
    self.audit = AuditLogService(session)
    self.rate_limiter = RateLimiter(redis_client)
    self.rule_sets = MeasurementRuleSetRepository(session)
    self.element_mappings = ElementTypeMappingRepository(session)
    self.recipes = AssemblyRecipeRepository(session)
    self.model_audits = ModelAuditResultRepository(session)

  async def _require_project(
    self,
    organization_id: UUID,
    project_id: UUID,
  ):
    project = await self.projects.get_by_id_and_org(
      project_id, organization_id
    )
    if project is None:
      raise TraceException(
        "Project not found.",
        status_code=404,
        code="PROJECT_NOT_FOUND",
      )
    return project

  async def upload_drawing(
    self,
    organization_id: UUID,
    project_id: UUID,
    user_id: UUID,
    file: UploadFile,
    idempotency_key: str | None,
  ) -> Drawing:
    from app.modules.drawings_boq.tasks import parse_drawing_task
    await self._require_project(organization_id, project_id)

    if idempotency_key:
      cached = await get_cached_response(
        organization_id, "drawing_upload", idempotency_key
      )
      if cached is not None:
        existing = await self.drawings.get_by_id_and_org(
          UUID(cached["drawing_id"]), organization_id
        )
        if existing is not None:
          return existing

    suffix = PurePosixPath(file.filename or "").suffix.lower()

    if suffix in UNSUPPORTED_FORMAT_GUIDANCE:
      raise TraceException(
        UNSUPPORTED_FORMAT_GUIDANCE[suffix],
        status_code=422,
        code="UNSUPPORTED_DRAWING_FORMAT",
      )

    drawing_format = SUPPORTED_UPLOAD_FORMATS.get(suffix) or REFERENCE_ONLY_FORMATS.get(suffix)
    if drawing_format is None:
      raise TraceException(
        "Unrecognized file type. Upload an .ifc file for automatic BOQ "
        "generation, or a .pdf to keep as a reference drawing.",
        status_code=422,
        code="UNSUPPORTED_DRAWING_FORMAT",
      )

    is_auto_parsed = suffix in SUPPORTED_UPLOAD_FORMATS

    await self.subscriptions.check_quota(organization_id, "drawings")

    CHUNK_SIZE = 1024 * 1024  

    chunks: list[bytes] = []
    total_size = 0

    while True:
      chunk = await file.read(CHUNK_SIZE)
      if not chunk:
        break
      total_size += len(chunk)
      if total_size > MAX_UPLOAD_BYTES:
        raise TraceException(
          f"File is too large. The maximum upload size is "
          f"{format_bytes(MAX_UPLOAD_BYTES)}.",
          status_code=413,
          code="FILE_TOO_LARGE",
        )
      chunks.append(chunk)

    contents = b"".join(chunks)
    file_size_bytes = total_size

    if file_size_bytes == 0:
      raise TraceException(
        "The uploaded file is empty.",
        status_code=422,
        code="EMPTY_UPLOAD",
      )

    if drawing_format == SUPPORTED_UPLOAD_FORMATS.get(suffix) and not _looks_like_ifc(contents):
      raise TraceException(
        "This file doesn't look like a valid IFC file. It may be corrupted or mislabeled.",
        status_code=422,
        code="INVALID_IFC_CONTENT",
      )

    await self.subscriptions.check_quota(
      organization_id, "storage_bytes", file_size_bytes
    )

    storage_key = build_storage_key(
      organization_id, project_id, file.filename or f"drawing{suffix}"
    )

    await asyncio.to_thread(
      upload_fileobj, storage_key, BytesIO(contents), file.content_type
    )

    now = datetime.now(timezone.utc)
    drawing_id = uuid4()

    drawing = Drawing(
      id=drawing_id,
      organization_id=organization_id,
      project_id=project_id,
      uploaded_by_user_id=user_id,
      original_filename=file.filename or f"drawing{suffix}",
      storage_key=storage_key,
      format=drawing_format,
      status=DrawingStatus.UPLOADED if is_auto_parsed else DrawingStatus.PARSED,
      file_size_bytes=file_size_bytes,
      parsed_at=None if is_auto_parsed else now,
      revision_group_id=drawing_id,
      revision_label=None,
      is_current_revision=True,
    )

    drawing = await self.drawings.create(drawing)
    try:
      await self.subscriptions.increment_usage_many(
        organization_id,
        {"drawings": 1, "storage_bytes": file_size_bytes},
      )
    except Exception:
      await asyncio.to_thread(delete_object, storage_key)
      raise

    await self.session.commit()
    
    await self.audit.log(
      organization_id,
      user_id,
      AuditEntityType.DRAWING,
      drawing.id,
      AuditAction.CREATE,
      f'Uploaded drawing "{drawing.original_filename}"',
    )

    if idempotency_key:
      await store_response(
        organization_id,
        "drawing_upload",
        idempotency_key,
        {"drawing_id": str(drawing.id)},
      )

    if is_auto_parsed:
      parse_drawing_task.apply_async(
        args=[str(drawing.id)], queue="bim_parsing"
      )

    return drawing
  
  async def extract_and_generate_boq(
    self,
    organization_id: UUID,
    drawing: Drawing,
    ifc_file,
    boq_version_id: UUID,
    actor_user_id: UUID,
  ) -> dict:
    created_elements: list[DrawingElement] = []
    skipped_zero_or_missing_quantity = 0

    for ifc_type in TARGET_IFC_TYPES:
      for element in ifc_file.by_type(ifc_type):
        quantity_result = extract_quantity(element)
        if quantity_result is None:
          skipped_zero_or_missing_quantity += 1
          continue
        quantity, unit = quantity_result

        material_name, is_generic_fallback = resolve_material_name(element)

        drawing_element = DrawingElement(
          id=uuid4(),
          organization_id=organization_id,
          drawing_id=drawing.id,
          ifc_global_id=getattr(element, "GlobalId", None),
          ifc_type=element.is_a(),
          name=getattr(element, "Name", None),
          raw_material_text=material_name,
          unit=unit,
          quantity=quantity,
          properties={"is_generic_fallback": is_generic_fallback},
        )
        self.session.add(drawing_element)
        created_elements.append(drawing_element)

    await self.session.flush()

    boq_version = await self.boq_versions.get_by_id_and_org(
      boq_version_id,
      organization_id,
    )

    if boq_version is None:
      raise TraceException(
        "BOQ version not found.",
        status_code=404,
        code="BOQ_VERSION_NOT_FOUND",
      )

    result = await self.generate_boq_from_elements(
      organization_id=organization_id,
      drawing=drawing,
      elements=created_elements,
      boq_version=boq_version,
      actor_user_id=actor_user_id,
    )

    result.update({
      "elements_extracted": len(created_elements),
      "elements_skipped_zero_or_missing_quantity": (
        skipped_zero_or_missing_quantity
      ),
    })

    await self.session.commit()
    return result

  
  async def get_drawing(
    self,
    organization_id: UUID,
    drawing_id: UUID,
  ) -> Drawing:
    drawing = await self.drawings.get_by_id_and_org(
      drawing_id, organization_id
    )
    if drawing is None:
      raise TraceException(
        "Drawing not found.",
        status_code=404,
        code="DRAWING_NOT_FOUND",
      )
    return drawing

  async def list_drawings(
    self,
    organization_id: UUID,
    project_id: UUID,
  ) -> list[Drawing]:
    await self._require_project(organization_id, project_id)
    return await self.drawings.list_by_project(organization_id, project_id)

  async def list_elements(
    self,
    organization_id: UUID,
    drawing_id: UUID,
  ) -> list[DrawingElement]:
    await self.get_drawing(organization_id, drawing_id)
    return await self.elements.list_by_drawing(drawing_id, organization_id)

  async def get_drawing_file(
    self,
    organization_id: UUID,
    drawing_id: UUID,
  ) -> tuple[bytes, str, str]:
    drawing = await self.get_drawing(organization_id, drawing_id)

    suffix = PurePosixPath(drawing.original_filename or "").suffix.lower()
    media_type = FILE_MEDIA_TYPES.get(suffix, "application/octet-stream")

    with tempfile.TemporaryDirectory() as tmp_dir:
      local_path = os.path.join(tmp_dir, f"drawing{suffix}")
      await asyncio.to_thread(download_to_path, drawing.storage_key, local_path)
      with open(local_path, "rb") as handle:
        contents = handle.read()

    return contents, media_type, drawing.original_filename

  async def list_boq_versions(
    self,
    organization_id: UUID,
    project_id: UUID,
  ) -> list[BOQVersion]:
    await self._require_project(organization_id, project_id)
    return await self.boq_versions.list_by_project(organization_id, project_id)

  async def create_boq_version(
    self,
    organization_id: UUID,
    project_id: UUID,
    payload: BOQVersionCreateRequest,
  ) -> BOQVersion:
    await self._require_project(organization_id, project_id)

    version = BOQVersion(
      id=uuid4(),
      organization_id=organization_id,
      project_id=project_id,
      drawing_id=None,
      label=payload.label.strip() or "Manual BOQ",
    )
    version = await self.boq_versions.create(version)
    await self.session.commit()
    return version
  
  async def suggest_items_from_pdf(
    self,
    organization_id: UUID,
    drawing_id: UUID,
    user_id: UUID,
  ) -> dict:
    drawing = await self.get_drawing(organization_id, drawing_id)

    if drawing.format != DrawingFormat.PDF:
     raise TraceException(
      "AI line-item suggestions are only available for PDF drawings.",
      status_code=422,
      code="DRAWING_NOT_PDF",
    )
    existing_elements = await self.elements.list_by_drawing(
    drawing_id, organization_id
    )

    if any(
     e.properties.get("source") == "pdf_ai_extraction"
     for e in existing_elements
    ):
     raise TraceException(
      "Items have already been suggested for this drawing. "
      "Delete the existing draft items first if you want to re-run extraction.",
      status_code=409,
      code="PDF_ITEMS_ALREADY_SUGGESTED",
    )

    await self.subscriptions.check_quota(organization_id, "ai_requests")
    await self.rate_limiter.check(
      key=f"ai_per_org:{organization_id}",
      limit=settings.rate_limit_ai_per_org_per_minute,
      window_seconds=60,
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
      local_path = os.path.join(tmp_dir, "drawing.pdf")
      await asyncio.to_thread(download_to_path, drawing.storage_key, local_path)
      with open(local_path, "rb") as handle:
        contents = handle.read()

    drawing_text = await asyncio.to_thread(extract_pdf_text, contents)
    existing_versions = await self.boq_versions.list_by_project(
      organization_id, drawing.project_id
    )
    version = next(
      (candidate for candidate in existing_versions if candidate.drawing_id == drawing.id),
      None,
    )

    if version is None:
      version = await self.boq_versions.create(
        BOQVersion(
          id=uuid4(),
          organization_id=organization_id,
          project_id=drawing.project_id,
          drawing_id=drawing.id,
          label=f"{drawing.original_filename} — AI-assisted",
        )
      )
      await self.session.flush()

    if not drawing_text:
      await self.session.commit()
      return {"boq_version_id": version.id, "created_item_count": 0, "items": []}

    orchestrator = AIOrchestratorService(self.session)
    result = await orchestrator.run(
      organization_id=organization_id,
      purpose=AIRequestPurpose.PDF_SCHEDULE_EXTRACTION,
      entity_type=AIEntityType.DRAWING,
      entity_id=drawing.id,
      prompt=build_schedule_extraction_prompt(drawing_text),
    )

    await self.subscriptions.increment_usage(organization_id, "ai_requests")

    if not result.success or not result.parsed_output:
      await self.session.commit()
      return {"boq_version_id": version.id, "created_item_count": 0, "items": []}

    rows = parse_schedule_extraction_response(result.parsed_output)

    created_items: list[BOQItem] = []

    for row in rows:
      normalized_name, category, _matched = await self.normalize_material(
        organization_id, row["description"],
      )
      default_rate = await self.get_material_default_rate(
        organization_id, row["description"],
      )

      drawing_element = DrawingElement(
        id=uuid4(),
        drawing_id=drawing.id,
        organization_id=organization_id,
        ifc_global_id=None,
        ifc_type="PDF_SCHEDULE_ROW",
        name=row["description"],
        raw_material_text=row["description"],
        unit=row["unit"],
        quantity=row["quantity"],
        properties={
          "source": "pdf_ai_extraction",
          "confidence": row.get("confidence"),
          "category": row.get("category"),
        },
      )
      await self.elements.bulk_create([drawing_element])

      created_items.append(
        BOQItem(
          id=uuid4(),
          organization_id=organization_id,
          boq_version_id=version.id,
          drawing_element_id=drawing_element.id,
          material_name=normalized_name,
          category=category or row.get("category"),
          unit=row["unit"],
          quantity=row["quantity"],
          unit_rate=default_rate,
          rate_source=BOQItemRateSource.LIBRARY if default_rate is not None else None,
          item_type=BOQItemType.CUSTOM,
          created_by_user_id=user_id,
        )
      )

    if created_items:
      await self.boq_items.bulk_create(created_items)
    await self.session.commit()
    await self.audit.log(
      organization_id,
      user_id,
      AuditEntityType.DRAWING,
      drawing.id,
      AuditAction.CREATE,
      f'AI-suggested {len(created_items)} draft BOQ item(s) from "{drawing.original_filename}"',
    )

    return {
      "boq_version_id": version.id,
      "created_item_count": len(created_items),
      "items": created_items,
    }

  async def list_boq_items(
    self,
    organization_id: UUID,
    boq_version_id: UUID,
  ) -> list[BOQItem]:
    version = await self.boq_versions.get_by_id_and_org(
      boq_version_id, organization_id
    )
    if version is None:
      raise TraceException(
        "BOQ version not found.",
        status_code=404,
        code="BOQ_VERSION_NOT_FOUND",
      )
    return await self.boq_items.list_by_version(boq_version_id, organization_id)

  async def update_boq_item(
    self,
    organization_id: UUID,
    item_id: UUID,
    user_id: UUID,
    payload: BOQItemUpdateRequest,
  ) -> BOQItem:
    item = await self.boq_items.get_by_id_and_org_for_update(
      item_id, organization_id
    )
    if item is None:
      raise TraceException(
        "BOQ item not found.",
        status_code=404,
        code="BOQ_ITEM_NOT_FOUND",
      )
    if item.status == BOQItemStatus.APPROVED:
      raise TraceException(
        "Approved BOQ items cannot be edited.",
        status_code=409,
        code="BOQ_ITEM_APPROVED",
      )
    if item.version != payload.version:
      raise TraceException(
        "This item was modified by someone else. Reload and try again.",
        status_code=409,
        code="CONCURRENT_MODIFICATION",
      )

    if payload.material_name is not None:
      item.material_name = payload.material_name
    if payload.category is not None:
      item.category = payload.category
    if payload.unit is not None:
      item.unit = payload.unit
    if payload.quantity is not None:
      item.quantity = payload.quantity
    if payload.unit_rate is not None:
      item.unit_rate = payload.unit_rate
      item.rate_source = BOQItemRateSource.MANUAL

      if payload.save_as_library_default and item.drawing_element_id is not None:
        drawing_element = await self.session.get(DrawingElement, item.drawing_element_id)
        if drawing_element is not None and drawing_element.raw_material_text:
          raw_key = drawing_element.raw_material_text.strip().lower()
          existing_entry = await self.material_library.get_by_raw_text(organization_id, raw_key)
          if existing_entry is None:
            await self.material_library.create(
              MaterialLibrary(
                id=uuid4(),
                organization_id=organization_id,
                raw_text=raw_key,
                normalized_name=item.material_name,
                category=item.category,
                default_unit=item.unit,
                default_rate=payload.unit_rate,
              )
            )
          else:
            existing_entry.default_rate = payload.unit_rate
            await self.material_library.update(existing_entry)
    item.version += 1

    await self.boq_items.update(item)
    await self.session.commit()
    await self.audit.log(
      organization_id,
      user_id,
      AuditEntityType.BOQ_ITEM,
      item.id,
      AuditAction.UPDATE,
      f'Updated BOQ item "{item.material_name}"',
    )

    return item

  async def approve_boq_item(
    self,
    organization_id: UUID,
    item_id: UUID,
    user_id: UUID,
  ) -> BOQItem:
    item = await self.boq_items.get_by_id_and_org_for_update(
      item_id, organization_id
    )
    if item is None:
      raise TraceException(
        "BOQ item not found.",
        status_code=404,
        code="BOQ_ITEM_NOT_FOUND",
      )

    if item.status == BOQItemStatus.APPROVED:
      raise TraceException(
        "BOQ item is already approved.",
        status_code=409,
        code="BOQ_ITEM_ALREADY_APPROVED",
      )
      
    if item.unit_rate is None:
      raise TraceException(
        "Cannot approve an item with no rate. Set a rate first.",
        status_code=422,
        code="BOQ_ITEM_UNPRICED",
      )

    item.status = BOQItemStatus.APPROVED
    item.approved_by_user_id = user_id
    item.approved_at = datetime.now(timezone.utc)
    item.version += 1
    
    await self.boq_items.update(item)
    await self.session.commit()

    await self.audit.log(
      organization_id,
      user_id,
      AuditEntityType.BOQ_ITEM,
      item.id,
      AuditAction.APPROVE,
      f'Approved BOQ item "{item.material_name}"',
    )
    return item

  async def create_material_library_entry(
    self,
    organization_id: UUID,
    payload: MaterialLibraryCreateRequest,
  ) -> MaterialLibrary:
    normalized_raw = payload.raw_text.strip().lower()
    existing = await self.material_library.get_by_raw_text(
      organization_id, normalized_raw
    )
    if existing is not None:
      raise TraceException(
        "A material mapping for this text already exists.",
        status_code=409,
        code="MATERIAL_MAPPING_ALREADY_EXISTS",
      )

    entry = MaterialLibrary(
      id=uuid4(),
      organization_id=organization_id,
      raw_text=normalized_raw,
      normalized_name=payload.normalized_name.strip(),
      category=payload.category,
      default_unit=payload.default_unit,
      default_rate=payload.default_rate,
    )
    entry = await self.material_library.create(entry)
    await self.session.commit()

    await self.audit.log(
      organization_id,
      None,
      AuditEntityType.MATERIAL_LIBRARY,
      entry.id,
      AuditAction.CREATE,
      f'Created material library entry "{entry.normalized_name}"',
    )
    return entry

  async def list_material_library(
    self,
    organization_id: UUID,
  ) -> list[MaterialLibrary]:
    return await self.material_library.list_by_org(organization_id)
  
  async def update_material_library_entry(
    self,
    organization_id: UUID,
    entry_id: UUID,
    payload: MaterialLibraryUpdateRequest,
  ) -> MaterialLibrary:
    entry = await self.material_library.get_by_id_and_org(entry_id, organization_id)
    if entry is None:
      raise TraceException(
        "Material mapping not found.",
        status_code=404,
        code="MATERIAL_MAPPING_NOT_FOUND",
      )
    if payload.normalized_name is not None:
      entry.normalized_name = payload.normalized_name.strip()
    if payload.category is not None:
      entry.category = payload.category
    if payload.default_unit is not None:
      entry.default_unit = payload.default_unit
    if payload.default_rate is not None:
      entry.default_rate = payload.default_rate
    entry = await self.material_library.update(entry)
    
    await self.session.commit()
    await self.audit.log(
      organization_id,
      None, 
      AuditEntityType.MATERIAL_LIBRARY,
      entry.id,
      AuditAction.UPDATE,
      f'Updated material library entry "{entry.normalized_name}"',
    )
    return entry

  async def get_material_default_rate(
    self,
    organization_id: UUID,
    raw_text: str,
  ) -> Decimal | None:
    normalized_input = raw_text.strip().lower()
    entry = await self.material_library.get_by_raw_text(organization_id, normalized_input)
    return entry.default_rate if entry is not None else None

  async def create_labour_rate(
    self,
    organization_id: UUID,
    payload: LabourRateCreateRequest,
  ) -> LabourRate:
    existing = await self.labour_rates.get_by_trade(organization_id, payload.trade.strip())
    if existing is not None:
      raise TraceException(
        "A labour rate for this trade already exists.",
        status_code=409,
        code="LABOUR_RATE_ALREADY_EXISTS",
      )
    rate = LabourRate(
      id=uuid4(),
      organization_id=organization_id,
      trade=payload.trade.strip(),
      unit=payload.unit.strip(),
      rate=payload.rate,
    )
    rate = await self.labour_rates.create(rate)
    await self.session.commit()
    return rate

  async def update_labour_rate(
    self,
    organization_id: UUID,
    rate_id: UUID,
    payload: LabourRateUpdateRequest,
  ) -> LabourRate:
    rate = await self.labour_rates.get_by_id_and_org(rate_id, organization_id)
    if rate is None:
      raise TraceException(
        "Labour rate not found.",
        status_code=404,
        code="LABOUR_RATE_NOT_FOUND",
      )
    if payload.trade is not None:
      rate.trade = payload.trade.strip()
    if payload.unit is not None:
      rate.unit = payload.unit.strip()
    if payload.rate is not None:
      rate.rate = payload.rate
    rate = await self.labour_rates.update(rate)
    await self.session.commit()
    return rate

  async def list_labour_rates(self, organization_id: UUID) -> list[LabourRate]:
    return await self.labour_rates.list_by_org(organization_id)

  async def add_custom_boq_item(
    self,
    organization_id: UUID,
    boq_version_id: UUID,
    user_id: UUID,
    payload: BOQCustomItemCreateRequest,
  ) -> BOQItem:
    version = await self.boq_versions.get_by_id_and_org(boq_version_id, organization_id)
    if version is None:
      raise TraceException(
        "BOQ version not found.",
        status_code=404,
        code="BOQ_VERSION_NOT_FOUND",
      )
    item = BOQItem(
      organization_id=organization_id,
      boq_version_id=boq_version_id,
      material_name=payload.material_name.strip(),
      category=payload.category,
      unit=payload.unit,
      quantity=payload.quantity,
      unit_rate=payload.unit_rate,
      item_type=BOQItemType.CUSTOM,
      created_by_user_id=user_id,
    )
    item = await self.boq_items.create(item)
    await self.session.commit()
    await self.audit.log(
      organization_id,
      user_id,
      AuditEntityType.BOQ_ITEM,
      item.id,
      AuditAction.CREATE,
      f'Added custom BOQ item "{item.material_name}"',
    )
    return item

  async def update_boq_version(
    self,
    organization_id: UUID,
    boq_version_id: UUID,
    payload: BOQVersionUpdateRequest,
  ) -> BOQVersion:
    version = await self.boq_versions.get_by_id_and_org(boq_version_id, organization_id)
    if version is None:
      raise TraceException(
        "BOQ version not found.",
        status_code=404,
        code="BOQ_VERSION_NOT_FOUND",
      )
    if payload.covered_area_sqft is not None:
      version.covered_area_sqft = payload.covered_area_sqft
    if payload.export_meta is not None:
      version.export_meta = {**version.export_meta, **payload.export_meta}
    version = await self.boq_versions.update(version)
    await self.session.commit()
    return version

  async def generate_labour_items(
    self,
    organization_id: UUID,
    boq_version_id: UUID,
  ) -> list[BOQItem]:
    version = await self.boq_versions.get_by_id_and_org(boq_version_id, organization_id)
    if version is None:
     raise TraceException(
      "BOQ version not found.",
      status_code=404,
      code="BOQ_VERSION_NOT_FOUND",
    )
    if not version.covered_area_sqft or version.covered_area_sqft <= 0:
     raise TraceException(
      "Set covered_area_sqft on this BOQ version before generating labour costs.",
      status_code=422,
      code="COVERED_AREA_REQUIRED",
    )

    rates = await self.labour_rates.list_by_org(organization_id)
    if not rates:
     raise TraceException(
       "No labour rates configured for this organization.",
       status_code=422,
       code="NO_LABOUR_RATES",
     )
    AREA_UNITS = {"sft", "sq ft", "sqft", "m2", "sqm", "square feet"}

    area_rates = [
       r for r in rates
       if r.unit.strip().lower() in AREA_UNITS
    ]
    skipped = [
       r for r in rates
       if r.unit.strip().lower() not in AREA_UNITS
    ]
    if not area_rates:
      raise TraceException(
       "No area-based (Sft/m²) labour rates configured.",
       status_code=422,
       code="NO_AREA_LABOUR_RATES",
      )

    existing = await self.boq_items.list_by_version(boq_version_id, organization_id)
    approved_trades = {
      item.material_name
      for item in existing
      if item.item_type == BOQItemType.LABOUR and item.status == BOQItemStatus.APPROVED
    }

    for item in existing:
     if item.item_type == BOQItemType.LABOUR and item.status == BOQItemStatus.DRAFT:
      await self.session.delete(item)
    await self.session.flush()

    new_items = [
     BOQItem(
      organization_id=organization_id,
      boq_version_id=boq_version_id,
      material_name=rate.trade,
      category="Labour",
      unit=rate.unit,
      quantity=version.covered_area_sqft,
      unit_rate=rate.rate,
      item_type=BOQItemType.LABOUR,
    )
     for rate in area_rates
     if rate.trade not in approved_trades
    ]
    if new_items:
     await self.boq_items.bulk_create(new_items)
    await self.session.commit()

    return new_items

  async def get_boq_summary(
    self,
    organization_id: UUID,
    boq_version_id: UUID,
  ) -> dict:
    version = await self.boq_versions.get_by_id_and_org(boq_version_id, organization_id)
    if version is None:
      raise TraceException(
        "BOQ version not found.",
        status_code=404,
        code="BOQ_VERSION_NOT_FOUND",
      )
    items = await self.boq_items.list_by_version(boq_version_id, organization_id)

    def _total(kind: BOQItemType) -> Decimal:
      return sum(
        (
          i.quantity * i.unit_rate
          for i in items
          if i.item_type == kind
          and i.status == BOQItemStatus.APPROVED
          and i.unit_rate is not None
        ),
        Decimal("0"),
      )
    materials_total = _total(BOQItemType.MATERIAL)
    labour_total = _total(BOQItemType.LABOUR)
    custom_total = _total(BOQItemType.CUSTOM)
    grand_total = materials_total + labour_total + custom_total

    cost_per_sqft = (
      grand_total / version.covered_area_sqft
      if version.covered_area_sqft and version.covered_area_sqft > 0
      else None
    )

    return {
      "boq_version_id": version.id,
      "materials_total": materials_total,
      "labour_total": labour_total,
      "custom_total": custom_total,
      "grand_total": grand_total,
      "cost_per_sqft": cost_per_sqft,
      "covered_area_sqft": version.covered_area_sqft,
      "amount_in_words": rupees_in_words(grand_total),
      "unpriced_item_count": sum(1 for i in items if i.unit_rate is None),
      "unapproved_item_count": sum(1 for i in items if i.status == BOQItemStatus.DRAFT),
      "item_count": len(items),
    }

  async def _get_organization_name(self, organization_id: UUID) -> str:
    result = await self.session.execute(
      select(Organization.name).where(Organization.id == organization_id)
    )
    return result.scalar_one_or_none() or "Your Company"
  
  async def get_project_boq_counts(self, organization_id: UUID) -> list[dict]:
    return await self.boq_items.get_latest_item_counts_by_project(organization_id)

  async def export_boq_pdf(
    self,
    organization_id: UUID,
    boq_version_id: UUID,
  ) -> tuple[bytes, str]:
    version = await self.boq_versions.get_by_id_and_org(boq_version_id, organization_id)
    if version is None:
      raise TraceException(
        "BOQ version not found.",
        status_code=404,
        code="BOQ_VERSION_NOT_FOUND",
      )
    items = await self.boq_items.list_by_version(boq_version_id, organization_id)

    if any(i.status == BOQItemStatus.DRAFT for i in items):
      raise TraceException(
        "Cannot export BOQ while draft items still exist. Please approve or remove them first.",
        status_code=409,
        code="BOQ_HAS_DRAFT_ITEMS",
      )

    organization_name = await self._get_organization_name(organization_id)
    safe_label = version.label.replace(' ', '_').encode('ascii', 'ignore').decode('ascii')
    pdf_bytes = build_boq_pdf(version, items, organization_name)
    return pdf_bytes, f"BOQ-{safe_label}.pdf"

  async def export_boq_xlsx(
    self,
    organization_id: UUID,
    boq_version_id: UUID,
  ) -> tuple[bytes, str]:
    version = await self.boq_versions.get_by_id_and_org(boq_version_id, organization_id)
    if version is None:
      raise TraceException(
        "BOQ version not found.",
        status_code=404,
        code="BOQ_VERSION_NOT_FOUND",
      )
    items = await self.boq_items.list_by_version(boq_version_id, organization_id)

    if any(i.status == BOQItemStatus.DRAFT for i in items):
      raise TraceException(
        "Cannot export BOQ while draft items still exist. Please approve or remove them first.",
        status_code=409,
        code="BOQ_HAS_DRAFT_ITEMS",
      )

    organization_name = await self._get_organization_name(organization_id)
    safe_label = version.label.replace(' ', '_').encode('ascii', 'ignore').decode('ascii')
    xlsx_bytes = build_boq_xlsx(version, items, organization_name)
    return xlsx_bytes, f"BOQ-{safe_label}.xlsx"

  async def normalize_material(
    self,
    organization_id: UUID,
    raw_text: str,
  ) -> tuple[str, str | None, bool]:
    normalized_input = " ".join(raw_text.strip().lower().split())
    input_hash = hashlib.sha256(
      normalized_input.encode("utf-8")
    ).hexdigest()

    cached = await self.material_cache.get_by_hash(input_hash, organization_id)
    if cached is not None:
      return cached.normalized_name, cached.category, True

    dictionary_entry = await self.material_library.get_by_raw_text(
      organization_id, normalized_input
    )
    if dictionary_entry is not None:
      await self.material_cache.create(
        MaterialNormalizationCache(
          id=uuid4(),
          organization_id=organization_id,
          input_hash=input_hash,
          normalized_name=dictionary_entry.normalized_name,
          category=dictionary_entry.category,
          source="dictionary",
        )
      )
      await self.session.commit()
      return dictionary_entry.normalized_name, dictionary_entry.category, True

    return raw_text.strip(), None, False

  async def store_ai_normalization(
    self,
    organization_id: UUID,
    raw_text: str,
    normalized_name: str,
    category: str | None,
  ) -> None:
    normalized_input = " ".join(raw_text.strip().lower().split())
    input_hash = hashlib.sha256(
      normalized_input.encode("utf-8")
    ).hexdigest()

    if await self.material_cache.get_by_hash(input_hash) is not None:
      return

    await self.material_cache.create(
      MaterialNormalizationCache(
        id=uuid4(),
        input_hash=input_hash,
        normalized_name=normalized_name,
        organization_id=organization_id,
        category=category,
        source="ai",
      )
    )
    await self.session.commit()
    
  async def delete_drawing(
    self,
    organization_id: UUID,
    drawing_id: UUID,
    user_id: UUID | None = None,
  ) -> None:
    drawing = await self.get_drawing(organization_id, drawing_id)
    storage_key = drawing.storage_key

    await self.session.delete(drawing)
    await self.session.commit()

    try:
     await asyncio.to_thread(delete_object, storage_key)
    except Exception:
     pass
   
    if user_id is not None:
     await self.audit.log(
      organization_id,
      user_id,
      AuditEntityType.DRAWING,
      drawing_id,
      AuditAction.DELETE,
      f'Deleted drawing "{drawing.original_filename}"',
    )
  
  async def create_revision(
    self,
    organization_id: UUID,
    project_id: UUID,
    previous_drawing_id: UUID,
    user_id: UUID,
    file: UploadFile,
    revision_label: str | None,
    idempotency_key: str | None,
  ) -> Drawing:
    previous = await self.get_drawing(organization_id, previous_drawing_id)
    if previous.project_id != project_id:
      raise TraceException(
        "This drawing does not belong to this project.", status_code=404, code="DRAWING_NOT_FOUND",
      )
    if not previous.is_current_revision:
      raise TraceException(
        "This drawing has already been superseded by a newer revision. Revise the current revision instead.",
        status_code=409, code="DRAWING_NOT_CURRENT_REVISION",
      )

    new_drawing = await self.upload_drawing(organization_id, project_id, user_id, file, idempotency_key)

    new_drawing.revision_group_id = previous.revision_group_id
    new_drawing.revision_label = (revision_label or "").strip() or None
    previous.is_current_revision = False
    previous.superseded_at = datetime.now(timezone.utc)
    await self.session.commit()

    await self.audit.log(
      organization_id, user_id, AuditEntityType.DRAWING, new_drawing.id, AuditAction.CREATE,
      f'Uploaded a new revision of "{previous.original_filename}"'
      + (f" ({revision_label})" if revision_label else "") + ", superseding the previous revision.",
    )

    return new_drawing

  async def list_revisions(self, organization_id: UUID, drawing_id: UUID) -> list[Drawing]:
    drawing = await self.get_drawing(organization_id, drawing_id)
    return await self.drawings.list_by_revision_group(organization_id, drawing.revision_group_id)
  
  async def list_boq_item_source_elements(
    self, organization_id: UUID, boq_item_id: UUID,
  ) -> list[DrawingElement]:
    result = await self.session.execute(
      select(DrawingElement)
      .join(BOQItemSourceElement, BOQItemSourceElement.drawing_element_id == DrawingElement.id)
      .where(
        BOQItemSourceElement.organization_id == organization_id,
        BOQItemSourceElement.boq_item_id == boq_item_id,
      )
      .order_by(DrawingElement.ifc_global_id.asc())
    )
    return list(result.scalars().unique())

  async def run_model_readiness_audit(
    self,
    organization_id: UUID,
    drawing_id: UUID,
  ) -> ModelAuditResult:
    drawing = await self.get_drawing(
      organization_id,
      drawing_id,
    )

    elements = await self.elements.list_by_drawing(
      drawing_id,
      organization_id,
    )

    issues: list[dict] = []
    missing_material = 0
    zero_quantity = 0
    unclassified_proxy = 0
    missing_qto = 0
    no_storey = 0

    for element in elements:
      properties = element.properties or {}
      element_label = element.ifc_global_id or element.id

      if (
        not element.raw_material_text
        or element.raw_material_text.strip() == ""
      ):
        missing_material += 1
        issues.append({
          "code": "MISSING_MATERIAL",
          "severity": "warning",
          "message": (
            f"Element {element_label} has no material text"
          ),
          "element_ids": [str(element.id)],
        })

      if element.quantity is None or element.quantity <= 0:
        zero_quantity += 1
        issues.append({
          "code": "ZERO_QUANTITY",
          "severity": "warning",
          "message": (
            f"Element {element_label} has zero/missing quantity"
          ),
          "element_ids": [str(element.id)],
        })

      if properties.get("is_generic_fallback") is True:
        unclassified_proxy += 1
        issues.append({
          "code": "UNCLASSIFIED_PROXY",
          "severity": "info",
          "message": (
            f"Element {element_label} used generic type name as material"
          ),
          "element_ids": [str(element.id)],
        })

      has_qto = (
        any(key.startswith("Qto_") for key in properties.keys())
        if isinstance(properties, dict)
        else False
      )

      if not has_qto and element.quantity == 0:
        missing_qto += 1
        issues.append({
          "code": "MISSING_QTO",
          "severity": "warning",
          "message": (
            f"Element {element_label} has no Qto quantities"
          ),
          "element_ids": [str(element.id)],
        })

      properties_text = str(properties).lower()

      if (
        "storey" not in properties_text
        and "ifcbuildingstorey" not in properties_text
      ):
        no_storey += 1

    score = Decimal("100.00")
    score -= Decimal(missing_material) * Decimal("3")
    score -= Decimal(zero_quantity) * Decimal("4")
    score -= Decimal(unclassified_proxy) * Decimal("1.5")
    score -= Decimal(missing_qto) * Decimal("2")
    score = max(score, Decimal("0"))

    audit = ModelAuditResult(
      id=uuid4(),
      organization_id=organization_id,
      drawing_id=drawing_id,
      overall_score=score,
      issues=issues,
      element_count=len(elements),
      missing_material_count=missing_material,
      zero_quantity_count=zero_quantity,
      unclassified_proxy_count=unclassified_proxy,
      extra_stats={
        "missing_qto_count": missing_qto,
        "no_storey_hint_count": no_storey,
      },
    )

    audit = await self.model_audits.create(audit)
    drawing.latest_audit_id = audit.id
    await self.drawings.update(drawing)

    await self.session.flush()
    return audit

  async def get_active_rule_set(
    self,
    organization_id: UUID,
    preferred_code: str | None = None,
  ) -> MeasurementRuleSet:
    code = preferred_code or "PUNJAB_CSR"

    rule_set = await self.rule_sets.get_by_code_and_org(
      code,
      organization_id,
    )
    if rule_set is not None:
      return rule_set
    rule_set = await self.rule_sets.get_system_default(code)

    if rule_set is not None:
      return rule_set
    rule_set = await self.rule_sets.get_system_default(
      "GENERIC_METRIC",
    )

    if rule_set is not None:
      return rule_set
    raise TraceException(
      "No active measurement rule set found. "
      "Seed PUNJAB_CSR or GENERIC_METRIC.",
      status_code=500,
      code="NO_RULE_SET",
    )

  async def expand_with_assemblies(
    self,
    organization_id: UUID,
    boq_version_id: UUID,
    aggregated_groups: list[AggregatedGroup],
    base_items_by_group_key: dict[tuple, BOQItem],
    rule_set: MeasurementRuleSet,
    actor_user_id: UUID | None,
  ) -> list[BOQItem]:
    created: list[BOQItem] = []

    for group in aggregated_groups:
      sample_properties = {}

      matching_recipes = await self.recipes.get_matching_recipes(
        organization_id,
        group.ifc_type,
        sample_properties,
      )
      if not matching_recipes:
        continue

      parent_item = base_items_by_group_key.get(
        (
          group.ifc_type,
          (group.raw_material_text or "").strip().lower(),
          group.unit,
        )
      )
      if parent_item is None:
        continue
      for recipe in matching_recipes:
        components_result = await self.session.execute(
          select(AssemblyRecipeComponent)
          .where(
            AssemblyRecipeComponent.recipe_id == recipe.id
          )
          .order_by(
            AssemblyRecipeComponent.sequence.asc()
          )
        )
        components = list(components_result.scalars().all())
        for component in components:
          parent_quantity = parent_item.quantity or Decimal("0")

          quantity = (
            parent_quantity
            * component.quantity_factor
            * component.waste_factor
          )
          if quantity <= 0:
            continue

          formula = (
            f"{parent_item.quantity} × "
            f"{component.quantity_factor} × "
            f"{component.waste_factor} "
            f"(recipe={recipe.code}, "
            f"component={component.description_template})"
          )

          item = BOQItem(
            id=uuid4(),
            organization_id=organization_id,
            boq_version_id=boq_version_id,
            material_name=component.description_template.replace(
              "{material}",
              parent_item.material_name,
            ),
            category=component.category or parent_item.category,
            unit=component.unit,
            quantity=quantity.quantize(Decimal("0.0001")),
            unit_rate=None,
            rate_source=None,
            item_type=component.item_type,
            status=BOQItemStatus.DRAFT,
            created_by_user_id=actor_user_id,
            work_item_code=component.work_item_code,
            description=component.description_template,
            calculation_formula=formula,
            confidence=Decimal("0.80"),
            rule_set_id=rule_set.id,
            recipe_id=recipe.id,
            gross_quantity=quantity,
            net_quantity=quantity,
            waste_factor_applied=component.waste_factor,
            source_element_count=len(group.element_ids),
          )

          self.session.add(item)
          await self.session.flush()

          for element_id, contribution in group.element_quantities.items():
            self.session.add(
              BOQItemSourceElement(
                id=uuid4(),
                organization_id=organization_id,
                boq_item_id=item.id,
                drawing_element_id=element_id,
                quantity_contributed=(
                  contribution
                  * component.quantity_factor
                  * component.waste_factor
                ).quantize(Decimal("0.001")),
                formula_snippet=formula,
                contribution_type="recipe_component",
              )
            )

          created.append(item)

    await self.session.flush()
    return created

  async def generate_boq_from_elements(
    self,
    organization_id: UUID,
    drawing: Drawing,
    elements: list[DrawingElement],
    boq_version: BOQVersion,
    actor_user_id: UUID | None = None,
    preferred_rule_code: str | None = None,
  ) -> dict:
    audit = await self.run_model_readiness_audit(
      organization_id,
      drawing.id,
    )

    rule_set = await self.get_active_rule_set(
      organization_id,
      preferred_rule_code,
    )

    mappings = await self.element_mappings.list_by_rule_set(
      rule_set.id,
    )

    mapping_by_ifc = {
      mapping.ifc_type: mapping
      for mapping in mappings
    }

    groups = aggregate_drawing_elements(elements)

    base_items: list[BOQItem] = []
    base_items_by_key: dict[tuple, BOQItem] = {}
    generation_meta = {
      "rule_set_id": str(rule_set.id),
      "rule_set_code": rule_set.code,
      "audit_score": float(audit.overall_score),
      "audit_id": str(audit.id),
      "warnings": [
        issue
        for issue in audit.issues
        if issue.get("severity") in ("warning", "error")
      ],
    }
    waste_factors = rule_set.waste_factors or {}
    net_preference = (
      rule_set.net_vs_gross_preference or "net"
    ).lower()

    for group in groups:
      mapping = mapping_by_ifc.get(group.ifc_type)

      unit = (
        mapping.unit_override
        if mapping and mapping.unit_override
        else group.unit
      ) or "unit"

      confidence = (
        mapping.confidence_base
        if mapping
        else Decimal("0.70")
      )

      work_item_code = (
        mapping.work_item_code
        if mapping
        else None
      )

      category = (
        mapping.default_category
        if mapping
        else None
      )

      waste_key = (
        group.raw_material_text
        or group.ifc_type
        or ""
      ).lower()

      waste = Decimal(
        str(
          waste_factors.get(
            waste_key,
            waste_factors.get("default", 1.0),
          )
        )
      )
      gross = group.total_quantity
      net = gross
      if net_preference == "net":
        final_quantity = net * waste
      else:
        final_quantity = gross * waste

      formula = (
        f"{gross} (gross) × "
        f"{waste} (waste) → "
        f"{final_quantity} [{rule_set.code}]"
      )
      normalized_name, normalized_category, _ = (
        await self.normalize_material(
          organization_id,
          group.raw_material_text or group.ifc_type,
        )
      )

      if category is None:
        category = normalized_category
      default_rate = await self.get_material_default_rate(
        organization_id,
        group.raw_material_text or group.ifc_type,
      )

      item = BOQItem(
        id=uuid4(),
        organization_id=organization_id,
        boq_version_id=boq_version.id,
        material_name=normalized_name,
        category=category,
        unit=unit,
        quantity=final_quantity.quantize(Decimal("0.0001")),
        unit_rate=default_rate,
        rate_source=(
          BOQItemRateSource.LIBRARY
          if default_rate is not None
          else None
        ),
        item_type=BOQItemType.MATERIAL,
        status=BOQItemStatus.DRAFT,
        created_by_user_id=actor_user_id,
        work_item_code=work_item_code,
        description=normalized_name,
        calculation_formula=formula,
        confidence=confidence,
        rule_set_id=rule_set.id,
        recipe_id=None,
        gross_quantity=gross,
        net_quantity=net,
        waste_factor_applied=waste,
        source_element_count=len(group.element_ids),
      )

      self.session.add(item)
      await self.session.flush()

      for element_id, contribution in group.element_quantities.items():
        self.session.add(
          BOQItemSourceElement(
            id=uuid4(),
            organization_id=organization_id,
            boq_item_id=item.id,
            drawing_element_id=element_id,
            quantity_contributed=contribution,
            formula_snippet=formula,
            contribution_type="base",
          )
        )

      key = (
        group.ifc_type,
        (group.raw_material_text or "").strip().lower(),
        group.unit,
      )

      base_items_by_key[key] = item
      base_items.append(item)

    recipe_items = await self.expand_with_assemblies(
      organization_id=organization_id,
      boq_version_id=boq_version.id,
      aggregated_groups=groups,
      base_items_by_group_key=base_items_by_key,
      rule_set=rule_set,
      actor_user_id=actor_user_id,
    )

    boq_version.rule_set_id = rule_set.id
    boq_version.audit_score = audit.overall_score
    boq_version.generation_meta = generation_meta

    await self.boq_versions.update(boq_version)
    await self.session.flush()

    return {
      "elements_used": len(elements),
      "base_items_created": len(base_items),
      "recipe_items_created": len(recipe_items),
      "audit_score": float(audit.overall_score),
      "rule_set_code": rule_set.code,
    }