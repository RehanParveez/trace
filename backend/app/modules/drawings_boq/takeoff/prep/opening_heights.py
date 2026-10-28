from __future__ import annotations

MIN_LABELS = 3            
AGREE_MM = 25.0           
MIN_SHARE = 0.6           
KINDS = ("DOOR", "WINDOW")

def sheet_labels(words: list) -> dict:
  """The heights (mm) printed in the D= / W= labels of a sheet, {"DOOR": [...], "WINDOW": [...]}; empty when the sheet prints none. A ventilator (V=) does not vote for the window height."""
  from app.modules.drawings_boq.takeoff.extract import opening_labels as OL
  got = OL.read(words, False)["labels"]
  out: dict = {}
  for lab in got:
    if lab.get("h_mm") and not lab.get("ventilator"):
      out.setdefault(lab["kind"], []).append(round(float(lab["h_mm"]), 1))
  return out

def _plan_sheet(meta: dict) -> bool:
  from app.modules.drawings_boq.takeoff.extract import sheet_identity as SID
  if (meta.get("title") or {}).get("composite"):
    return False
  return SID.read_as(meta.get("identity")) == "PLAN_ITEMS"

def gather(sheets: list) -> dict:
  pool: dict = {k: [] for k in KINDS}
  for s in sheets:
    meta = getattr(s, "prep_meta", None) or {}
    got = meta.get("opening_labels")
    if not got or not _plan_sheet(meta):
      continue
    for k in KINDS:
      pool[k].extend(float(h) for h in got.get(k) or [])
  return {k: sorted(v) for k, v in pool.items()}

def merge(own: dict | None, other: dict | None) -> dict:
  return {k: sorted(list((own or {}).get(k) or []) + list((other or {}).get(k) or [])) for k in KINDS}

def decide(pool: dict | None) -> dict:
  out: dict = {}
  for kind in KINDS:
    hs = sorted(float(h) for h in (pool or {}).get(kind) or [])
    n = len(hs)
    if n < MIN_LABELS:
      continue
    best: list = []
    
    for i in range(n):
      j = i
      while j < n and hs[j] - hs[i] <= AGREE_MM:
        j += 1
      if j - i > len(best):
        best = hs[i:j]
    if len(best) >= MIN_LABELS and len(best) / n >= MIN_SHARE:
      mid = len(best) // 2
      med = best[mid] if len(best) % 2 else (best[mid - 1] + best[mid]) / 2.0
      out[kind] = {"height_mm": round(med, 1), "n": len(best), "of": n, "basis": "SET_LABELS"}
  return out
