from __future__ import annotations

SET_ASIDE = "set_aside"
BY = "FLOOR_COMBINE"
STAMP = "floor_union"
SAME, ADDED, DUPLICATE = "SAME", "ADDED", "DUPLICATE_OF"
DERIVED = "DERIVED_FROM_OTHER_SHEET"

def combined_away(row) -> bool:
  return row.decision == "REJECTED" and ((row.facts or {}).get(SET_ASIDE) or {}).get("by") == BY

def by_hand(row) -> bool:
  return row.decision == "REJECTED" and not combined_away(row)

def pool(rows: list) -> list:
  return [r for r in rows if not by_hand(r)]

def _stamp(row, value: dict | None) -> bool:
  cur = (row.facts or {}).get(STAMP)
  if cur == value:
    return False
  f = dict(row.facts or {})
  if value is None:
    f.pop(STAMP, None)
  else:
    f[STAMP] = value
  row.facts = f
  return True

def decide(union, *, floor: str, primary_page: int, secondary_page: int) -> dict:
  reject: list = []
  restore: list = []
  blocked: list = []
  changed: set = set()
  same = added = derived = 0

  def stamp(row, value) -> None:
    if _stamp(row, value):
      changed.add(str(row.id))
  for pair in union.pairs:
    p, s = pair.primary, pair.secondary
    same += 1
    other = int(getattr(s, "count", 1) or 1)
    mine = int(getattr(p, "count", 1) or 1)
    
    if pair.how != "ALONG_WALL":
      stamp(p, {"role": SAME, "other_page": secondary_page, "other_count": other, "count": mine, "how": pair.how, "floor": floor})
    if combined_away(s) or s.decision == "NEW":
      if s.decision == "NEW":
        reject.append((s, {"page_no": primary_page, "paired_with": str(p.id), "how": pair.how}))
      stamp(s, {"role": DUPLICATE, "page": primary_page, "how": pair.how, "floor": floor})
    elif s.decision == "ACCEPTED" and p.decision == "NEW":
      reject.append((p, {"page_no": secondary_page, "paired_with": str(s.id), "how": pair.how}))
      stamp(p, {"role": DUPLICATE, "page": secondary_page, "how": pair.how, "floor": floor})
    elif s.decision == "ACCEPTED" and p.decision == "ACCEPTED":
      blocked.append({"floor": floor, "code": "FLOOR_BOTH_ACCEPTED", "ids": [str(p.id), str(s.id)]})
      
  for s in union.only_secondary:
    if (s.facts or {}).get("derived_from") and s.decision != "ACCEPTED":
      if s.decision == "NEW":
        reject.append((s, {"page_no": primary_page, "paired_with": None, "how": DERIVED}))
      derived += 1
      stamp(s, {"role": DUPLICATE, "page": primary_page, "how": DERIVED, "floor": floor})
      continue
    added += 1
    
    if combined_away(s):
      restore.append(s)
    stamp(s, {"role": ADDED, "page": secondary_page, "floor": floor})
  for p in union.only_primary:
    if combined_away(p):
      restore.append(p)
    stamp(p, None)
  return {"reject": reject, "restore": restore, "stamped": len(changed), "blocked": blocked, "same": same, "added": added, "derived_set_aside": derived}

def apply_decisions(plan: dict, *, user_id, now) -> int:
  n = 0
  for row, why in plan["reject"]:
    if row.decision == "REJECTED":
      continue
    row.decision, row.decided_by_user_id, row.decided_at = "REJECTED", user_id, now
    row.facts = {**(row.facts or {}), SET_ASIDE: {"by": BY, **why}}
    n += 1
    
  for row in plan["restore"]:
    if not combined_away(row):
      continue
    row.decision, row.decided_by_user_id, row.decided_at = "NEW", None, None
    row.facts = {k: v for k, v in (row.facts or {}).items() if k != SET_ASIDE}
    n += 1
  return n
