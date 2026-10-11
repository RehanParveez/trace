from __future__ import annotations
from decimal import Decimal
from datetime import date, timedelta
import calendar
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.cash_flow.repository import CashFlowRepository
from uuid import UUID
from app.modules.cash_flow.models import CashFlowSettings
from app.modules.identity.models import Organization
from app.modules.cash_flow.forecasting import CashFlowCategory, CashFlowDirection, CashFlowLineItem, build_forecast, clamp_to_as_of
from app.modules.cash_flow.schemas import CashFlowSettingsUpdateRequest
from app.shared.timeutils import today_local, to_local_date

TAX_DUE_DAY = 15         
WAGES_PAYDAY_LAG_DAYS = 7   
ZERO = Decimal("0")

def _month_bounds(day: date) -> tuple[date, date]:
  return day.replace(day=1), day.replace(day=calendar.monthrange(day.year, day.month)[1])

def _due_date_for_month(month_start: date) -> date:
  """15th of the month after `month_start`'s month."""
  year, month = (month_start.year + 1, 1) if month_start.month == 12 else (month_start.year, month_start.month + 1)
  return date(year, month, TAX_DUE_DAY)

class CashFlowService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = CashFlowRepository(session)

  async def get_settings(self, organization_id: UUID) -> CashFlowSettings:
    return await self.repo.get_or_create_settings(organization_id)

  async def update_settings(self, organization_id: UUID, payload: CashFlowSettingsUpdateRequest) -> CashFlowSettings:
    settings = await self.repo.get_or_create_settings(organization_id)
    for field_name in (
      "procurement_payment_days", "subcontractor_payment_days", "client_collection_days", "labour_lookback_days",
      "expected_client_wht_percentage",
    ):
      value = getattr(payload, field_name)
      if value is not None:
        setattr(settings, field_name, value)
    await self.session.commit()
    return settings

  async def get_forecast(
    self, organization_id: UUID, project_id: UUID | None, horizon_days: int, starting_cash_balance: Decimal | None,
  ) -> dict:
    settings = await self.repo.get_or_create_settings(organization_id)
    organization = await self.session.get(Organization, organization_id)
    currency = organization.currency if organization else "PKR"
    today = today_local()
    horizon_end = today + timedelta(days=horizon_days - 1)
    limitations: list[str] = []
    line_items: list[CashFlowLineItem] = []

    payment_days = settings.procurement_payment_days
    for delivery, request in await self.repo.get_delivery_payables(organization_id, project_id, today - timedelta(days=payment_days)):
      amount = delivery.amount
      if amount is None and request.estimated_amount is not None and request.quantity > 0:
        amount = (Decimal(str(request.estimated_amount)) * delivery.quantity / request.quantity).quantize(Decimal("0.01"))
      if amount is None or amount <= 0:
        continue
      raw_date = delivery.received_date + timedelta(days=payment_days)
      event_date, is_overdue = clamp_to_as_of(raw_date, today)
      supplier = delivery.supplier_name or request.supplier_name
      line_items.append(CashFlowLineItem(
        event_date=event_date, category=CashFlowCategory.PROCUREMENT, direction=CashFlowDirection.OUT,
        amount=Decimal(str(amount)), is_estimated_timing=True, is_overdue=is_overdue,
        description=f"Supplier payment: {request.material_name}" + (f" ({supplier})" if supplier else ""),
      ))

    pending = await self.repo.get_pending_procurement(organization_id, project_id)
    delivered = await self.repo.get_delivered_by_request(organization_id, [r.id for r in pending])
    skipped_no_amount = 0
    for request in pending:
      if request.estimated_amount is None:
        skipped_no_amount += 1
        continue
      quantity = Decimal(str(request.quantity))
      remaining_share = (quantity - delivered.get(request.id, ZERO)) / quantity if quantity > 0 else ZERO
      remaining_amount = (Decimal(str(request.estimated_amount)) * max(remaining_share, ZERO)).quantize(Decimal("0.01"))
      if remaining_amount <= 0:
        continue
      base_date = request.needed_by_date if request.needed_by_date is not None else to_local_date(request.created_at)
      event_date, is_overdue = clamp_to_as_of(base_date + timedelta(days=payment_days), today)
      line_items.append(CashFlowLineItem(
        event_date=event_date, category=CashFlowCategory.PROCUREMENT, direction=CashFlowDirection.OUT,
        amount=remaining_amount, description=f"Procurement: {request.material_name} (not yet delivered)",
        is_estimated_timing=True, is_overdue=is_overdue,
      ))
    if skipped_no_amount > 0:
      limitations.append(
        f"{skipped_no_amount} pending procurement request(s) have no estimated amount and are excluded from this forecast."
      )
    limitations.append(
      f"Trace does not record supplier payments. A delivery is assumed unpaid for {payment_days} day(s) after it "
      "arrives and then treated as paid, so older deliveries do not appear here even if a supplier is still waiting."
    )

    wages_due = await self.repo.get_labour_wages_due(organization_id, project_id)
    if wages_due > 0:
      line_items.append(CashFlowLineItem(
        event_date=today + timedelta(days=min(WAGES_PAYDAY_LAG_DAYS, horizon_days - 1)), category=CashFlowCategory.LABOUR,
        direction=CashFlowDirection.OUT, amount=wages_due, description="Labour wages earned and not yet paid",
        is_estimated_timing=True,
      ))
    lookback_start = today - timedelta(days=settings.labour_lookback_days)
    labour_total = await self.repo.get_labour_run_rate_total(organization_id, project_id, lookback_start, today)
    labour_daily_run_rate = (labour_total / settings.labour_lookback_days) if settings.labour_lookback_days > 0 else ZERO
    if labour_daily_run_rate == 0:
      limitations.append("No recent labour attendance data was found, so no labour cost is projected forward.")
    else:
      bucket_count = max((horizon_days + 6) // 7, 1)
      for i in range(bucket_count):
        week_start = today + timedelta(days=i * 7)
        days_in_week = min(7, horizon_days - i * 7)
        if days_in_week <= 0:
          break
        line_items.append(CashFlowLineItem(
          event_date=week_start, category=CashFlowCategory.LABOUR, direction=CashFlowDirection.OUT,
          amount=(labour_daily_run_rate * days_in_week).quantize(Decimal("0.01")),
          description=f"Labour (projected run-rate, {days_in_week} day(s))",
          is_estimated_timing=True,
        ))

    for bill, settled_so_far in await self.repo.get_outstanding_subcontractor_bills(organization_id, project_id):
      outstanding = bill.net_payable + bill.sales_tax_amount - settled_so_far
      if outstanding <= 0:
        continue
      issued_date = to_local_date(bill.issued_at) if bill.issued_at else today
      event_date, is_overdue = clamp_to_as_of(issued_date + timedelta(days=settings.subcontractor_payment_days), today)
      line_items.append(CashFlowLineItem(
        event_date=event_date, category=CashFlowCategory.SUBCONTRACTOR, direction=CashFlowDirection.OUT,
        amount=outstanding, description=f"Subcontractor bill #{bill.bill_number}",
        is_estimated_timing=True, is_overdue=is_overdue,
      ))

    wht_pct = Decimal(str(settings.expected_client_wht_percentage or 0))
    expected_client_wht_total = ZERO
    for bill in await self.repo.get_outstanding_running_bills(organization_id, project_id):
      outstanding = bill.net_payable + bill.sales_tax_amount - (bill.collected_amount or ZERO)
      if outstanding <= 0:
        continue
      withheld = (outstanding * wht_pct / Decimal("100")).quantize(Decimal("0.01"))
      expected_client_wht_total += withheld
      issued_date = to_local_date(bill.issued_at) if bill.issued_at else today
      event_date, is_overdue = clamp_to_as_of(issued_date + timedelta(days=settings.client_collection_days), today)
      line_items.append(CashFlowLineItem(
        event_date=event_date, category=CashFlowCategory.CLIENT_COLLECTION, direction=CashFlowDirection.IN,
        amount=outstanding - withheld,
        description=f"Client running bill #{bill.bill_number}" + (f" (after {wht_pct}% tax withheld)" if withheld > 0 else ""),
        is_estimated_timing=True, is_overdue=is_overdue,
      ))
    suggested = await self.repo.get_observed_client_wht_percentage(organization_id, project_id)
    if wht_pct == 0 and suggested is not None:
      limitations.append(
        f"Clients have withheld about {suggested}% of your past receipts, but the expected withholding in Cash Flow "
        "Settings is 0%. Until you set it, expected client receipts here are higher than the cash you will actually get."
      )

    this_start, this_end = _month_bounds(today)
    prev_start, prev_end = _month_bounds(this_start - timedelta(days=1))
    for month_start, month_end in ((prev_start, prev_end), (this_start, this_end)):
      due = _due_date_for_month(month_start)
      if due < today or due > horizon_end:
        continue
      sales_tax_net = await self.repo.get_sales_tax_net_for_month(organization_id, project_id, month_start, month_end)
      if sales_tax_net > 0:
        line_items.append(CashFlowLineItem(
          event_date=due, category=CashFlowCategory.TAX, direction=CashFlowDirection.OUT, amount=sales_tax_net,
          description=f"Sales tax payable for {month_start.strftime('%B %Y')} (charged to clients less charged by subcontractors)",
          is_estimated_timing=False,
        ))
      wht_total = await self.repo.get_wht_deducted_for_month(organization_id, project_id, month_start, month_end)
      if wht_total > 0:
        line_items.append(CashFlowLineItem(
          event_date=due, category=CashFlowCategory.TAX, direction=CashFlowDirection.OUT, amount=wht_total,
          description=f"Withholding tax to deposit for {month_start.strftime('%B %Y')}",
          is_estimated_timing=False,
        ))
    limitations.append(
      "Sales tax and withholding tax are shown as due on the 15th of the following month, based on what Trace has "
      "recorded. Trace does not record when you actually file or deposit, so months whose due date has passed are assumed settled."
    )
    limitations.append(
      "Retention held back by clients is not in this forecast; it only becomes cash when you plan and record its release."
    )
    limitations.append(
      "This is a projection built from payment-terms assumptions (see Cash Flow Settings), not a bank feed or a "
      "guarantee. Trace does not track your actual bank balance -- enter a starting balance above to see a "
      "projected balance line, or leave it blank to see net movement only."
    )

    result = build_forecast(line_items, today, horizon_days, starting_cash_balance)

    return {
      "as_of_date": result.as_of_date, "horizon_days": result.horizon_days, "currency": currency,
      "starting_cash_balance": starting_cash_balance,
      "weekly_buckets": [
        {
          "week_start": b.week_start, "week_end": b.week_end, "total_inflow": b.total_inflow,
          "total_outflow": b.total_outflow, "net_change": b.net_change, "cumulative_net": b.cumulative_net,
          "projected_balance": b.projected_balance,
        }
        for b in result.weekly_buckets
      ],
      "summaries": {
        days: {"days": s.days, "cumulative_net": s.cumulative_net, "projected_balance": s.projected_balance}
        for days, s in result.summaries.items()
      },
      "line_items": [
        {
          "event_date": li.event_date, "category": li.category.value, "direction": li.direction.value,
          "amount": li.amount, "description": li.description,
          "is_estimated_timing": li.is_estimated_timing, "is_overdue": li.is_overdue,
        }
        for li in sorted(line_items, key=lambda x: x.event_date)
      ],
      "assumptions": settings, "labour_daily_run_rate": labour_daily_run_rate,
      "expected_client_wht_total": expected_client_wht_total, "suggested_client_wht_percentage": suggested,
      "limitations": limitations,
    }