from __future__ import annotations
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.repository import BOQVersionRepository, LabourRateRepository, BOQItemRepository
from uuid import UUID
from app.core.exceptions import TraceException
from app.modules.drawings_boq.models import BOQItemType, BOQItem, BOQItemStatus, BOQVersionStatus
from app.modules.drawings_boq.boq_service import assert_mutable, BOQEngineService
from app.modules.audit.service import AuditLogService
from datetime import date
from app.modules.audit.models import AuditAction, AuditEntityType

AREA_UNITS = {"sft", "sq ft", "sqft", "m2", "sqm", "square feet"}
SQFT_PER_M2 = Decimal("10.7639104")

def labour_quantity(covered_area_sqft: Decimal, rate_unit: str) -> Decimal:
  if (rate_unit or "").strip().lower() in {"m2", "sqm"}:
    return (Decimal(covered_area_sqft) / SQFT_PER_M2).quantize(Decimal("0.0001"))
  return covered_area_sqft

class LabourPricingService:
 
  def __init__(self, session: AsyncSession):
    self.session = session
    self.versions = BOQVersionRepository(session)
    self.items = BOQItemRepository(session)
    self.labour_rates = LabourRateRepository(session)
    self.audit = AuditLogService(session)

  async def generate(self, organization_id: UUID, boq_version_id: UUID, user_id: UUID | None = None) -> list[BOQItem]:
    version = await self.versions.get_by_id_and_org(boq_version_id, organization_id)
    
    if version is None:
      raise TraceException("BOQ version not found.", status_code=404, code="BOQ_VERSION_NOT_FOUND")
    if version.status == BOQVersionStatus.SUPERSEDED:
      raise TraceException("Cannot generate labour items on a superseded BOQ version.",
        status_code=409, code="BOQ_VERSION_SUPERSEDED")
    assert_mutable(version)
    
    if not version.covered_area_sqft or version.covered_area_sqft <= 0:
      raise TraceException("Set covered_area_sqft on this BOQ version before generating labour costs.",
        status_code=422, code="COVERED_AREA_REQUIRED")

    today = date.today()
    rates = [r for r in await self.labour_rates.list_by_org(organization_id)
      if r.effective_from is None or r.effective_from <= today]
    if not rates:
      raise TraceException("No labour rates configured for this organization.", status_code=422, code="NO_LABOUR_RATES")
    area_rates = [r for r in rates if r.unit.strip().lower() in AREA_UNITS]
    if not area_rates:
      raise TraceException("No area-based (Sft/m²) labour rates configured.", status_code=422, code="NO_AREA_LABOUR_RATES")

    existing = await self.items.list_by_version(boq_version_id, organization_id)
    approved_trades = {i.material_name for i in existing
      if i.item_type == BOQItemType.LABOUR and i.status == BOQItemStatus.APPROVED}
    replaced = [i for i in existing if i.item_type == BOQItemType.LABOUR and i.status == BOQItemStatus.DRAFT]
    for item in replaced:
      await self.session.delete(item)
    await self.session.flush()

    new_items = [BOQItem(
      organization_id=organization_id, boq_version_id=boq_version_id, material_name=rate.trade, category="Labour",
      unit=rate.unit, quantity=labour_quantity(version.covered_area_sqft, rate.unit), unit_rate=rate.rate,
      item_type=BOQItemType.LABOUR, source_kind="ESTIMATE", work_item_code=rate.work_item_code,
      net_quantity=labour_quantity(version.covered_area_sqft, rate.unit))
      for rate in area_rates if rate.trade not in approved_trades]
    
    if new_items:
      await self.items.bulk_create(new_items)
    if version.origin == "ENGINE":
      await BOQEngineService(self.session).refresh_pricing_issue(organization_id, version.id)
    await self.session.commit()
    await self.audit.log(organization_id, user_id, AuditEntityType.BOQ_VERSION, version.id, AuditAction.UPDATE,
      f"Generated labour lines: {len(new_items)} created, {len(replaced)} draft line(s) replaced, "
      f"{len(approved_trades)} approved trade(s) kept")
    return new_items