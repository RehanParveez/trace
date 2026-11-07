from __future__ import annotations

def carry_down(rows: list) -> dict:
  last: dict = {}
  
  carried = unknown = 0
  for r in rows:
    block = (r.sheet, r.member)
    if r.dia is not None:
      last[block] = (r.dia, r.sr)
      continue
    if block in last:
      dia, sr = last[block]
      r.dia = dia
      r.issues.append(f"dia:carried from sr {sr}")
      carried += 1
    else:
      r.issues.append("dia:unknown")
      unknown += 1
  return {"carried": carried, "unknown": unknown}
