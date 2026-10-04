from __future__ import annotations
import asyncio
import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
from app.core.database import WorkerSessionLocal, dispose_worker_engine
from uuid import uuid4
from app.modules.drawings_boq.ifc_reader import ReadElement, read_ifc
from app.modules.drawings_boq.ifc_types import NO_LEGACY_BOQ_ROLES, READER_VERSION
from app.modules.drawings_boq.models import BOQItem, BOQVersion, BuildingLevel, Drawing, DrawingElement, DrawingStatus, BOQItemRateSource, BOQItemSourceElement
from app.modules.drawings_boq.repository import BOQItemRepository, BOQVersionRepository, DrawingElementRepository, DrawingRepository
from app.shared.storage import download_to_path
from app.modules.drawings_boq.service import DrawingBOQService
from app.workers.celery_app import celery_app
from app.modules.notifications.models import NotificationType
from app.modules.notifications.service import NotificationService
from app.modules.ai_requests.models import AIEntityType, AIRequestPurpose
from app.modules.ai_requests.service import AIOrchestratorService
from sqlalchemy import select
from app.core.config import settings
from app.modules.drawings_boq.calc_service import CalculationService, engine_v2_enabled
from app.modules.drawings_boq.spatial_repository import persist_spatial

MAX_AI_NORMALIZATIONS_PER_PARSE = 50

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

def _build_drawing_element(drawing: Drawing, item: ReadElement, level_ids: dict) -> DrawingElement:
  return DrawingElement(
    drawing_id=drawing.id,
    organization_id=drawing.organization_id,
    ifc_global_id=item.global_id,
    ifc_type=item.ifc_type,
    name=item.name[:500] if item.name else None,
    raw_material_text=item.raw_material_text,
    unit=item.unit,
    quantity=item.quantity,
    properties=item.properties,
    discipline=item.discipline,
    structural_role=item.structural_role,
    classification_source=item.classification_source,
    classification_confidence=item.classification_confidence,
    quantity_source=item.quantity_source,
    level_id=level_ids.get(item.level_global_id),
    length_mm=item.length_mm,
    width_mm=item.width_mm,
    height_mm=item.height_mm,
    thickness_mm=item.thickness_mm,
    elevation_base_mm=item.elevation_base_mm,
    elevation_top_mm=item.elevation_top_mm,
    area_mm2=item.area_mm2,
    volume_mm3=item.volume_mm3,
    bbox_min_x_mm=item.bbox_min_mm[0] if item.bbox_min_mm else None,
    bbox_min_y_mm=item.bbox_min_mm[1] if item.bbox_min_mm else None,
    bbox_min_z_mm=item.bbox_min_mm[2] if item.bbox_min_mm else None,
    bbox_max_x_mm=item.bbox_max_mm[0] if item.bbox_max_mm else None,
    bbox_max_y_mm=item.bbox_max_mm[1] if item.bbox_max_mm else None,
    bbox_max_z_mm=item.bbox_max_mm[2] if item.bbox_max_mm else None,
    geometry_kind=item.geometry_kind,
    profile=item.profile,
    placement=item.placement,
    normalization_status=item.status,
    normalization_issues=item.issues,
  )

