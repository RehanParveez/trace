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
from app.modules.drawings_boq.models import BOQItem, BOQItemStatus, BOQVersion, Drawing, DrawingElement, DrawingFormat, DrawingStatus, MaterialLibrary, MaterialNormalizationCache
from app.modules.drawings_boq.repository import BOQItemRepository, BOQVersionRepository, DrawingElementRepository, DrawingRepository, MaterialLibraryRepository, MaterialNormalizationCacheRepository
from app.modules.drawings_boq.schemas import BOQItemUpdateRequest, MaterialLibraryCreateRequest
from app.modules.projects.repository import ProjectRepository
from app.modules.subscriptions.service import SubscriptionService
from app.shared.idempotency import get_cached_response, store_response
from app.shared.storage import build_storage_key, upload_fileobj
from app.modules.drawings_boq.tasks import parse_drawing_task

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
    self.projects = ProjectRepository(session)
    self.subscriptions = SubscriptionService(session)

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
    )
    entry = await self.material_library.create(entry)
    await self.session.commit()
    return entry

  async def list_material_library(
    self,
    organization_id: UUID,
  ) -> list[MaterialLibrary]:
    return await self.material_library.list_by_org(organization_id)

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