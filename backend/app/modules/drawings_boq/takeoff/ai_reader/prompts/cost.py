from __future__ import annotations
import json
from app.core.config import settings

MILLION = 1_000_000

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

def summarise(rows: list, table: dict | None = None, usd_to_pkr: float | None = None) -> dict:
  table = prices() if table is None else table
  fx = float(settings.ai_usd_to_pkr if usd_to_pkr is None else usd_to_pkr)
  total = {"requests": 0, "with_tokens": 0, "input_tokens": 0, "output_tokens": 0, "seconds": 0.0, "usd": 0.0, "pkr": 0.0, "unpriced_models": [], "by_model": {}}
  unpriced: set = set()
  
  for r in rows:
    model = str(r.get("model") or "")
    inp, out = r.get("input_tokens"), r.get("output_tokens")
    cost = usd(model, inp, out, table)
    if model and model not in table:
      unpriced.add(model)
    slot = total["by_model"].setdefault(model, {"requests": 0, "input_tokens": 0, "output_tokens": 0, "seconds": 0.0, "usd": 0.0, "pkr": 0.0})
    for bucket in (total, slot):
      bucket["requests"] += 1
      bucket["input_tokens"] += int(inp or 0)
      bucket["output_tokens"] += int(out or 0)
      bucket["seconds"] += float(r.get("seconds") or 0.0)
      bucket["usd"] += cost
      bucket["pkr"] += cost * fx
    if inp is not None and out is not None:
      total["with_tokens"] += 1
  total["unpriced_models"] = sorted(unpriced)
  
  for bucket in [total, *total["by_model"].values()]:
    bucket["seconds"] = round(bucket["seconds"], 2)
    bucket["usd"] = round(bucket["usd"], 6)
    bucket["pkr"] = round(bucket["pkr"], 4)
  return total
