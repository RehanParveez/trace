from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

class CashFlowDirection(str, Enum):
  IN = "IN"
  OUT = "OUT"

class CashFlowCategory(str, Enum):
  PROCUREMENT = "PROCUREMENT"
  LABOUR = "LABOUR"
  SUBCONTRACTOR = "SUBCONTRACTOR"
  CLIENT_COLLECTION = "CLIENT_COLLECTION"

@dataclass
class CashFlowLineItem:
  event_date: date
  category: CashFlowCategory
  direction: CashFlowDirection
  amount: Decimal
  description: str
  is_estimated_timing: bool  
  is_overdue: bool = False

@dataclass
class WeeklyBucket:
  week_start: date
  week_end: date
  total_inflow: Decimal
  total_outflow: Decimal
  net_change: Decimal
  cumulative_net: Decimal
  projected_balance: Decimal | None

@dataclass
class HorizonSummary:
  days: int
  cumulative_net: Decimal
  projected_balance: Decimal | None

@dataclass
class CashFlowForecastResult:
  as_of_date: date
  horizon_days: int
  weekly_buckets: list[WeeklyBucket]
  summaries: dict[int, HorizonSummary] 

def clamp_to_as_of(event_date: date, as_of: date) -> tuple[date, bool]:
  if event_date < as_of:
    return as_of, True
  return event_date, False

def build_forecast(
  line_items: list[CashFlowLineItem],
  as_of: date,
  horizon_days: int,
  starting_cash_balance: Decimal | None,
) -> CashFlowForecastResult:
  bucket_count = max((horizon_days + 6) // 7, 1)
  buckets: list[WeeklyBucket] = []
  cumulative = Decimal("0")
  running_balance = starting_cash_balance

  for i in range(bucket_count):
    week_start = as_of + timedelta(days=i * 7)
    week_end = min(week_start + timedelta(days=6), as_of + timedelta(days=horizon_days - 1))

    inflow = Decimal("0")
    outflow = Decimal("0")
    for item in line_items:
      if week_start <= item.event_date <= week_end:
        if item.direction == CashFlowDirection.IN:
          inflow += item.amount
        else:
          outflow += item.amount

    net = inflow - outflow
    cumulative += net
    if running_balance is not None:
      running_balance = running_balance + net

    buckets.append(WeeklyBucket(
      week_start=week_start, week_end=week_end, total_inflow=inflow, total_outflow=outflow,
      net_change=net, cumulative_net=cumulative, projected_balance=running_balance,
    ))

  summaries: dict[int, HorizonSummary] = {}
  for marker_days in (30, 60, 90):
    if marker_days > horizon_days:
      continue
    marker_date = as_of + timedelta(days=marker_days - 1)
    matching_bucket = next((b for b in buckets if b.week_start <= marker_date <= b.week_end), buckets[-1])
    summaries[marker_days] = HorizonSummary(
      days=marker_days, cumulative_net=matching_bucket.cumulative_net,
      projected_balance=matching_bucket.projected_balance,
    )

  return CashFlowForecastResult(
    as_of_date=as_of, horizon_days=horizon_days, weekly_buckets=buckets, summaries=summaries,
  )