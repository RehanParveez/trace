from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.expenses.repository import ExpenseRepository
from app.modules.projects.repository import ProjectRepository
from uuid import UUID, uuid4
from app.modules.expenses.models import Expense, ExpenseStatus
from app.modules.expenses.schemas import ExpenseCreateRequest, ExpenseReviewRequest
from app.core.exceptions import TraceException

class ExpenseService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = ExpenseRepository(session)
    self.projects = ProjectRepository(session)

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

  async def create_expense(
    self,
    organization_id: UUID,
    user_id: UUID,
    payload: ExpenseCreateRequest,
  ) -> Expense:
    await self._ensure_project(organization_id, payload.project_id)
    expense = Expense(
      id=uuid4(),
      organization_id=organization_id,
      project_id=payload.project_id,
      category=payload.category.strip(),
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
    expense = await self.repo.get_by_id(expense_id, organization_id)
    if expense is None:
      raise TraceException(
        "Expense not found.", status_code=404, code="EXPENSE_NOT_FOUND",
      )
    if expense.status != ExpenseStatus.PENDING:
      raise TraceException(
        "Only pending expenses can be reviewed.",
        status_code=409, code="EXPENSE_ALREADY_REVIEWED",
      )
    expense.status = new_status
    expense.reviewed_by = reviewer_id
    expense.review_note = payload.note.strip() if payload.note else None
    await self.session.flush()
    await self.session.commit()
    return expense

  async def _ensure_project(self, organization_id: UUID, project_id: UUID) -> None:
    project = await self.projects.get_by_id_and_org(project_id, organization_id)
    if project is None:
      raise TraceException(
        "Project not found.", status_code=404, code="PROJECT_NOT_FOUND",
      )