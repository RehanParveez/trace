from __future__ import annotations
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
from unittest.mock import patch
from uuid import uuid4
import pytest
from fastapi import UploadFile
from sqlalchemy import select
from app.core.exceptions import TraceException
from app.modules.drawings_boq.models import BOQItem, BOQItemStatus, BOQItemType, BOQVersion, DrawingFormat, DrawingStatus, LabourRate, MaterialLibrary, MaterialNormalizationCache
from app.modules.drawings_boq.permissions import DRAWINGS_BOQ_PERMISSIONS
from app.modules.drawings_boq.schemas import BOQItemUpdateRequest, LabourRateCreateRequest, MaterialLibraryCreateRequest
from app.modules.drawings_boq.service import DrawingBOQService
from app.modules.identity.models import Permission
from app.modules.subscriptions.models import SubscriptionStatus

def _svc(session) -> DrawingBOQService:
  return DrawingBOQService(session)

def _upload(filename: str, content: bytes, content_type: str = "application/octet-stream") -> UploadFile:
  return UploadFile(
    filename=filename,
    file=BytesIO(content),
    headers={"content-type": content_type},
  )

async def _ensure_drawings_permissions(db_session, role) -> None:
  needed = list(DRAWINGS_BOQ_PERMISSIONS.keys())
  existing_keys = {p.key for p in (role.permissions or [])}
  for key in needed:
    key_str = str(key)
    if key_str in existing_keys:
      continue
    result = await db_session.execute(
      select(Permission).where(Permission.key == key_str)
    )
    perm = result.scalar_one_or_none()
    if perm is None:
      perm = Permission(id=uuid4(), key=key_str, description=key_str)
      db_session.add(perm)
      await db_session.flush()
    role.permissions = list(role.permissions or []) + [perm]
  await db_session.flush()

async def _active_sub(make_subscription, organization, make_plan):
  plan = await make_plan(
    quotas={
      "projects": 50,
      "storage_bytes": 10_737_418_240,
      "drawings": 100,
      "ai_requests": 200,
      "site_photos": 500,
    }
  )
  return await make_subscription(
    organization=organization,
    plan=plan,
    status=SubscriptionStatus.ACTIVE,
  )

@pytest.mark.asyncio
async def test_upload_rejects_unsupported_format(
  db_session,
  organization,
  user,
  project_factory,
  make_subscription,
  make_plan,
):
  await _active_sub(make_subscription, organization, make_plan)
  project = await project_factory()
  svc = _svc(db_session)

  with pytest.raises(TraceException) as exc:
    await svc.upload_drawing(
      organization.id,
      project.id,
      user.id,
      _upload("model.rvt", b"fake"),
      None,
    )
  assert exc.value.status_code == 422
  assert exc.value.code == "UNSUPPORTED_DRAWING_FORMAT"

@pytest.mark.asyncio
async def test_upload_rejects_invalid_ifc_content(
  db_session,
  organization,
  user,
  project_factory,
  make_subscription,
  make_plan,
):
  await _active_sub(make_subscription, organization, make_plan)
  project = await project_factory()
  svc = _svc(db_session)

  with pytest.raises(TraceException) as exc:
    await svc.upload_drawing(
      organization.id,
      project.id,
      user.id,
      _upload("bad.ifc", b"this is not an IFC file"),
      None,
    )
  assert exc.value.code == "INVALID_IFC_CONTENT"

@pytest.mark.asyncio
async def test_upload_pdf_marked_parsed_no_celery(
  db_session,
  organization,
  user,
  project_factory,
  make_subscription,
  make_plan,
):
  await _active_sub(make_subscription, organization, make_plan)
  project = await project_factory()
  svc = _svc(db_session)

  with (
    patch("app.modules.drawings_boq.service.upload_fileobj"),
    patch("app.modules.drawings_boq.tasks.parse_drawing_task") as task_mock,
  ):
    drawing = await svc.upload_drawing(
      organization.id,
      project.id,
      user.id,
      _upload("schedule.pdf", b"%PDF-1.4 content", "application/pdf"),
      None,
    )

  assert drawing.format == DrawingFormat.PDF
  assert drawing.status == DrawingStatus.PARSED
  assert drawing.parsed_at is not None
  task_mock.apply_async.assert_not_called()

