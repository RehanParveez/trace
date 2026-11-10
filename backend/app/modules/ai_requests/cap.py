from __future__ import annotations
import datetime
import json
from app.core.config import settings

CAP_REACHED, CAP_NO_PRICE = "AI_CAP_REACHED", "AI_CAP_NO_PRICE"
MILLION = 1_000_000
CALL_INPUT_TOKENS = 4000

def prices() -> dict:
  try:
    raw = json.loads(settings.ai_price_usd_per_million or "{}")
  except json.JSONDecodeError:
    return {}
  return {str(k): (float(v[0]), float(v[1])) for k, v in raw.items() if isinstance(v, (list, tuple)) and len(v) == 2}

def usd(model: str, input_tokens, output_tokens, table: dict | None = None) -> float:
  rate = (table if table is not None else prices()).get(str(model))
  if rate is None:
    return 0.0
  return (int(input_tokens or 0) * rate[0] + int(output_tokens or 0) * rate[1]) / MILLION

def month_start(now: datetime.datetime | None = None) -> datetime.datetime:
  now = now or datetime.datetime.now(datetime.timezone.utc)
  return datetime.datetime(now.year, now.month, 1, tzinfo=datetime.timezone.utc)

def in_month(day: str | None, now: datetime.datetime | None = None) -> bool:
  if not day:
    return True
  return str(day)[:7] == month_start(now).strftime("%Y-%m")

def spent_usd(rows: list, table: dict | None = None) -> float:
  table = prices() if table is None else table
  return sum(usd(m, i, o, table) for m, i, o in rows)

def next_call_usd(model: str, max_tokens: int, table: dict | None = None) -> float | None:
  table = prices() if table is None else table
  if str(model) not in table:
    return None
  return usd(model, CALL_INPUT_TOKENS, max_tokens, table)

def check(spent: float, model: str, max_tokens: int, cap_usd: float | None = None, table: dict | None = None) -> str | None:
  cap = float(settings.ai_monthly_cap_usd if cap_usd is None else cap_usd)
  nxt = next_call_usd(model, max_tokens, table)
  if nxt is None:
    return f"{CAP_NO_PRICE}: {model} has no price in AI_PRICE_USD_PER_MILLION, so its cost cannot be held under the monthly cap of {cap:g} USD."
  if spent + nxt > cap:
    return f"{CAP_REACHED}: {spent:.4f} USD spent this month and the next call may cost up to {nxt:.4f} USD, which would pass the monthly cap of {cap:g} USD (AI_MONTHLY_CAP_USD)."
  return None
