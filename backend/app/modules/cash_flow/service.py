from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.cash_flow.repository import CashFlowRepository
from app.modules.cash_flow.models import CashFlowSettings
from app.modules.cash_flow.forecasting import CashFlowCategory, CashFlowDirection, CashFlowLineItem, build_forecast, clamp_to_as_of
from uuid import UUID
from app.modules.cash_flow.schemas import CashFlowSettingsUpdateRequest
from datetime import date
from decimal import Decimal
from app.modules.identity.models import Organization

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
    today = date.today()
    limitations: list[str] = []

    line_items: list[CashFlowLineItem] = []

    procurement_requests = await self.repo.get_pending_procurement(organization_id, project_id)
    skipped_no_amount = 0
    for request in procurement_requests:
      if request.estimated_amount is None:
        skipped_no_amount += 1
        continue
      base_date = request.needed_by_date if request.needed_by_date is not None else request.created_at.date()
      raw_date = base_date + __import__("datetime").timedelta(days=settings.procurement_payment_days)
      event_date, is_overdue = clamp_to_as_of(raw_date, today)
      line_items.append(CashFlowLineItem(
        event_date=event_date, category=CashFlowCategory.PROCUREMENT, direction=CashFlowDirection.OUT,
        amount=Decimal(str(request.estimated_amount)), description=f"Procurement: {request.material_name}",
        is_estimated_timing=True, is_overdue=is_overdue,
      ))
    if skipped_no_amount > 0:
      limitations.append(
        f"{skipped_no_amount} pending procurement request(s) have no estimated amount and are excluded from this forecast."
      )
    limitations.append(
      "A procurement request is assumed unpaid until it moves to RECEIVED, at which point it drops out of this "
      "forecast. Trace does not currently track whether a received item has actually been paid."
    )

    lookback_start = today - __import__("datetime").timedelta(days=settings.labour_lookback_days)
    labour_total = await self.repo.get_labour_run_rate_total(organization_id, project_id, lookback_start, today)
    labour_daily_run_rate = (labour_total / settings.labour_lookback_days) if settings.labour_lookback_days > 0 else Decimal("0")
    if labour_daily_run_rate == 0:
      limitations.append("No recent labour attendance data was found, so no labour cost is projected forward.")
    else:
    
      bucket_count = max((horizon_days + 6) // 7, 1)
      for i in range(bucket_count):
        week_start = today + __import__("datetime").timedelta(days=i * 7)
        days_in_week = min(7, horizon_days - i * 7)
        if days_in_week <= 0:
          break
        line_items.append(CashFlowLineItem(
          event_date=week_start, category=CashFlowCategory.LABOUR, direction=CashFlowDirection.OUT,
          amount=(labour_daily_run_rate * days_in_week).quantize(Decimal("0.01")),
          description=f"Labour (projected run-rate, {days_in_week} day(s))",
          is_estimated_timing=True,
        ))

    for bill, paid_so_far in await self.repo.get_outstanding_subcontractor_bills(organization_id, project_id):
      total_due = bill.net_payable + bill.sales_tax_amount
      outstanding = total_due - paid_so_far
      if outstanding <= 0:
        continue
      issued_date = bill.issued_at.date() if bill.issued_at else today
      raw_date = issued_date + __import__("datetime").timedelta(days=settings.subcontractor_payment_days)
      event_date, is_overdue = clamp_to_as_of(raw_date, today)
      line_items.append(CashFlowLineItem(
        event_date=event_date, category=CashFlowCategory.SUBCONTRACTOR, direction=CashFlowDirection.OUT,
        amount=outstanding, description=f"Subcontractor bill #{bill.bill_number}",
        is_estimated_timing=True, is_overdue=is_overdue,
      ))

    for bill in await self.repo.get_outstanding_running_bills(organization_id, project_id):
      total_due = bill.net_payable + bill.sales_tax_amount
      outstanding = total_due - (bill.collected_amount or Decimal("0"))
      if outstanding <= 0:
        continue
      issued_date = bill.issued_at.date() if bill.issued_at else today
      raw_date = issued_date + __import__("datetime").timedelta(days=settings.client_collection_days)
      event_date, is_overdue = clamp_to_as_of(raw_date, today)
      line_items.append(CashFlowLineItem(
        event_date=event_date, category=CashFlowCategory.CLIENT_COLLECTION, direction=CashFlowDirection.IN,
        amount=outstanding, description=f"Client running bill #{bill.bill_number}",
        is_estimated_timing=True, is_overdue=is_overdue,
      ))

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
      "assumptions": settings, "labour_daily_run_rate": labour_daily_run_rate, "limitations": limitations,
    }