@pytest.mark.asyncio
async def test_upload_ifc_enqueues_parse_task(
  db_session,
  organization,
  user,
  project_factory,
  make_subscription,
  make_plan,
):
  await _active_sub(make_subscription, organization, make_plan)
  project = await project_factory()
  svc = _svc(db_session)

  ifc_header = b"ISO-10303-21;\nHEADER;"
  with (
    patch("app.modules.drawings_boq.service.upload_fileobj"),
    patch("app.modules.drawings_boq.tasks.parse_drawing_task") as task_mock,
  ):
    drawing = await svc.upload_drawing(
      organization.id,
      project.id,
      user.id,
      _upload("model.ifc", ifc_header),
      None,
    )

  assert drawing.format == DrawingFormat.IFC
  assert drawing.status == DrawingStatus.UPLOADED
  task_mock.apply_async.assert_called_once()

@pytest.mark.asyncio
async def test_update_rejects_approved_item(
  db_session,
  organization,
  user,
  project_factory,
):
  project = await project_factory()
  version = BOQVersion(
    id=uuid4(),
    organization_id=organization.id,
    project_id=project.id,
    label="V1",
  )
  db_session.add(version)
  item = BOQItem(
    id=uuid4(),
    organization_id=organization.id,
    boq_version_id=version.id,
    material_name="Concrete",
    unit="m3",
    quantity=Decimal("1"),
    unit_rate=Decimal("100"),
    status=BOQItemStatus.APPROVED,
    version=1,
    item_type=BOQItemType.MATERIAL,
  )
  db_session.add(item)
  await db_session.flush()

  svc = _svc(db_session)
  with pytest.raises(TraceException) as exc:
    await svc.update_boq_item(
      organization.id,
      item.id,
      user.id,
      BOQItemUpdateRequest(version=1, material_name="Changed"),
    )
  assert exc.value.code == "BOQ_ITEM_APPROVED"

@pytest.mark.asyncio
async def test_update_optimistic_lock(
  db_session,
  organization,
  user,
  project_factory,
):
  project = await project_factory()
  version = BOQVersion(
    id=uuid4(),
    organization_id=organization.id,
    project_id=project.id,
    label="V1",
  )
  db_session.add(version)
  item = BOQItem(
    id=uuid4(),
    organization_id=organization.id,
    boq_version_id=version.id,
    material_name="Steel",
    unit="kg",
    quantity=Decimal("10"),
    status=BOQItemStatus.DRAFT,
    version=3,
    item_type=BOQItemType.MATERIAL,
  )
  db_session.add(item)
  await db_session.flush()

  svc = _svc(db_session)
  with pytest.raises(TraceException) as exc:
    await svc.update_boq_item(
      organization.id,
      item.id,
      user.id,
      BOQItemUpdateRequest(version=1, quantity=Decimal("20")),
    )
  assert exc.value.code == "CONCURRENT_MODIFICATION"

@pytest.mark.asyncio
async def test_approve_rejects_unpriced(
  db_session,
  organization,
  user,
  project_factory,
):
  project = await project_factory()
  version = BOQVersion(
    id=uuid4(),
    organization_id=organization.id,
    project_id=project.id,
    label="V1",
  )
  db_session.add(version)
  item = BOQItem(
    id=uuid4(),
    organization_id=organization.id,
    boq_version_id=version.id,
    material_name="Unpriced",
    unit="m3",
    quantity=Decimal("1"),
    unit_rate=None,
    status=BOQItemStatus.DRAFT,
    version=1,
    item_type=BOQItemType.MATERIAL,
  )
  db_session.add(item)
  await db_session.flush()

  svc = _svc(db_session)
  with pytest.raises(TraceException) as exc:
    await svc.approve_boq_item(organization.id, item.id, user.id)
  assert exc.value.code == "BOQ_ITEM_UNPRICED"

@pytest.mark.asyncio
async def test_approve_success(
  db_session,
  organization,
  user,
  project_factory,
):
  project = await project_factory()
  version = BOQVersion(
    id=uuid4(),
    organization_id=organization.id,
    project_id=project.id,
    label="V1",
  )
  db_session.add(version)
  item = BOQItem(
    id=uuid4(),
    organization_id=organization.id,
    boq_version_id=version.id,
    material_name="Ready",
    unit="m3",
    quantity=Decimal("2"),
    unit_rate=Decimal("18000"),
    status=BOQItemStatus.DRAFT,
    version=1,
    item_type=BOQItemType.MATERIAL,
  )
  db_session.add(item)
  await db_session.flush()

  svc = _svc(db_session)
  approved = await svc.approve_boq_item(organization.id, item.id, user.id)
  assert approved.status == BOQItemStatus.APPROVED
  assert approved.approved_by_user_id == user.id
  assert approved.approved_at is not None
  assert approved.version == 2

