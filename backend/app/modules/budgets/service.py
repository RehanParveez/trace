from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.budgets.repository import BudgetRepository
from app.modules.projects.repository import ProjectRepository
from app.modules.budgets.models import Budget, BudgetCategory
from app.modules.budgets.schemas import BudgetSaveRequest
from app.core.exceptions import TraceException
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy.exc import IntegrityError
from app.modules.organizations.repository import OrganizationRepository
from app.modules.expenses.repository import ExpenseRepository
from app.modules.expenses.models import ExpenseStatus
from app.modules.labour.repository import LabourRepository
from app.modules.procurement.repository import ProcurementRepository
from app.modules.subcontractors.repository import SubcontractorRepository

class BudgetService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = BudgetRepository(session)
    self.projects = ProjectRepository(session)
    self.organizations = OrganizationRepository(session) 
    self.expenses = ExpenseRepository(session)
    self.labour = LabourRepository(session)
    self.procurement = ProcurementRepository(session)
    self.subcontractors = SubcontractorRepository(session) 

  async def list_budgets(
    self, organization_id: UUID, project_id: UUID | None = None,
  ) -> list[Budget]:
    if project_id is None:
      return []
    await self._ensure_project(organization_id, project_id)
    return await self.repo.list_by_project(project_id, organization_id)
  
  async def list_budgets_by_org(self, organization_id: UUID) -> list[Budget]:
    return await self.repo.list_by_org(organization_id)

  async def get_organization_summary(
    self, organization_id: UUID,
) -> dict:
    organization = await self.organizations.get_organization(organization_id)
    summary = await self.repo.get_organization_summary(organization_id)
    summary["currency"] = organization.currency if organization else "PKR"
    return summary

  async def save_budget(
    self, organization_id: UUID, payload: BudgetSaveRequest,
  ) -> Budget:
    await self._ensure_project(organization_id, payload.project_id) 

    organization = await self.organizations.get_organization(organization_id)
    if organization is None:
     raise TraceException(
        "Organization not found.",
        status_code=404,
        code="ORGANIZATION_NOT_FOUND",
    )

    requested_currency = (payload.currency or organization.currency).upper().strip()
    if len(requested_currency) != 3:
     raise TraceException(
        "Currency must be a 3-letter code.",
        status_code=422,
        code="INVALID_CURRENCY",
    )
     
    if requested_currency != organization.currency:
     raise TraceException(
        f"This organization's operating currency is {organization.currency}. "
        f"Budgets cannot be created in {requested_currency}.",
        status_code=422,
        code="CURRENCY_MISMATCH",
    )
    currency = organization.currency

    budget = await self.repo.get_by_project_for_update(payload.project_id, organization_id)
    created_new = budget is None

    if budget is None:
      budget = Budget(
        id=uuid4(),
        organization_id=organization_id,
        project_id=payload.project_id,
        approved_amount=payload.approved_amount,
        currency=currency,
        notes=payload.notes.strip() if payload.notes else None,
      )
      await self.repo.create(budget)
    else:
      if payload.version is None or payload.version != budget.version:
        raise TraceException(
          "This budget was changed by someone else. Reload and try again.",
          status_code=409, code="BUDGET_VERSION_CONFLICT",
        )

      budget.approved_amount = payload.approved_amount
      budget.currency = currency
      budget.notes = payload.notes.strip() if payload.notes else None
      budget.version += 1
      budget.version += 1

    await self.session.flush()

    existing_categories = {} if created_new else {c.id: c for c in budget.categories}
    kept_ids: set[UUID] = set()
    for cat in payload.categories:
      name = cat.name.strip()
      if not name:
       continue
      current = existing_categories.get(cat.id) if cat.id is not None else None
      if current is not None:
        current.name = name
        current.allocated_amount = Decimal(cat.allocated_amount)
        kept_ids.add(current.id)
        continue
      self.session.add(
       BudgetCategory(
       id=uuid4(),
       organization_id=organization_id,
       budget_id=budget.id,
       name=name,
       allocated_amount=Decimal(cat.allocated_amount),
     )
   )

    for category_id, category in existing_categories.items():
      if category_id in kept_ids:
        continue
      linked = await self.expenses.count_for_category(category_id, organization_id)
      if linked > 0:
        raise TraceException(
          f"The category '{category.name}' has {linked} expense(s) recorded against it, so it cannot be removed. "
          "Rename it or set its allocation to 0 instead.",
          status_code=409, code="BUDGET_CATEGORY_IN_USE",
        )
      await self.session.delete(category)

    try:
      await self.session.flush()
      await self.session.commit()
    except IntegrityError as exc:
      await self.session.rollback()
      raise TraceException(
        "Unable to save budget.",
        status_code=409, code="BUDGET_SAVE_CONFLICT",
      ) from exc

    await self.session.refresh(budget, attribute_names=["categories"])
    return budget

  async def get_status(
    self,
    organization_id: UUID,
    project_id: UUID,
    *,
    include_expenses: bool,
    include_labour: bool,
    include_subcontracts: bool,
    include_materials: bool,
  ) -> dict:
    """Budget against actual for one project, worked out in one place so every screen shows the same figures.
    Parts the caller may not see come back as None and are left out of the totals."""
    await self._ensure_project(organization_id, project_id)
    organization = await self.organizations.get_organization(organization_id)
    currency = organization.currency if organization else "PKR"
    budget = await self.repo.get_by_project(project_id, organization_id)

    zero = Decimal("0")
    approved_by_category: dict[UUID | None, Decimal] = {}
    pending_by_category: dict[UUID | None, Decimal] = {}
    expenses_approved: Decimal | None = None
    expenses_pending: Decimal | None = None
    if include_expenses:
      expenses_approved = zero
      expenses_pending = zero
      for category_id, status, total in await self.expenses.get_category_totals(organization_id, project_id):
        if status == ExpenseStatus.APPROVED:
          approved_by_category[category_id] = approved_by_category.get(category_id, zero) + total
          expenses_approved += total
        else:
          pending_by_category[category_id] = pending_by_category.get(category_id, zero) + total
          expenses_pending += total

    labour_accrued = (
      await self.labour.get_total_accrued_cost(organization_id, project_id) if include_labour else None
    )
    subcontracted = (
      Decimal(str(await self.subcontractors.get_project_billed_total(organization_id, project_id)))
      if include_subcontracts else None
    )
    materials_received: Decimal | None = None
    materials_committed: Decimal | None = None
    if include_materials:
      materials_received, materials_committed = await self.procurement.get_project_materials_money(
        organization_id, project_id,
      )

    total_used = sum(
      (v for v in (expenses_approved, labour_accrued, subcontracted, materials_received) if v is not None), zero,
    )
    forecast_total = total_used + (materials_committed or zero)
    approved_amount = Decimal(str(budget.approved_amount)) if budget else zero

    categories = []
    allocated_total = zero
    if budget is not None:
      for category in budget.categories:
        allocated = Decimal(str(category.allocated_amount))
        allocated_total += allocated
        spent = approved_by_category.get(category.id, zero)
        categories.append({
          "category_id": category.id, "name": category.name, "allocated_amount": allocated,
          "spent_amount": spent, "pending_amount": pending_by_category.get(category.id, zero),
          "remaining_amount": allocated - spent,
          "used_percentage": float(spent / allocated * 100) if allocated > 0 else None,
        })
        
    if include_expenses:
      loose_spent = approved_by_category.get(None, zero)
      loose_pending = pending_by_category.get(None, zero)
      if loose_spent > 0 or loose_pending > 0:
        categories.append({
          "category_id": None, "name": "Not assigned to a category", "allocated_amount": zero,
          "spent_amount": loose_spent, "pending_amount": loose_pending,
          "remaining_amount": zero - loose_spent, "used_percentage": None,
        })

    return {
      "project_id": project_id, "has_budget": budget is not None, "currency": currency,
      "approved_amount": approved_amount, "allocated_total": allocated_total,
      "expenses_approved": expenses_approved, "expenses_pending": expenses_pending,
      "labour_accrued": labour_accrued, "subcontracted": subcontracted,
      "materials_received": materials_received, "materials_committed": materials_committed,
      "total_used": total_used, "forecast_total": forecast_total,
      "remaining": approved_amount - forecast_total,
      "used_percentage": float(total_used / approved_amount * 100) if approved_amount > 0 else None,
      "categories": categories,
    }

  async def _ensure_project(self, organization_id: UUID, project_id: UUID) -> None:
    project = await self.projects.get_by_id_and_org(project_id, organization_id)
    if project is None:
      raise TraceException(
        "Project not found.",
        status_code=404, code="PROJECT_NOT_FOUND",
      )