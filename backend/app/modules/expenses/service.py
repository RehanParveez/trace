from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.expenses.repository import ExpenseRepository
from app.modules.projects.repository import ProjectRepository
from uuid import UUID, uuid4
from app.modules.expenses.models import Expense, ExpenseStatus
from app.modules.expenses.schemas import ExpenseCreateRequest, ExpenseReviewRequest
from app.core.exceptions import TraceException
from app.modules.budgets.repository import BudgetRepository
from decimal import Decimal

class ExpenseService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = ExpenseRepository(session)
    self.projects = ProjectRepository(session)
    self.budgets = BudgetRepository(session)

  async def list_expenses(
    self,
    organization_id: UUID,
    project_id: UUID | None = None,
    status: ExpenseStatus | None = None,
    skip: int = 0,
    limit: int = 100,
  ) -> list[Expense]:
    if project_id is not None:
      await self._ensure_project(organization_id, project_id)
    return await self.repo.list_expenses(
      organization_id, project_id, status, skip, limit,
    )
    
  async def get_organization_summary(
    self, organization_id: UUID,
  ) -> dict:
    return await self.repo.get_organization_summary(organization_id)
  
  async def get_status_totals(
    self,
    organization_id: UUID,
    project_id: UUID | None = None,
  ) -> dict[ExpenseStatus, Decimal]:
    
    if project_id is not None:
      await self._ensure_project(organization_id, project_id)
    return await self.repo.get_status_totals(organization_id, project_id)

  async def create_expense(
    self,
    organization_id: UUID,
    user_id: UUID,
    payload: ExpenseCreateRequest,
  ) -> Expense:
    await self._ensure_project(organization_id, payload.project_id)
    category_name, budget_category_id = await self._resolve_category(
      organization_id, payload.project_id, payload.category, payload.budget_category_id,
    )
    expense = Expense(
      id=uuid4(),
      organization_id=organization_id,
      project_id=payload.project_id,
      category=category_name,
      budget_category_id=budget_category_id,
      description=payload.description.strip() if payload.description else None,
      amount=payload.amount,
      expense_date=payload.expense_date,
      status=ExpenseStatus.PENDING,
      submitted_by=user_id,
    )
    await self.repo.create(expense)
    await self.session.commit()
    return expense

  async def approve_expense(
    self,
    organization_id: UUID,
    expense_id: UUID,
    reviewer_id: UUID,
    payload: ExpenseReviewRequest,
  ) -> Expense:
    return await self._review(
      organization_id, expense_id, reviewer_id, payload, ExpenseStatus.APPROVED,
    )

  async def reject_expense(
    self,
    organization_id: UUID,
    expense_id: UUID,
    reviewer_id: UUID,
    payload: ExpenseReviewRequest,
  ) -> Expense:
    return await self._review(
      organization_id, expense_id, reviewer_id, payload, ExpenseStatus.REJECTED,
    )

  async def _review(
    self,
    organization_id: UUID,
    expense_id: UUID,
    reviewer_id: UUID,
    payload: ExpenseReviewRequest,
    new_status: ExpenseStatus,
  ) -> Expense:
    expense = await self.repo.get_by_id_for_update(expense_id, organization_id)
    if expense is None:
      raise TraceException(
        "Expense not found.", status_code=404, code="EXPENSE_NOT_FOUND",
      )
    if expense.status != ExpenseStatus.PENDING:
      raise TraceException(
        "Only pending expenses can be reviewed.",
        status_code=409, code="EXPENSE_ALREADY_REVIEWED",
      )
    if payload.budget_category_id is not None:
      category_name, budget_category_id = await self._resolve_category(
        organization_id, expense.project_id, None, payload.budget_category_id,
      )
      expense.category = category_name
      expense.budget_category_id = budget_category_id
    expense.status = new_status
    expense.reviewed_by = reviewer_id
    expense.review_note = payload.note.strip() if payload.note else None
    await self.session.flush()
    await self.session.commit()
    return expense

  async def _resolve_category(
    self,
    organization_id: UUID,
    project_id: UUID,
    free_text: str | None,
    budget_category_id: UUID | None,
  ) -> tuple[str, UUID | None]:
    if budget_category_id is not None:
      category = await self.budgets.get_category_for_project(
        budget_category_id, project_id, organization_id,
      )
      if category is None:
        raise TraceException(
          "That budget category does not belong to this project's budget.",
          status_code=422, code="BUDGET_CATEGORY_NOT_FOUND",
        )
      return category.name, category.id
    label = (free_text or "").strip()
    if not label:
      raise TraceException(
        "Pick a budget category or type a category.",
        status_code=422, code="EXPENSE_CATEGORY_REQUIRED",
      )
    matches = await self.budgets.find_categories_by_name(project_id, organization_id, label)
    if len(matches) == 1:
      return matches[0].name, matches[0].id
    return label, None

  async def _ensure_project(self, organization_id: UUID, project_id: UUID) -> None:
    project = await self.projects.get_by_id_and_org(project_id, organization_id)
    if project is None:
      raise TraceException(
        "Project not found.", status_code=404, code="PROJECT_NOT_FOUND",
      )
      
  