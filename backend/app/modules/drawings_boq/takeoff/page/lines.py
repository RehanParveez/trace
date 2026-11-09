from __future__ import annotations
from app.modules.drawings_boq.takeoff.page import settings as S

def runs(items: list, h: float) -> list:
  rows: list = []
  for i, w in sorted(items, key=lambda p: -(p[1].v0 + p[1].v1) / 2):
    y = (w.v0 + w.v1) / 2
    for r in rows:
      if abs(r["y"] - y) <= 0.4 * h:
        r["words"].append((i, w))
        break
    else:
      rows.append({"y": y, "words": [(i, w)]})
      
  out: list = []
  gap = S.get("notes", "word_gap") * h
  for r in rows:
    r["words"].sort(key=lambda p: p[1].u0)
    cur = [r["words"][0]]
    for p in r["words"][1:]:
      if p[1].u0 - cur[-1][1].u1 > gap:
        out.append({"y": r["y"], "words": cur})
        cur = [p]
      else:
        cur.append(p)
    out.append({"y": r["y"], "words": cur})
  for r in out:
    r["u0"], r["u1"] = r["words"][0][1].u0, max(p[1].u1 for p in r["words"])
  return out
