from __future__ import annotations
import asyncio
import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
import ifcopenshell
import ifcopenshell.util.element
from app.core.database import WorkerSessionLocal, dispose_worker_engine
from app.modules.drawings_boq.models import BOQItem, BOQVersion, DrawingElement, DrawingStatus, BOQItemRateSource
from app.modules.drawings_boq.repository import BOQItemRepository, BOQVersionRepository, DrawingElementRepository, DrawingRepository
from app.shared.storage import download_to_path
from app.modules.drawings_boq.service import DrawingBOQService
from app.workers.celery_app import celery_app
from app.modules.notifications.models import NotificationType
from app.modules.notifications.service import NotificationService
from app.modules.ai_requests.models import AIEntityType, AIRequestPurpose
from app.modules.ai_requests.service import AIOrchestratorService

TARGET_IFC_TYPES = [
  "IfcWall",
  "IfcSlab",
  "IfcBeam",
  "IfcColumn",
  "IfcDoor",
  "IfcWindow",
  "IfcRoof",
  "IfcStair",
]

QUANTITY_ATTRS = (
  "NetVolume",
  "GrossVolume",
  "NetArea",
  "GrossArea",
  "Length",
)

@celery_app.task(
  name="app.modules.drawings_boq.tasks.parse_drawing_task",
  time_limit=900,
  soft_time_limit=780,
)

def parse_drawing_task(drawing_id: str) -> str:
  async def _run() -> None:
    try:
      await _parse_drawing(UUID(drawing_id))
    finally:
      await dispose_worker_engine()

  asyncio.run(_run())
  return "parsed"

