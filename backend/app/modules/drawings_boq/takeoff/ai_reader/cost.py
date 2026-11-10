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

def per_accepted(records: list, table: dict | None = None, usd_to_pkr: float | None = None) -> dict:
  table = prices() if table is None else table
  out: dict = {}
  for r in records:
    slot = out.setdefault(r["task"], {"accepted": 0, "review": 0, "escalated": 0, "reads": 0, "input_tokens": 0, "output_tokens": 0, "usd": 0.0, "pkr": 0.0, "unpriced_models": set()})
    fx = float(settings.ai_usd_to_pkr if usd_to_pkr is None else usd_to_pkr)
    slot["accepted"] += int(r.get("accepted") or 0)
    slot["review"] += int(r.get("review") or 0)
    slot["escalated"] += int(r.get("escalated") or 0)
    
    for read in r.get("reads") or []:
      model = str(read.get("model") or "")
      cost = usd(model, read.get("input_tokens"), read.get("output_tokens"), table)
      if model and model not in table:
        slot["unpriced_models"].add(model)
      slot["reads"] += 1
      slot["input_tokens"] += int(read.get("input_tokens") or 0)
      slot["output_tokens"] += int(read.get("output_tokens") or 0)
      slot["usd"] += cost
      slot["pkr"] += cost * fx
      
  for slot in out.values():
    n = slot["accepted"]
    slot["usd_per_accepted"] = round(slot["usd"] / n, 6) if n else None
    slot["pkr_per_accepted"] = round(slot["pkr"] / n, 4) if n else None
    slot["usd"], slot["pkr"] = round(slot["usd"], 6), round(slot["pkr"], 4)
    slot["unpriced_models"] = sorted(slot["unpriced_models"])
  return out

def by_set(records: list, table: dict | None = None, usd_to_pkr: float | None = None) -> dict:
  sets: dict = {}
  for r in records:
    sets.setdefault(str(r.get("set") or ""), []).append(r)
  return {name: per_accepted(rows, table, usd_to_pkr) for name, rows in sorted(sets.items())}

def lines(records: list, table: dict | None = None, usd_to_pkr: float | None = None) -> list:
  def fmt(task: str, s: dict) -> str:
    per = "no accepted answer" if s["usd_per_accepted"] is None else f"${s['usd_per_accepted']:.4f} (PKR {s['pkr_per_accepted']:.2f}) for each accepted answer"
    extra = f"; models without a price: {', '.join(s['unpriced_models'])}" if s["unpriced_models"] else ""
    return f"{task}: {s['accepted']} accepted, {s['review']} held for review, {s['escalated']} sent to the stronger model, {s['reads']} model calls, ${s['usd']:.4f} in all, {per}{extra}"

  out = [fmt(t, s) for t, s in sorted(per_accepted(records, table, usd_to_pkr).items())]
  for name, tasks in by_set(records, table, usd_to_pkr).items():
    out += [f"  set {name or '(none)'} - " + fmt(t, s) for t, s in sorted(tasks.items())]
  return out
