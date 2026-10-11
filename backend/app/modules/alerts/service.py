from __future__ import annotations
from decimal import Decimal
from app.modules.identity.enums import PermissionKey
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.cash_flow.repository import CashFlowRepository
from uuid import UUID
from datetime import timedelta
from sqlalchemy import select, func
from app.modules.bank_guarantees.models import BankGuarantee, BankGuaranteeStatus
from app.shared.timeutils import today_local, to_local_date
from app.modules.procurement.models import ProcurementRequest, ProcurementStatus
from app.modules.budgets.models import Budget
from app.modules.budgets.service import BudgetService
from app.modules.cash_flow.service import TAX_DUE_DAY, _due_date_for_month, _month_bounds

ZERO = Decimal("0")
GUARANTEE_WARNING_DAYS = 30
TAX_WARNING_DAYS = 7
BUDGET_WARNING_PERCENT = 90
BUDGET_CHECK_LIMIT = 40

KIND_PERMISSION = {
  "CLIENT_BILLS_OVERDUE": PermissionKey.RUNNING_BILL_READ,
  "SUBCONTRACTOR_BILLS_OVERDUE": PermissionKey.SUBCONTRACTOR_READ,
  "GUARANTEES_EXPIRING": PermissionKey.BANK_GUARANTEE_READ,
  "TAX_DUE": PermissionKey.SALES_TAX_READ,
  "PROCUREMENT_OVERDUE": PermissionKey.PROCUREMENT_READ,
  "BUDGETS_NEAR_LIMIT": PermissionKey.BUDGET_READ,
}

class AlertsService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.cash = CashFlowRepository(session)

  async def get_attention(
    self, organization_id: UUID, permissions: set[str] | None = None, project_ids: set[UUID] | None = None,
  ) -> list[dict]:
    today = today_local()
    settings = await self.cash.get_or_create_settings(organization_id)
    items: list[dict] = []

    def allowed(kind: str) -> bool:
      return permissions is None or KIND_PERMISSION[kind] in permissions

    def in_scope(pid: UUID) -> bool:
      return project_ids is None or pid in project_ids

    if allowed("CLIENT_BILLS_OVERDUE"):
      count, amount = 0, ZERO
      for bill in await self.cash.get_outstanding_running_bills(organization_id, None):
        if not in_scope(bill.project_id) or bill.issued_at is None:
          continue
        outstanding = bill.net_payable + bill.sales_tax_amount - (bill.collected_amount or ZERO)
        if outstanding > 0 and to_local_date(bill.issued_at) + timedelta(days=settings.client_collection_days) < today:
          count += 1
          amount += outstanding
      if count:
        items.append({"kind": "CLIENT_BILLS_OVERDUE", "count": count, "amount": amount})

    if allowed("SUBCONTRACTOR_BILLS_OVERDUE"):
      count, amount = 0, ZERO
      for bill, settled in await self.cash.get_outstanding_subcontractor_bills(organization_id, None):
        if not in_scope(bill.project_id) or bill.issued_at is None:
          continue
        outstanding = bill.net_payable + bill.sales_tax_amount - settled
        if outstanding > 0 and to_local_date(bill.issued_at) + timedelta(days=settings.subcontractor_payment_days) < today:
          count += 1
          amount += outstanding
      if count:
        items.append({"kind": "SUBCONTRACTOR_BILLS_OVERDUE", "count": count, "amount": amount})

    if allowed("GUARANTEES_EXPIRING"):
      rows = (await self.session.execute(
        select(BankGuarantee.project_id, BankGuarantee.amount).where(
          BankGuarantee.organization_id == organization_id,
          BankGuarantee.status.in_([BankGuaranteeStatus.ACTIVE, BankGuaranteeStatus.RENEWED]),
          BankGuarantee.expiry_date <= today + timedelta(days=GUARANTEE_WARNING_DAYS),
        )
      )).all()
      rows = [r for r in rows if in_scope(r[0])]
      if rows:
        items.append({"kind": "GUARANTEES_EXPIRING", "count": len(rows), "amount": sum((Decimal(str(r[1])) for r in rows), ZERO)})

    if allowed("TAX_DUE") and project_ids is None:
      prev_start, prev_end = _month_bounds(today.replace(day=1) - timedelta(days=1))
      due = _due_date_for_month(prev_start)
      if today <= due <= today + timedelta(days=TAX_WARNING_DAYS):
        sales_tax = max(await self.cash.get_sales_tax_net_for_month(organization_id, None, prev_start, prev_end), ZERO)
        wht = await self.cash.get_wht_deducted_for_month(organization_id, None, prev_start, prev_end)
        if sales_tax + wht > 0:
          items.append({"kind": "TAX_DUE", "count": 1, "amount": sales_tax + wht})

    if allowed("PROCUREMENT_OVERDUE"):
      rows = (await self.session.execute(
        select(ProcurementRequest.project_id).where(
          ProcurementRequest.organization_id == organization_id,
          ProcurementRequest.status.in_([ProcurementStatus.APPROVED, ProcurementStatus.ORDERED]),
          ProcurementRequest.needed_by_date.is_not(None), ProcurementRequest.needed_by_date < today,
        )
      )).all()
      count = sum(1 for r in rows if in_scope(r[0]))
      if count:
        items.append({"kind": "PROCUREMENT_OVERDUE", "count": count, "amount": None})

    if allowed("BUDGETS_NEAR_LIMIT"):
      budget_projects = [
        pid for (pid,) in (await self.session.execute(
          select(Budget.project_id).where(Budget.organization_id == organization_id).limit(BUDGET_CHECK_LIMIT)
        )).all() if in_scope(pid)
      ]
      near = 0
      budgets = BudgetService(self.session)
      for pid in budget_projects:
        status = await budgets.get_status(
          organization_id, pid, include_expenses=True, include_labour=True, include_subcontracts=True, include_materials=True,
        )
        if status["used_percentage"] is not None and status["used_percentage"] >= BUDGET_WARNING_PERCENT:
          near += 1
      if near:
        items.append({"kind": "BUDGETS_NEAR_LIMIT", "count": near, "amount": None})

    return items