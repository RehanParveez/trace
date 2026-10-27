from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.prep import title_block as TB

FRAME_BAND_SHARE = 0.03          
FRAME_SPAN_SHARE = 0.5           
TITLE_RECT_TOL_MM = 2.0          
TITLE_RECT_PAD = 1.5             
PT_PER_MM = 72.0 / 25.4
_LABEL = re.compile(r"^(?:CLIENT|PROJECT|CONSULTANT|DRAWN|CHECKED|TITLE|DRG|DWG|REVISION|SHEET\s+NO)\b", re.I)

def title_rect(words: list, cropbox: tuple) -> tuple | None:
  """The box of the title block, from its own label words (client, project, drawn, checked, title ...) that lie in the title-block zone of the page. None when fewer than three are found."""
  found = [w for w in TB.zone_words(words, cropbox) if _LABEL.match(w.text.strip())]
  if len(found) < 3:
    return None
  pad = TITLE_RECT_PAD * max(w.size for w in found) + TITLE_RECT_TOL_MM * PT_PER_MM
  return min(w.x0 for w in found) - pad, min(w.cy for w in found) - pad, max(w.x1 for w in found) + pad, max(w.cy for w in found) + pad

def frame_runs(index, runs: list, frames: list) -> list:
  if not runs:
    return []

  from app.modules.drawings_boq.takeoff.extract import walls as W
  l, b, r, t = index.bbox
  w, h = max(r - l, 1.0), max(t - b, 1.0)
  rect = title_rect(index.words, index.bbox)
  out = []
  
  for run in runs:
    (ax, ay), (bx, by) = W.run_ends(run, frames[run.peak])
    if rect and rect[0] <= min(ax, bx) and max(ax, bx) <= rect[2] and rect[1] <= min(ay, by) and max(ay, by) <= rect[3]:
      out.append(run)
      continue
    tol = TITLE_RECT_TOL_MM * PT_PER_MM
    if abs(ax - bx) <= tol:
      near = min(ax, bx) - l <= FRAME_BAND_SHARE * w or r - max(ax, bx) <= FRAME_BAND_SHARE * w
      if near and abs(ay - by) >= FRAME_SPAN_SHARE * h:
        out.append(run)
    elif abs(ay - by) <= tol:
      near = min(ay, by) - b <= FRAME_BAND_SHARE * h or t - max(ay, by) <= FRAME_BAND_SHARE * h
      if near and abs(ax - bx) >= FRAME_SPAN_SHARE * w:
        out.append(run)
  return out
