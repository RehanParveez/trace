from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.material_stock.models import MaterialIssue, MaterialIssueType
from uuid import UUID
from sqlalchemy import func, select
from app.modules.procurement.models import ProcurementRequest, ProcurementStatus

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
    result = await self.session.execute(
      select(
        func.lower(func.trim(ProcurementRequest.material_name)).label("name_key"),
        func.max(ProcurementRequest.material_name).label("display_name"),
        func.max(ProcurementRequest.unit).label("unit"),
        func.sum(ProcurementRequest.quantity).label("total_qty"),
      )
      .where(
        ProcurementRequest.organization_id == organization_id,
        ProcurementRequest.project_id == project_id,
        ProcurementRequest.status == ProcurementStatus.RECEIVED,
      )
      .group_by(func.lower(func.trim(ProcurementRequest.material_name)))
    )
    return [(row.name_key, row.display_name, row.unit, row.total_qty) for row in result.all()]

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