async def _parse_drawing(drawing_id: UUID) -> None:

  async with WorkerSessionLocal() as session:
    drawings = DrawingRepository(session)
    drawing = await drawings.get_by_id(drawing_id)
    if drawing is None:
      return
    if drawing.status == DrawingStatus.PARSED:  
      return
    drawing.status = DrawingStatus.PROCESSING
    await drawings.update(drawing)
    await session.commit()

  with tempfile.TemporaryDirectory() as tmp_dir:
    local_path = os.path.join(tmp_dir, "drawing.ifc")
    try:
      download_to_path(drawing.storage_key, local_path)
      elements_data = _extract_ifc_elements(local_path)
    except Exception as exc:
      async with WorkerSessionLocal() as session:
        drawings = DrawingRepository(session)
        failed = await drawings.get_by_id(drawing_id)
        if failed is not None:
          failed.status = DrawingStatus.FAILED
          failed.error_message = str(exc)[:2000]
          await drawings.update(failed)
          if failed.uploaded_by_user_id is not None:
            await NotificationService(session).notify_user(
              failed.organization_id,
              failed.uploaded_by_user_id,
              NotificationType.DRAWING_FAILED,
              f'"{failed.original_filename}" failed to parse',
              body=str(exc)[:500],
              link_path=f"/app/projects/{failed.project_id}",
              commit=False,
            )
        await session.commit()
      return  

  async with WorkerSessionLocal() as session:
    drawings = DrawingRepository(session)
    elements_repo = DrawingElementRepository(session)
    boq_versions_repo = BOQVersionRepository(session)
    boq_items_repo = BOQItemRepository(session)
    service = DrawingBOQService(session)

    current_drawing = await drawings.get_by_id(drawing_id)
    if current_drawing is None:
      return
    if current_drawing.status == DrawingStatus.PARSED:
      return

    try:
      drawing_elements = [
        DrawingElement(
          drawing_id=current_drawing.id,
          organization_id=current_drawing.organization_id,
          ifc_global_id=item["global_id"],
          ifc_type=item["ifc_type"],
          name=item["name"],
          raw_material_text=item["material_text"] or item["ifc_type"],
          unit=item["unit"],
          quantity=item["quantity"],
          properties=item["properties"],
        )
        for item in elements_data
      ]

      if drawing_elements:
        await elements_repo.bulk_create(drawing_elements)

      boq_version = await boq_versions_repo.create(
        BOQVersion(
          organization_id=current_drawing.organization_id,
          project_id=current_drawing.project_id,
          drawing_id=current_drawing.id,
          label=f"{current_drawing.original_filename} — auto-generated",
        )
      )

      boq_items: list[BOQItem] = []

      for element, drawing_element in zip(elements_data, drawing_elements):
        raw_text = element["material_text"] or element["ifc_type"]
        normalized_name, category, matched = await service.normalize_material(
          current_drawing.organization_id,
          raw_text,
        )
        default_rate = await service.get_material_default_rate(
          current_drawing.organization_id, raw_text,
        )
        rate_source = BOQItemRateSource.LIBRARY if default_rate is not None else None

        if not matched:
          orchestrator = AIOrchestratorService(session)
          result = await orchestrator.run(
            organization_id=current_drawing.organization_id,
            purpose=AIRequestPurpose.MATERIAL_NORMALIZATION,
            entity_type=AIEntityType.DRAWING_ELEMENT,
            entity_id=drawing_element.id,
            prompt=(
              "Normalize this construction material description extracted from a "
              "BIM/IFC drawing for Pakistan-market construction estimating. Respond "
              'with strict JSON only: {"normalized_name": "...", "category": "...", '
              '"suggested_rate_pkr": <number or null>}. Only set suggested_rate_pkr if '
              "you have reasonable confidence in a current Pakistan-market unit rate; "
              "otherwise use null. Raw text: " + raw_text
            ),
          )
          if (
            result.success
            and result.parsed_output
            and result.parsed_output.get("normalized_name")
          ):
            normalized_name = result.parsed_output["normalized_name"]
            category = result.parsed_output.get("category")
            suggested_rate = result.parsed_output.get("suggested_rate_pkr")
            if suggested_rate is not None:
              try:
                default_rate = Decimal(str(suggested_rate))
                rate_source = BOQItemRateSource.AI_SUGGESTED
              except Exception:
                pass
            await service.store_ai_normalization(
              raw_text,
              normalized_name,
              category,
            )

        boq_items.append(
          BOQItem(
            organization_id=current_drawing.organization_id,
            boq_version_id=boq_version.id,
            drawing_element_id=drawing_element.id,
            material_name=normalized_name,
            category=category,
            unit=element["unit"] or "unit",
            quantity=element["quantity"],
            unit_rate=default_rate,
            rate_source=rate_source,
          )
        )

      if boq_items:
        await boq_items_repo.bulk_create(boq_items)

      if current_drawing.uploaded_by_user_id is not None:
        await NotificationService(session).notify_user(
          current_drawing.organization_id,
          current_drawing.uploaded_by_user_id,
          NotificationType.DRAWING_PARSED,
          f'"{current_drawing.original_filename}" finished parsing',
          body=f"{len(boq_items)} draft BOQ items were generated.",
          link_path=f"/app/projects/{current_drawing.project_id}",
          commit=False,
        )

      current_drawing.status = DrawingStatus.PARSED
      current_drawing.parsed_at = datetime.now(timezone.utc)
      await drawings.update(current_drawing)
      await session.commit()

    except Exception as exc:
      await session.rollback()
      current_drawing.error_message = str(exc)[:2000]
      current_drawing.status = DrawingStatus.FAILED
      await drawings.update(current_drawing)
      if current_drawing.uploaded_by_user_id is not None:
        await NotificationService(session).notify_user(
          current_drawing.organization_id,
          current_drawing.uploaded_by_user_id,
          NotificationType.DRAWING_FAILED,
          f'"{current_drawing.original_filename}" failed to parse',
          body=str(exc)[:500],
          link_path=f"/app/projects/{current_drawing.project_id}",
          commit=False,
        )
      await session.commit()

def _extract_ifc_elements(path: str) -> list[dict]:
  model = ifcopenshell.open(path)
  results: list[dict] = []

  for ifc_type in TARGET_IFC_TYPES:
    for element in model.by_type(ifc_type):
      psets = ifcopenshell.util.element.get_psets(element) or {}
      quantity, unit = _best_quantity(psets)
      results.append(
        {
          "global_id": getattr(element, "GlobalId", None),
          "ifc_type": ifc_type,
          "name": getattr(element, "Name", None),
          "material_text": _material_text(element),
          "unit": unit,
          "quantity": quantity,
          "properties": dict(psets),
        }
      )

  return results

def _best_quantity(psets: dict) -> tuple[Decimal, str | None]:
  for pset_name, pset_values in psets.items():
    if not pset_name.startswith("Qto_"):
      continue
    for attr in QUANTITY_ATTRS:
      if attr in pset_values and pset_values[attr] is not None:
        unit = (
          "m3"
          if "Volume" in attr
          else "m2"
          if "Area" in attr
          else "m"
        )
        return Decimal(str(pset_values[attr])), unit
  return Decimal("0"), None

def _material_text(element) -> str | None:
  try:
    material = ifcopenshell.util.element.get_material(element)
    return (
      getattr(material, "Name", None)
      if material is not None
      else None
    )
  except Exception:
    return None