@pytest.mark.asyncio
async def test_generate_labour_requires_covered_area(
  db_session,
  organization,
  project_factory,
):
  project = await project_factory()
  version = BOQVersion(
    id=uuid4(),
    organization_id=organization.id,
    project_id=project.id,
    label="V1",
    covered_area_sqft=None,
  )
  db_session.add(version)
  await db_session.flush()

  svc = _svc(db_session)
  with pytest.raises(TraceException) as exc:
    await svc.generate_labour_items(organization.id, version.id)
  assert exc.value.code == "COVERED_AREA_REQUIRED"

@pytest.mark.asyncio
async def test_generate_labour_skips_approved_and_replaces_drafts(
  db_session,
  organization,
  project_factory,
):
  project = await project_factory()
  version = BOQVersion(
    id=uuid4(),
    organization_id=organization.id,
    project_id=project.id,
    label="V1",
    covered_area_sqft=Decimal("1000"),
  )
  db_session.add(version)

  trade = "Labour Contractor — grey structure"
  db_session.add(
    LabourRate(
      id=uuid4(),
      organization_id=organization.id,
      trade=trade,
      unit="Sft",
      rate=Decimal("550"),
    )
  )
  db_session.add(
    BOQItem(
      id=uuid4(),
      organization_id=organization.id,
      boq_version_id=version.id,
      material_name=trade,
      unit="Sft",
      quantity=Decimal("1000"),
      unit_rate=Decimal("550"),
      item_type=BOQItemType.LABOUR,
      status=BOQItemStatus.APPROVED,
      version=1,
    )
  )
  draft = BOQItem(
    id=uuid4(),
    organization_id=organization.id,
    boq_version_id=version.id,
    material_name="Old draft labour",
    unit="Sft",
    quantity=Decimal("1000"),
    unit_rate=Decimal("400"),
    item_type=BOQItemType.LABOUR,
    status=BOQItemStatus.DRAFT,
    version=1,
  )
  db_session.add(draft)
  await db_session.flush()

  svc = _svc(db_session)
  created = await svc.generate_labour_items(organization.id, version.id)
  assert created == []

  remaining = await db_session.execute(
    select(BOQItem).where(
      BOQItem.boq_version_id == version.id,
      BOQItem.item_type == BOQItemType.LABOUR,
      BOQItem.status == BOQItemStatus.DRAFT,
    )
  )
  assert remaining.scalars().all() == []

@pytest.mark.asyncio
async def test_summary_only_counts_approved_priced(
  db_session,
  organization,
  project_factory,
):
  project = await project_factory()
  version = BOQVersion(
    id=uuid4(),
    organization_id=organization.id,
    project_id=project.id,
    label="V1",
    covered_area_sqft=Decimal("100"),
  )
  db_session.add(version)

  items = [
    BOQItem(
      id=uuid4(),
      organization_id=organization.id,
      boq_version_id=version.id,
      material_name="Mat A",
      unit="m3",
      quantity=Decimal("2"),
      unit_rate=Decimal("50"),
      item_type=BOQItemType.MATERIAL,
      status=BOQItemStatus.APPROVED,
      version=1,
    ),
    BOQItem(
      id=uuid4(),
      organization_id=organization.id,
      boq_version_id=version.id,
      material_name="Mat B",
      unit="m3",
      quantity=Decimal("10"),
      unit_rate=Decimal("50"),
      item_type=BOQItemType.MATERIAL,
      status=BOQItemStatus.DRAFT,
      version=1,
    ),
    BOQItem(
      id=uuid4(),
      organization_id=organization.id,
      boq_version_id=version.id,
      material_name="Labour",
      unit="Sft",
      quantity=Decimal("100"),
      unit_rate=Decimal("10"),
      item_type=BOQItemType.LABOUR,
      status=BOQItemStatus.APPROVED,
      version=1,
    ),
    BOQItem(
      id=uuid4(),
      organization_id=organization.id,
      boq_version_id=version.id,
      material_name="Custom",
      unit="ls",
      quantity=Decimal("1"),
      unit_rate=None,
      item_type=BOQItemType.CUSTOM,
      status=BOQItemStatus.DRAFT,
      version=1,
    ),
  ]
  db_session.add_all(items)
  await db_session.flush()

  svc = _svc(db_session)
  summary = await svc.get_boq_summary(organization.id, version.id)

  assert summary["materials_total"] == Decimal("100")
  assert summary["labour_total"] == Decimal("1000")
  assert summary["custom_total"] == Decimal("0")
  assert summary["grand_total"] == Decimal("1100")
  assert summary["unpriced_item_count"] == 1
  assert summary["unapproved_item_count"] == 2
  assert summary["item_count"] == 4
  assert summary["cost_per_sqft"] == Decimal("11")

