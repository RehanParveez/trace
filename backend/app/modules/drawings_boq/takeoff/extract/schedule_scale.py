from __future__ import annotations
import statistics

TOL = 0.12               
MIN_PAIRS = 3            
MIN_SHARE = 0.6          

def verdict(pairs: list) -> dict:
  fs = [float(p["factor"]) for p in pairs if p.get("factor") and float(p["factor"]) > 0]
  kinds = sorted({p["kind"] for p in pairs})
  
  if len(fs) < MIN_PAIRS:
    return {"status": "TOO_FEW", "pairs": len(fs), "kinds": kinds}
  med = statistics.median(fs)
  agree = [f for f in fs if abs(f / med - 1.0) <= TOL]
  base = {"pairs": len(fs), "agree": len(agree), "factor": round(statistics.median(agree), 4) if agree else round(med, 4), "kinds": kinds}
  if len(agree) < MIN_PAIRS or len(agree) < MIN_SHARE * len(fs):
    return {"status": "MIXED", **base}
  return {"status": "SETTLED" if abs(base["factor"] - 1.0) <= TOL else "DISAGREES", **base}
