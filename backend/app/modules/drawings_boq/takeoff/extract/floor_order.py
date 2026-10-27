from __future__ import annotations
from collections import Counter

JACCARD_MIN = 0.6                 
MIN_SIZES = 3                     
LADDER = ("GROUND", "FIRST", "SECOND", "THIRD", "FOURTH")
ORDER = ["FOUNDATION", "BASEMENT", "GROUND", "MEZZANINE", "FIRST", "SECOND", "THIRD", "FOURTH", "TYPICAL", "ROOF"]
PLAN_ROLES = (None, "PLAN", "UNKNOWN", "STRUCTURAL")

def _eligible(sheet: dict) -> bool:
  ident, clues, title = sheet.get("identity") or {}, sheet.get("clues") or {}, sheet.get("title") or {}
  if title.get("composite") or ident.get("basis") == "PERSON" and ident.get("read_as") not in (None, "PLAN_ITEMS"):
    return False
  if ident.get("role") not in PLAN_ROLES or ident.get("plan_kind") in ("FRAMING", "FOUNDATION") or ident.get("read_as") not in (None, "PLAN_ITEMS", "SYMBOLS_ONLY"):
    return False
  return len(clues.get("sizes") or []) >= MIN_SIZES

def jaccard(a: list, b: list) -> float:
  ca, cb = Counter(a), Counter(b)
  union = sum((ca | cb).values())
  return sum((ca & cb).values()) / union if union else 0.0

def _groups(sheets: list) -> list:
  parent = list(range(len(sheets)))
  def find(i: int) -> int:
    while parent[i] != i:
      parent[i] = parent[parent[i]]
      i = parent[i]
    return i
  for i in range(len(sheets)):
    for j in range(i + 1, len(sheets)):
      if jaccard(sheets[i]["clues"]["sizes"], sheets[j]["clues"]["sizes"]) >= JACCARD_MIN:
        parent[find(j)] = find(i)
  out: dict = {}
  for i, s in enumerate(sheets):
    out.setdefault(find(i), []).append(s)
  return sorted(out.values(), key=lambda g: min(s["page_no"] for s in g))

def assign(sheets: list) -> dict:
  named_all = {(s.get("title") or {}).get("level_hint") for s in sheets if (s.get("title") or {}).get("level_hint") and not (s.get("title") or {}).get("composite")}
  plans = [s for s in sheets if _eligible(s)]
  out: dict = {}
  pending: list = []
  taken = set(named_all)
  
  for gi, group in enumerate(_groups(plans), start=1):
    names = {(s.get("title") or {}).get("level_hint") for s in group if (s.get("title") or {}).get("level_hint")}
    unnamed = [s for s in group if not (s.get("title") or {}).get("level_hint")]
    if not unnamed or len(names) > 1:
      continue
    if not names and all((s.get("identity") or {}).get("plan_kind") == "OVERLAY" for s in group):
      continue
    if names:
      floor, reason = next(iter(names)), "SHARES_ROOM_SIZES"
    else:
      ground = sum(int((s["clues"] or {}).get("ground_words") or 0) for s in group)
      roof = sum(int((s["clues"] or {}).get("roof_words") or 0) for s in group)
      beds = sum(int((s["clues"] or {}).get("bed_words") or 0) for s in group)
      if ground > 0 and "GROUND" not in taken:
        floor, reason = "GROUND", "PORCH_OR_LAWN_LABELS"
      elif roof > 0 and beds == 0 and "ROOF" not in taken:
        floor, reason = "ROOF", "MUMTY_OR_STAIR_TOWER_LABELS"
      else:
        pending.append((gi, unnamed))
        continue
      taken.add(floor)
    for s in unnamed:
      out[s["sheet_id"]] = {"floor": floor, "reason": reason, "group": gi, "pages": sorted(x["page_no"] for x in group)}
      
  lowest = min((ORDER.index(f) for f in named_all if f in ORDER), default=-1)
  free = [f for f in LADDER if ORDER.index(f) > lowest and f not in taken]
  for gi, unnamed in pending:
    if not free:
      break
    floor = free.pop(0)
    for s in unnamed:
      out[s["sheet_id"]] = {"floor": floor, "reason": "PAGE_ORDER", "group": gi, "pages": sorted(x["page_no"] for x in unnamed)}
  return out