@pytest.mark.asyncio
async def test_export_rejects_draft_items(
  db_session,
  organization,
  project_factory,
):
  project = await project_factory()
  version = BOQVersion(
    id=uuid4(),
    organization_id=organization.id,
    project_id=project.id,
    label="Export Me",
  )
  db_session.add(version)
  db_session.add(
    BOQItem(
      id=uuid4(),
      organization_id=organization.id,
      boq_version_id=version.id,
      material_name="Draft",
      unit="m3",
      quantity=Decimal("1"),
      unit_rate=Decimal("10"),
      item_type=BOQItemType.MATERIAL,
      status=BOQItemStatus.DRAFT,
      version=1,
    )
  )
  await db_session.flush()

  svc = _svc(db_session)
  with pytest.raises(TraceException) as exc:
    await svc.export_boq_pdf(organization.id, version.id)
  assert exc.value.code == "BOQ_HAS_DRAFT_ITEMS"

  with pytest.raises(TraceException) as exc:
    await svc.export_boq_xlsx(organization.id, version.id)
  assert exc.value.code == "BOQ_HAS_DRAFT_ITEMS"

@pytest.mark.asyncio
async def test_normalize_cache_hit(
  db_session,
  organization,
):
  raw = "concrete grade 25"
  normalized_input = " ".join(raw.strip().lower().split())
  h = sha256(normalized_input.encode()).hexdigest()

  db_session.add(
    MaterialNormalizationCache(
      id=uuid4(),
      input_hash=h,
      normalized_name="Concrete Grade 25 (M25)",
      category="Concrete",
      source="dictionary",
      organization_id=organization.id,
    )
  )
  await db_session.flush()

  svc = _svc(db_session)
  name, category, matched = await svc.normalize_material(organization.id, raw)
  assert matched is True
  assert name == "Concrete Grade 25 (M25)"
  assert category == "Concrete"

@pytest.mark.asyncio
async def test_normalize_library_fallback_writes_cache(
  db_session,
  organization,
):
  db_session.add(
    MaterialLibrary(
      id=uuid4(),
      organization_id=organization.id,
      raw_text="concrete grade 25",
      normalized_name="Concrete Grade 25 (M25)",
      category="Concrete",
      default_unit="m3",
      default_rate=Decimal("18500"),
    )
  )
  await db_session.flush()

  svc = _svc(db_session)
  name, category, matched = await svc.normalize_material(
    organization.id, "concrete grade 25"
  )
  assert matched is True
  assert name == "Concrete Grade 25 (M25)"

  result = await db_session.execute(select(MaterialNormalizationCache))
  caches = result.scalars().all()
  assert any(c.source == "dictionary" for c in caches)

@pytest.mark.asyncio
async def test_normalize_unknown_returns_raw(
  db_session,
  organization,
):
  svc = _svc(db_session)
  name, category, matched = await svc.normalize_material(
    organization.id, "completely unknown material xyz"
  )
  assert matched is False
  assert name == "completely unknown material xyz"
  assert category is None

@pytest.mark.asyncio
async def test_material_library_rejects_duplicate(
  db_session,
  organization,
):
  db_session.add(
    MaterialLibrary(
      id=uuid4(),
      organization_id=organization.id,
      raw_text="cement opc",
      normalized_name="OPC Cement",
      category="Cement",
    )
  )
  await db_session.flush()

  svc = _svc(db_session)
  with pytest.raises(TraceException) as exc:
    await svc.create_material_library_entry(
      organization.id,
      MaterialLibraryCreateRequest(
        raw_text="cement opc",
        normalized_name="OPC Cement",
      ),
    )
  assert exc.value.code == "MATERIAL_MAPPING_ALREADY_EXISTS"

@pytest.mark.asyncio
async def test_labour_rate_rejects_duplicate(
  db_session,
  organization,
):
  db_session.add(
    LabourRate(
      id=uuid4(),
      organization_id=organization.id,
      trade="Electrician",
      unit="Sft",
      rate=Decimal("30"),
    )
  )
  await db_session.flush()

  svc = _svc(db_session)
  with pytest.raises(TraceException) as exc:
    await svc.create_labour_rate(
      organization.id,
      LabourRateCreateRequest(trade="Electrician", unit="Sft", rate=Decimal("35")),
    )
  assert exc.value.code == "LABOUR_RATE_ALREADY_EXISTS"