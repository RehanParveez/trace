from __future__ import annotations
from app.modules.drawings_boq.takeoff.orientation.frame import Frame
from array import array
from app.modules.drawings_boq.takeoff.prep.extract import Ring, Word, RawPage
import math
from app.modules.drawings_boq.takeoff.prep.spatial import VectorIndex

def turn_segments(segs: array, frame: Frame) -> array:
  out = array("f", bytes(len(segs) * segs.itemsize))
  fwd = frame.forward
  
  for k in range(0, len(segs), 5):
    a, b = fwd(segs[k], segs[k + 1])
    c, d = fwd(segs[k + 2], segs[k + 3])
    out[k], out[k + 1], out[k + 2], out[k + 3], out[k + 4] = a, b, c, d, segs[k + 4]
  return out

def turn_ring(r: Ring, frame: Frame) -> Ring:
  pts = [frame.forward(x, y) for x, y in r.pts]
  xs, ys = [p[0] for p in pts], [p[1] for p in pts]
  return Ring(pts=pts, area=r.area, bbox=(min(xs), min(ys), max(xs), max(ys)), fill=r.fill, curved=r.curved, width=r.width)

GLYPH_WIDTH_EM = 0.6

def tight_extent(w: Word) -> tuple:
  a = math.radians(float(w.angle) % 90.0)
  s2 = abs(math.sin(2.0 * a))
  
  if s2 < 0.03:
    return w.length, w.height
  h = max(0.3 * w.size, w.height - GLYPH_WIDTH_EM * w.size * s2)
  return max(0.3 * h, w.length - h * s2), h

def turn_word(w: Word, frame: Frame) -> Word:
  cx, cy = frame.forward(w.cx, w.cy)
  angle = (w.angle + frame.psi) % 360.0
  
  if angle < 1e-6 or angle > 360.0 - 1e-6:
    angle = 0.0
  if frame.quarter:
    x0, y0, x1, y1 = frame.forward_box((w.x0, w.y0, w.x1, w.y1))
    length, height = w.length, w.height
  else:
    length, height = tight_extent(w)
    a = math.radians(angle if angle <= 180.0 else angle - 360.0)
    ca, sa = abs(math.cos(a)), abs(math.sin(a))
    hx = (length / 2.0) * ca + (height / 2.0) * sa
    hy = (length / 2.0) * sa + (height / 2.0) * ca
    x0, y0, x1, y1 = cx - hx, cy - hy, cx + hx, cy + hy
    
  return Word(text=w.text, x0=x0, y0=y0, x1=x1, y1=y1, angle=angle, size=w.size, cx=cx, cy=cy, length=length, height=height)

def turn_words(words: list, frame: Frame) -> list:
  return [turn_word(w, frame) for w in words]

def turn_rings(rings: list, frame: Frame) -> list:
  return [turn_ring(r, frame) for r in rings]

def turn_index(index: VectorIndex, frame: Frame) -> VectorIndex:
  if frame.identity:
    return index
  return VectorIndex(turn_segments(index.segs, frame), index.kinds, turn_rings(index.rings, frame), turn_words(index.words, frame), tuple(frame.box_out))

def turn_page(raw: RawPage, frame: Frame) -> RawPage:
  if frame.identity:
    return raw
  out = frame.box_out
  
  images = [{**im, "bbox": tuple(frame.forward_box(im["bbox"]))} if im.get("bbox") else dict(im) for im in raw.images]
  return RawPage(page_no=raw.page_no, width_pt=out[2] - out[0], height_pt=out[3] - out[1], rotation=0, mediabox=tuple(frame.forward_box(raw.mediabox)), cropbox=tuple(out),
    segs=turn_segments(raw.segs, frame), kinds=raw.kinds, rings=turn_rings(raw.rings, frame), words=turn_words(raw.words, frame), images=images, stats=dict(raw.stats))
