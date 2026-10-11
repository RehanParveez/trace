from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.material_stock.models import MaterialIssue, MaterialIssueType
from uuid import UUID
from decimal import Decimal
from sqlalchemy import case, func, or_, select
from app.modules.procurement.models import ProcurementDelivery, ProcurementRequest, ProcurementStatus

class MaterialStockRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create_issue(self, issue: MaterialIssue) -> MaterialIssue:
    self.session.add(issue)
    await self.session.flush()
    return issue

  async def list_issues(self, organization_id: UUID, project_id: UUID) -> list[MaterialIssue]:
    result = await self.session.execute(
      select(MaterialIssue)
      .where(MaterialIssue.organization_id == organization_id, MaterialIssue.project_id == project_id)
      .order_by(MaterialIssue.issue_date.desc())
    )
    return list(result.scalars().all())

  async def get_received_totals_by_material(
    self, organization_id: UUID, project_id: UUID,
  ) -> list[tuple[str, str, str, object]]:
    delivered = (
      select(
        ProcurementDelivery.request_id.label("request_id"),
        func.sum(ProcurementDelivery.quantity).label("qty"),
      )
      .where(
        ProcurementDelivery.organization_id == organization_id,
        ProcurementDelivery.project_id == project_id,
        ProcurementDelivery.voided_at.is_(None),
      )
      .group_by(ProcurementDelivery.request_id)
      .subquery()
    )
    received_qty = case(
      (delivered.c.qty.isnot(None), delivered.c.qty),
      (ProcurementRequest.status == ProcurementStatus.RECEIVED, ProcurementRequest.quantity),
      else_=0,
    )
    result = await self.session.execute(
      select(
        func.lower(func.trim(ProcurementRequest.material_name)).label("name_key"),
        func.max(ProcurementRequest.material_name).label("display_name"),
        func.max(ProcurementRequest.unit).label("unit"),
        func.sum(received_qty).label("total_qty"),
      )
      .select_from(ProcurementRequest)
      .outerjoin(delivered, delivered.c.request_id == ProcurementRequest.id)
      .where(
        ProcurementRequest.organization_id == organization_id,
        ProcurementRequest.project_id == project_id,
        or_(delivered.c.qty.isnot(None), ProcurementRequest.status == ProcurementStatus.RECEIVED),
      )
      .group_by(func.lower(func.trim(ProcurementRequest.material_name)))
    )
    return [(row.name_key, row.display_name, row.unit, row.total_qty) for row in result.all()]

  async def get_material_balance(
    self, organization_id: UUID, project_id: UUID, material_name: str,
  ) -> Decimal:
    key = material_name.strip().lower()
    received = Decimal("0")
    for name_key, _display, _unit, qty in await self.get_received_totals_by_material(organization_id, project_id):
      if name_key == key:
        received += Decimal(str(qty))
    used = Decimal("0")
    for name_key, _display, _unit, _type, qty in await self.get_issue_totals_by_material(organization_id, project_id):
      if name_key == key:
        used += Decimal(str(qty))
    return received - used

  async def get_known_units(
    self, organization_id: UUID, project_id: UUID, material_name: str,
  ) -> set[str]:
    key = material_name.strip().lower()
    units: set[str] = set()
    requests = await self.session.execute(
      select(ProcurementRequest.unit).where(
        ProcurementRequest.organization_id == organization_id,
        ProcurementRequest.project_id == project_id,
        func.lower(func.trim(ProcurementRequest.material_name)) == key,
        ProcurementRequest.status.in_([ProcurementStatus.ORDERED, ProcurementStatus.RECEIVED]),
      )
    )
    
    units.update(u.strip().lower() for u in requests.scalars().all())
    issues = await self.session.execute(
      select(MaterialIssue.unit).where(
        MaterialIssue.organization_id == organization_id,
        MaterialIssue.project_id == project_id,
        func.lower(func.trim(MaterialIssue.material_name)) == key,
      )
    )
    units.update(u.strip().lower() for u in issues.scalars().all())
    return units

  async def get_issue_totals_by_material(
    self, organization_id: UUID, project_id: UUID,
  ) -> list[tuple[str, str, str, MaterialIssueType, object]]:
    result = await self.session.execute(
      select(
        func.lower(func.trim(MaterialIssue.material_name)).label("name_key"),
        func.max(MaterialIssue.material_name).label("display_name"),
        func.max(MaterialIssue.unit).label("unit"),
        MaterialIssue.issue_type,
        func.sum(MaterialIssue.quantity).label("total_qty"),
      )
      .where(MaterialIssue.organization_id == organization_id, MaterialIssue.project_id == project_id)
      .group_by(func.lower(func.trim(MaterialIssue.material_name)), MaterialIssue.issue_type)
    )
    return [(row.name_key, row.display_name, row.unit, row.issue_type, row.total_qty) for row in result.all()]