async def _parse_drawing(drawing_id: UUID) -> None:
  organization_id: UUID | None = None
  storage_key: str | None = None

  async with WorkerSessionLocal() as session:
    drawings = DrawingRepository(session)

    result = await session.execute(
      select(Drawing)
      .where(
        Drawing.id == drawing_id,
        Drawing.status.in_([DrawingStatus.UPLOADED, DrawingStatus.FAILED]),
      )
      .with_for_update(skip_locked=True)
    )
    drawing = result.scalar_one_or_none()
    if drawing is None:
      return

    organization_id = drawing.organization_id
    storage_key = drawing.storage_key

    drawing.status = DrawingStatus.PROCESSING
    drawing.error_message = None
    await drawings.update(drawing)
    await session.commit()

  with tempfile.TemporaryDirectory() as tmp_dir:
    local_path = os.path.join(tmp_dir, "drawing.ifc")
    try:
      download_to_path(storage_key, local_path)
      read_result = read_ifc(local_path)
    except Exception as exc:
      async with WorkerSessionLocal() as session:
        drawings = DrawingRepository(session)
        failed = await drawings.get_by_id_and_org(drawing_id, organization_id)
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

    current_drawing = await drawings.get_by_id_and_org(drawing_id, organization_id)
    if current_drawing is None:
      return
    if current_drawing.status == DrawingStatus.PARSED:
      return
    drawing_org_id = current_drawing.organization_id
    drawing_project_id = current_drawing.project_id
    drawing_filename = current_drawing.original_filename
    uploader_id = current_drawing.uploaded_by_user_id
    parsed_ok = False
    try:
      if not read_result.elements:
        raise ValueError("No supported building elements were found in this IFC file.")
      level_ids: dict[str, UUID] = {}
      level_rows: list[BuildingLevel] = []
      for level in read_result.levels:
        row = BuildingLevel(
          id=uuid4(),
          organization_id=current_drawing.organization_id,
          drawing_id=current_drawing.id,
          name=level.name[:200],
          elevation_mm=level.elevation_mm,
          ifc_storey_id=level.global_id,
          sequence=level.sequence,
        )
        level_ids[level.global_id] = row.id
        level_rows.append(row)
      if level_rows:
        session.add_all(level_rows)
        await session.flush()

      drawing_elements = [
        _build_drawing_element(current_drawing, item, level_ids)
        for item in read_result.elements
      ]

      if drawing_elements:
        await elements_repo.bulk_create(drawing_elements)
      await persist_spatial(session, current_drawing, read_result, drawing_elements, level_ids)

      audit = await service.run_model_readiness_audit(
        current_drawing.organization_id,
        current_drawing.id,
        model_issues=read_result.model_issues,
      )

      boq_version = await boq_versions_repo.create(
        BOQVersion(
          organization_id=current_drawing.organization_id,
          project_id=current_drawing.project_id,
          drawing_id=current_drawing.id,
          label=f"{current_drawing.original_filename} — auto-generated",
        )
      )

      boq_items: list[BOQItem] = []
      skipped_without_quantity = 0
      stored_only = 0
      material_memo: dict[str, tuple] = {}
      ai_calls_left = MAX_AI_NORMALIZATIONS_PER_PARSE
      org_id = current_drawing.organization_id

      async def _resolve_material(raw_text: str, element_row_id: UUID) -> tuple:
        nonlocal ai_calls_left
        memo = material_memo.get(raw_text)
        if memo is not None:
          return memo
        normalized_name, category, matched = await service.normalize_material(org_id, raw_text)
        default_rate = await service.get_material_default_rate(org_id, raw_text)
        rate_source = BOQItemRateSource.LIBRARY if default_rate is not None else None

        if not matched and ai_calls_left > 0:
          ai_calls_left -= 1
          result = await AIOrchestratorService(session).run(
            organization_id=org_id,
            purpose=AIRequestPurpose.MATERIAL_NORMALIZATION,
            entity_type=AIEntityType.DRAWING_ELEMENT,
            entity_id=element_row_id,
            prompt=(
              "Normalize this construction material description extracted from a "
              "BIM/IFC drawing for Pakistan-market construction estimating. Respond "
              'with strict JSON only: {"normalized_name": "...", "category": "...", '
              '"suggested_rate_pkr": <number or null>}. Only set suggested_rate_pkr if '
              "you have reasonable confidence in a current Pakistan-market unit rate; "
              "otherwise use null. Raw text: " + raw_text
            ),
          )
          if result.success and result.parsed_output and result.parsed_output.get("normalized_name"):
            normalized_name = result.parsed_output["normalized_name"]
            category = result.parsed_output.get("category")
            suggested_rate = result.parsed_output.get("suggested_rate_pkr")
            if suggested_rate is not None:
              try:
                default_rate = Decimal(str(suggested_rate))
                rate_source = BOQItemRateSource.AI_SUGGESTED
              except Exception:
                pass
            await service.store_ai_normalization(org_id, raw_text, normalized_name, category)

        resolved = (
          str(normalized_name)[:300],
          str(category)[:150] if category else None,
          default_rate,
          rate_source,
        )
        material_memo[raw_text] = resolved
        return resolved

      grouped: dict[tuple, dict] = {}
      for element, drawing_element in zip(read_result.elements, drawing_elements):
        if element.structural_role in NO_LEGACY_BOQ_ROLES:
          stored_only += 1
          continue
        if element.quantity <= 0 or not element.unit:
          skipped_without_quantity += 1
          continue

        name, category, default_rate, rate_source = await _resolve_material(
          element.raw_material_text, drawing_element.id,
        )

        if element.discipline.startswith("MEP_"):
          key = (element.structural_role, name, element.unit)
          bucket = grouped.get(key)
          if bucket is None:
            bucket = {
              "quantity": Decimal("0"), "category": category, "rate": default_rate,
              "rate_source": rate_source, "generic": element.is_generic_fallback, "elements": [],
            }
            grouped[key] = bucket
          bucket["quantity"] += element.quantity
          bucket["elements"].append((drawing_element.id, element.quantity))
          continue

        boq_items.append(
          BOQItem(
            organization_id=org_id,
            boq_version_id=boq_version.id,
            drawing_element_id=drawing_element.id,
            material_name=name,
            category=category,
            unit=element.unit,
            quantity=element.quantity,
            unit_rate=default_rate,
            rate_source=rate_source,
          )
        )

      aggregated_links: list[BOQItemSourceElement] = []
      for (role, name, unit), bucket in sorted(grouped.items(), key=lambda kv: kv[0]):
        title = role.replace("_", " ").title()
        label = name if bucket["generic"] else f"{title} - {name}"
        item = BOQItem(
          id=uuid4(),
          organization_id=org_id,
          boq_version_id=boq_version.id,
          material_name=label[:300],
          category=bucket["category"],
          unit=unit,
          quantity=bucket["quantity"],
          unit_rate=bucket["rate"],
          rate_source=bucket["rate_source"],
        )
        boq_items.append(item)
        for element_row_id, contribution in bucket["elements"]:
          aggregated_links.append(
            BOQItemSourceElement(
              id=uuid4(),
              organization_id=org_id,
              boq_item_id=item.id,
              drawing_element_id=element_row_id,
              quantity_contributed=contribution,
              formula_snippet=f"sum of {len(bucket['elements'])} {role} elements",
              contribution_type="legacy_group",
            )
          )

      if boq_items:
        await boq_items_repo.bulk_create(boq_items)
      if aggregated_links:
        session.add_all(aggregated_links)
        await session.flush()

      if current_drawing.uploaded_by_user_id is not None:
        await NotificationService(session).notify_user(
          current_drawing.organization_id,
          current_drawing.uploaded_by_user_id,
          NotificationType.DRAWING_PARSED,
          f'"{current_drawing.original_filename}" finished parsing',
          body=(
            f"{len(boq_items)} draft BOQ lines from {len(read_result.elements)} elements; "
            f"model readiness {audit.overall_score}%"
            + (f"; {skipped_without_quantity} element(s) had no usable quantity." if skipped_without_quantity else ".")
          ),
          link_path=f"/app/projects/{current_drawing.project_id}",
          commit=False,
        )

      current_drawing.ingestion_meta = {
        "reader_version": READER_VERSION,
        "ifc_schema": read_result.schema,
        "length_unit_scale": read_result.length_unit_scale,
        "model_issues": read_result.model_issues,
        "stats": read_result.stats,
      }
      current_drawing.status = DrawingStatus.PARSED
      current_drawing.parsed_at = datetime.now(timezone.utc)
      await drawings.update(current_drawing)
      await session.commit()
      parsed_ok = True

    except Exception as exc:
      await session.rollback()
      failed = await drawings.get_by_id_and_org(drawing_id, drawing_org_id)
      if failed is not None:
        failed.error_message = str(exc)[:2000]
        failed.status = DrawingStatus.FAILED
        await drawings.update(failed)
      if uploader_id is not None:
        await NotificationService(session).notify_user(
          drawing_org_id,
          uploader_id,
          NotificationType.DRAWING_FAILED,
          f'"{drawing_filename}" failed to parse',
          body=str(exc)[:500],
          link_path=f"/app/projects/{drawing_project_id}",
          commit=False,
        )
      await session.commit()

    if parsed_ok and engine_v2_enabled(drawing_org_id):
      try:
        await CalculationService(session).request_run(
          drawing_org_id, drawing_project_id, uploader_id, None, None,
          convention_code=settings.engine_default_convention)
      except Exception:
        await session.rollback()