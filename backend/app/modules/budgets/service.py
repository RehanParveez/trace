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

class BudgetService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = BudgetRepository(session)
    self.projects = ProjectRepository(session)

  async def list_budgets(
    self, organization_id: UUID, project_id: UUID | None = None,
  ) -> list[Budget]:
    if project_id is None:
      return []
    await self._ensure_project(organization_id, project_id)
    return await self.repo.list_by_project(project_id, organization_id)

  async def save_budget(
    self, organization_id: UUID, payload: BudgetSaveRequest,
  ) -> Budget:
    await self._ensure_project(organization_id, payload.project_id)

    currency = (payload.currency or "PKR").upper().strip()
    if len(currency) != 3:
      raise TraceException(
        "Currency must be a 3-letter code.",
        status_code=422, code="INVALID_CURRENCY",
      )

    budget = await self.repo.get_by_project(payload.project_id, organization_id)

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
      budget.approved_amount = payload.approved_amount
      budget.currency = currency
      budget.notes = payload.notes.strip() if payload.notes else None
      await self.repo.delete_categories(budget)

    await self.session.flush()

    for cat in payload.categories:
      name = cat.name.strip()
      if not name:
       continue
      self.session.add(
       BudgetCategory(
       id=uuid4(),
       budget_id=budget.id,
       name=name,
       allocated_amount=Decimal(cat.allocated_amount),
     )
   )

    try:
      await self.session.flush()
      await self.session.commit()
    except IntegrityError as exc:
      await self.session.rollback()
      raise TraceException(
        "Unable to save budget.",
        status_code=409, code="BUDGET_SAVE_CONFLICT",
      ) from exc

    reloaded = await self.repo.get_by_project(payload.project_id, organization_id)
    return reloaded  

  async def _ensure_project(self, organization_id: UUID, project_id: UUID) -> None:
    project = await self.projects.get_by_id_and_org(project_id, organization_id)
    if project is None:
      raise TraceException(
        "Project not found.",
        status_code=404, code="PROJECT_NOT_FOUND",
      )