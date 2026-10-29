from __future__ import annotations

A3_LONG_PT = 1190.55   

def factor(page_wh: tuple) -> float:
  w, h = float(page_wh[0]), float(page_wh[1])
  return max(w, h, 1.0) / A3_LONG_PT
