from __future__ import annotations
import asyncio
import hashlib
from datetime import datetime, timezone
from io import BytesIO
from pathlib import PurePosixPath
from uuid import UUID, uuid4
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import TraceException
from app.modules.drawings_boq.models import BOQItem, BOQItemStatus, BOQItemType, BOQVersion, Drawing, DrawingElement, DrawingFormat, DrawingStatus, LabourRate, MaterialLibrary, MaterialNormalizationCache
from app.modules.drawings_boq.repository import BOQItemRepository, BOQVersionRepository, DrawingElementRepository, DrawingRepository, LabourRateRepository, MaterialLibraryRepository, MaterialNormalizationCacheRepository
from app.modules.drawings_boq.schemas import BOQCustomItemCreateRequest, BOQItemUpdateRequest, BOQVersionUpdateRequest, LabourRateCreateRequest, LabourRateUpdateRequest, MaterialLibraryCreateRequest, MaterialLibraryUpdateRequest
from app.modules.projects.repository import ProjectRepository
from app.modules.subscriptions.service import SubscriptionService
from app.shared.idempotency import get_cached_response, store_response
from app.shared.storage import build_storage_key, upload_fileobj
from sqlalchemy import select
from app.modules.drawings_boq.export import build_boq_pdf, build_boq_xlsx
from app.modules.drawings_boq.words import rupees_in_words
from app.modules.identity.models import Organization
from app.modules.audit.models import AuditAction, AuditEntityType
from app.modules.audit.service import AuditLogService
from decimal import Decimal

SUPPORTED_UPLOAD_FORMATS = {".ifc": DrawingFormat.IFC}

UNSUPPORTED_FORMAT_GUIDANCE = {
  ".rvt": (
    "RVT files can't be parsed directly. Export an IFC file from Revit "
    "(File > Export > IFC) and upload that instead."
  ),
  ".dwg": "DWG support isn't available yet — export to IFC if possible.",
  ".dxf": "DXF support isn't available yet — export to IFC if possible.",
}

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

    drawing_format = SUPPORTED_UPLOAD_FORMATS.get(suffix)
    if drawing_format is None:
      raise TraceException(
        "Unrecognized file type. Upload an .ifc file.",
        status_code=422,
        code="UNSUPPORTED_DRAWING_FORMAT",
      )

    await self.subscriptions.check_quota(organization_id, "drawings")

    contents = await file.read()
    storage_key = build_storage_key(
      organization_id, project_id, file.filename or "drawing.ifc"
    )

    await asyncio.to_thread(
      upload_fileobj, storage_key, BytesIO(contents), file.content_type
    )

    drawing = Drawing(
      id=uuid4(),
      organization_id=organization_id,
      project_id=project_id,
      uploaded_by_user_id=user_id,
      original_filename=file.filename or "drawing.ifc",
      storage_key=storage_key,
      format=drawing_format,
      status=DrawingStatus.UPLOADED,
      file_size_bytes=len(contents),
    )

    drawing = await self.drawings.create(drawing)
    await self.subscriptions.increment_usage(organization_id, "drawings")
    await self.session.commit()

    if idempotency_key:
      await store_response(
        organization_id,
        "drawing_upload",
        idempotency_key,
        {"drawing_id": str(drawing.id)},
      )

    parse_drawing_task.apply_async(
      args=[str(drawing.id)], queue="bim_parsing"
    )

    return drawing

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
    return await self.elements.list_by_drawing(drawing_id)

  async def list_boq_versions(
    self,
    organization_id: UUID,
    project_id: UUID,
  ) -> list[BOQVersion]:
    await self._require_project(organization_id, project_id)
    return await self.boq_versions.list_by_project(organization_id, project_id)

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
    return await self.boq_items.list_by_version(boq_version_id)

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

    item.status = BOQItemStatus.APPROVED
    item.approved_by_user_id = user_id
    item.approved_at = datetime.now(timezone.utc)
    item.version += 1

    await self.boq_items.update(item)
    await self.session.commit()
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

    existing = await self.boq_items.list_by_version(boq_version_id)
    approved_trades = {
      item.material_name for item in existing
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
      for rate in rates
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
    items = await self.boq_items.list_by_version(boq_version_id)

    def _total(kind: BOQItemType) -> Decimal:
      return sum(
        (i.quantity * i.unit_rate for i in items if i.item_type == kind and i.unit_rate is not None),
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
    items = await self.boq_items.list_by_version(boq_version_id)
    organization_name = await self._get_organization_name(organization_id)
    pdf_bytes = build_boq_pdf(version, items, organization_name)
    return pdf_bytes, f"BOQ-{version.label.replace(' ', '_')}.pdf"

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
    items = await self.boq_items.list_by_version(boq_version_id)
    organization_name = await self._get_organization_name(organization_id)
    xlsx_bytes = build_boq_xlsx(version, items, organization_name)
    return xlsx_bytes, f"BOQ-{version.label.replace(' ', '_')}.xlsx"

  async def normalize_material(
    self,
    organization_id: UUID,
    raw_text: str,
  ) -> tuple[str, str | None, bool]:
    normalized_input = " ".join(raw_text.strip().lower().split())
    input_hash = hashlib.sha256(
      normalized_input.encode("utf-8")
    ).hexdigest()

    cached = await self.material_cache.get_by_hash(input_hash)
    if cached is not None:
      return cached.normalized_name, cached.category, True

    dictionary_entry = await self.material_library.get_by_raw_text(
      organization_id, normalized_input
    )
    if dictionary_entry is not None:
      await self.material_cache.create(
        MaterialNormalizationCache(
          id=uuid4(),
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
        category=category,
        source="ai",
      )
    )
    await self.session.commit()