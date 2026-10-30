from __future__ import annotations

A3_LONG_PT = 1190.55   

SAME_SIZE = 0.005   

def factor(page_wh: tuple) -> float:
  w, h = float(page_wh[0]), float(page_wh[1])
  return max(w, h, 1.0) / A3_LONG_PT

def unit(page_wh: tuple) -> float:
  """factor(), but a sheet within SAME_SIZE of the reference counts as the reference: PDF page boxes are rounded to whole points, and a sheet that is the reference size must read exactly as it always did."""
  k = factor(page_wh)
  return 1.0 if abs(k - 1.0) <= SAME_SIZE else k

def of_box(box: tuple) -> float:
  return unit((box[2] - box[0], box[3] - box[1]))

class _CanonIndex:
  """The segment index of a page seen in the canonical frame (A3 long side = 1190.55 pt)."""

  def __init__(self, index, k: float):
    self._index, self._k = index, k

  def window(self, x0, y0, x1, y1, max_segments: int = 20000, include_curves: bool = True):
    k = self._k
    segs, total, truncated = self._index.window(x0 * k, y0 * k, x1 * k, y1 * k, max_segments=max_segments, include_curves=include_curves)
    return [(a / k, b / k, c / k, d / k, kind) for a, b, c, d, kind in segs], total, truncated

def canon_words(words: list, k: float) -> list:
  from dataclasses import replace
  return [replace(w, x0=w.x0 / k, y0=w.y0 / k, x1=w.x1 / k, y1=w.y1 / k, size=w.size / k, cx=w.cx / k, cy=w.cy / k, length=w.length / k, height=w.height / k) for w in words]

def canon(index, words: list, page_wh: tuple) -> tuple:
  k = unit(page_wh)
  return _CanonIndex(index, k), canon_words(words, k), k
