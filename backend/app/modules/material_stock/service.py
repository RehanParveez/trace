from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.material_stock.repository import MaterialStockRepository
from app.modules.projects.repository import ProjectRepository
from app.modules.material_stock.models import MaterialIssue, MaterialIssueType
from app.modules.material_stock.schemas import MaterialIssueCreateRequest
from uuid import UUID, uuid4
from decimal import Decimal
from sqlalchemy import func, select
from app.modules.identity.models import Organization
from app.core.exceptions import TraceException
from app.modules.drawings_boq.models import MaterialLibrary

class MaterialStockService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = MaterialStockRepository(session)
    self.projects = ProjectRepository(session)

  async def record_issue(
    self, organization_id: UUID, project_id: UUID, payload: MaterialIssueCreateRequest, actor_user_id: UUID,
  ) -> MaterialIssue:
    await self._require_project(organization_id, project_id)
    issue = MaterialIssue(
      id=uuid4(), organization_id=organization_id, project_id=project_id,
      material_name=payload.material_name.strip(), unit=payload.unit.strip(), quantity=payload.quantity,
      issue_type=payload.issue_type, issued_to=payload.issued_to, issue_date=payload.issue_date,
      notes=payload.notes, recorded_by_user_id=actor_user_id,
    )
    await self.repo.create_issue(issue)
    await self.session.commit()
    return issue

  async def list_issues(self, organization_id: UUID, project_id: UUID) -> list[MaterialIssue]:
    await self._require_project(organization_id, project_id)
    return await self.repo.list_issues(organization_id, project_id)

  async def get_reconciliation(self, organization_id: UUID, project_id: UUID) -> dict:
    await self._require_project(organization_id, project_id)

    received_rows = await self.repo.get_received_totals_by_material(organization_id, project_id)
    issue_rows = await self.repo.get_issue_totals_by_material(organization_id, project_id)

    lines_by_key: dict[str, dict] = {}
    for name_key, display_name, unit, qty in received_rows:
      lines_by_key[name_key] = {
        "material_name": display_name, "unit": unit,
        "received": Decimal(str(qty)), "issued": Decimal("0"), "wastage": Decimal("0"),
      }

    for name_key, display_name, unit, issue_type, qty in issue_rows:
      line = lines_by_key.setdefault(
        name_key, {"material_name": display_name, "unit": unit, "received": Decimal("0"), "issued": Decimal("0"), "wastage": Decimal("0")},
      )
      if issue_type == MaterialIssueType.ISSUED:
        line["issued"] += Decimal(str(qty))
      else:
        line["wastage"] += Decimal(str(qty))

    organization = await self.session.get(Organization, organization_id)
    currency = organization.currency if organization else "PKR"

    lines = []
    for line in lines_by_key.values():
      balance = line["received"] - line["issued"] - line["wastage"]
      wastage_percentage = (
        float(line["wastage"] / line["received"] * 100) if line["received"] > 0 else None
      )
      estimated_wastage_cost = await self._estimate_wastage_cost(organization_id, line["material_name"], line["wastage"])
      lines.append({
        "material_name": line["material_name"], "unit": line["unit"],
        "total_received": line["received"], "total_issued": line["issued"], "total_wastage": line["wastage"],
        "balance": balance, "wastage_percentage": wastage_percentage, "estimated_wastage_cost": estimated_wastage_cost,
      })

    lines.sort(key=lambda l: l["material_name"].lower())
    return {"project_id": project_id, "lines": lines, "currency": currency}

  async def _estimate_wastage_cost(
    self, organization_id: UUID, material_name: str, wastage_qty: Decimal,
  ) -> Decimal | None:

    if wastage_qty <= 0:
      return None
    try:
      result = await self.session.execute(
        select(MaterialLibrary.default_rate).where(
          MaterialLibrary.organization_id == organization_id,
          func.lower(MaterialLibrary.normalized_name) == material_name.lower(),
        ).limit(1)
      )
      rate = result.scalar_one_or_none()
      if rate is None:
        return None
      return (wastage_qty * Decimal(str(rate))).quantize(Decimal("0.01"))
    except Exception:
      return None

  async def _require_project(self, organization_id: UUID, project_id: UUID):
    project = await self.projects.get_by_id_and_org(project_id, organization_id)
    if project is None:
      raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")
    return project