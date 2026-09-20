from __future__ import annotations
from decimal import Decimal
import pytest
from sqlalchemy import select
from app.core.exceptions import TraceException
from app.modules.budgets.models import BudgetCategory
from app.modules.budgets.schemas import BudgetCategoryInput, BudgetSaveRequest
from app.modules.budgets.service import BudgetService

def _save_payload(
  project_id,
  *,
  approved_amount: Decimal = Decimal("5000000.00"),
  currency: str | None = None,
  notes: str | None = "Initial approved budget",
  version: int | None = None,
  categories: list[BudgetCategoryInput] | None = None,
) -> BudgetSaveRequest:
  return BudgetSaveRequest(
    project_id=project_id,
    approved_amount=approved_amount,
    currency=currency,
    notes=notes,
    version=version,
    categories=categories or [],
  )

@pytest.mark.asyncio
async def test_save_budget_creates_new_budget_when_none_exists(
  budget_service: BudgetService,
  budget_admin_context,
  project_factory,
):
  org = budget_admin_context.organization
  project = await project_factory(organization_id=org.id)

  payload = _save_payload(
    project.id,
    approved_amount=Decimal("12500000.00"),
    notes="  Seed construction budget  ",
    categories=[
      BudgetCategoryInput(name="Civil works", allocated_amount=Decimal("6500000")),
      BudgetCategoryInput(name="  MEP  ", allocated_amount=Decimal("3200000")),
      BudgetCategoryInput(name="   ", allocated_amount=Decimal("100")),
      BudgetCategoryInput(name="\t", allocated_amount=Decimal("50")),
    ],
  )
  result = await budget_service.save_budget(org.id, payload)

  assert result is not None
  assert result.project_id == project.id
  assert result.organization_id == org.id
  assert result.approved_amount == Decimal("12500000.00")
  assert result.currency == org.currency
  assert result.notes == "Seed construction budget"
  assert result.version == 1
  assert len(result.categories) == 2
  names = {c.name for c in result.categories}
  assert names == {"Civil works", "MEP"}


@pytest.mark.asyncio
async def test_save_budget_rejects_project_from_other_organization(
  budget_service: BudgetService,
  budget_admin_context,
  other_organization,
  project_factory,
):
  org = budget_admin_context.organization
  foreign_project = await project_factory(organization_id=other_organization.id)
  payload = _save_payload(foreign_project.id)
  with pytest.raises(TraceException) as exc:
    await budget_service.save_budget(org.id, payload)
  assert exc.value.status_code == 404
  assert exc.value.code == "PROJECT_NOT_FOUND"
  
@pytest.mark.asyncio
async def test_save_budget_updates_existing_and_increments_version(
  budget_service: BudgetService,
  budget_admin_context,
  project_factory,
  make_budget,
  db_session,
):
  org = budget_admin_context.organization
  project = await project_factory(organization_id=org.id)

  existing = await make_budget(
    organization=org,
    project=project,
    approved_amount=Decimal("1000000"),
    version=3,
    categories=[("Old category", Decimal("500000"))],
  )

  payload = _save_payload(
    project.id,
    approved_amount=Decimal("2000000.00"),
    notes="Revised",
    version=3,
    categories=[
      BudgetCategoryInput(name="New A", allocated_amount=Decimal("1200000")),
      BudgetCategoryInput(name="New B", allocated_amount=Decimal("800000")),
    ],
  )
  result = await budget_service.save_budget(org.id, payload)

  assert result.id == existing.id
  assert result.approved_amount == Decimal("2000000.00")
  assert result.notes == "Revised"
  assert result.version == 4
  rows = await db_session.execute(
    select(BudgetCategory).where(BudgetCategory.budget_id == existing.id)
  )
  cats = list(rows.scalars().all())
  assert len(cats) == 2
  assert {c.name for c in cats} == {"New A", "New B"}
  
@pytest.mark.asyncio
async def test_save_budget_raises_version_conflict_on_stale_version(
  budget_service: BudgetService,
  budget_admin_context,
  project_factory,
  make_budget,
):
  org = budget_admin_context.organization
  project = await project_factory(organization_id=org.id)

  await make_budget(
    organization=org,
    project=project,
    version=5,
  )
  payload = _save_payload(project.id, version=4)
  with pytest.raises(TraceException) as exc:
    await budget_service.save_budget(org.id, payload)

  assert exc.value.status_code == 409
  assert exc.value.code == "BUDGET_VERSION_CONFLICT"

@pytest.mark.asyncio
async def test_save_budget_requires_version_when_budget_already_exists(
  budget_service: BudgetService,
  budget_admin_context,
  project_factory,
  make_budget,
):
  org = budget_admin_context.organization
  project = await project_factory(organization_id=org.id)

  await make_budget(organization=org, project=project, version=1)

  payload = _save_payload(project.id, version=None)

  with pytest.raises(TraceException) as exc:
    await budget_service.save_budget(org.id, payload)

  assert exc.value.status_code == 409
  assert exc.value.code == "BUDGET_VERSION_CONFLICT"

@pytest.mark.asyncio
async def test_save_budget_rejects_currency_mismatch(
  budget_service: BudgetService,
  budget_admin_context,
  project_factory,
):
  org = budget_admin_context.organization
  assert org.currency == "PKR"

  project = await project_factory(organization_id=org.id)
  payload = _save_payload(project.id, currency="USD")

  with pytest.raises(TraceException) as exc:
    await budget_service.save_budget(org.id, payload)

  assert exc.value.status_code == 422
  assert exc.value.code == "CURRENCY_MISMATCH"

@pytest.mark.asyncio
async def test_save_budget_uses_organization_currency_when_omitted(
  budget_service: BudgetService,
  budget_admin_context,
  project_factory,
):
  org = budget_admin_context.organization
  project = await project_factory(organization_id=org.id)

  payload = _save_payload(project.id, currency=None)

  result = await budget_service.save_budget(org.id, payload)
  assert result.currency == org.currency

@pytest.mark.asyncio
async def test_list_budgets_returns_empty_when_project_id_omitted(
  budget_service: BudgetService,
  budget_admin_context,
):
  result = await budget_service.list_budgets(
    budget_admin_context.organization.id, project_id=None
  )
  assert result == []

@pytest.mark.asyncio
async def test_list_budgets_returns_budget_for_valid_project(
  budget_service: BudgetService,
  budget_admin_context,
  project_factory,
  make_budget,
):
  org = budget_admin_context.organization
  project = await project_factory(organization_id=org.id)
  await make_budget(organization=org, project=project)

  result = await budget_service.list_budgets(org.id, project_id=project.id)
  assert len(result) == 1
  assert result[0].project_id == project.id

@pytest.mark.asyncio
async def test_get_organization_summary_includes_currency_and_totals(
  budget_service: BudgetService,
  budget_admin_context,
  project_factory,
  make_budget,
):
  org = budget_admin_context.organization
  p1 = await project_factory(organization_id=org.id)
  p2 = await project_factory(organization_id=org.id)

  await make_budget(organization=org, project=p1, approved_amount=Decimal("1000"))
  await make_budget(organization=org, project=p2, approved_amount=Decimal("2500"))
  summary = await budget_service.get_organization_summary(org.id)
  assert summary["budget_count"] == 2
  assert summary["total_approved_amount"] == Decimal("3500")
  assert summary["currency"] == org.currency