from __future__ import annotations
import math
from dataclasses import dataclass
from functools import cached_property
from array import array
from app.modules.drawings_boq.takeoff.orientation import axes as AX

MIN_WORDS = 8
QUARTER_SHARE = 0.6
SKEW_SHARE = 0.8
SKEW_MIN_DEG = 0.75
SKEW_BAND_DEG = 2.0
AXES_MIN_SHARE = 0.4
AXES_AGREE_DEG = 3.0
MIN_SEGMENT_PT = 3.0
MAX_SEGMENTS_SAMPLED = 120_000

_QUARTER = ((1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0))

def _cos_sin(psi: float) -> tuple:
  q = round(psi / 90.0)
  if abs(psi - q * 90.0) < 1e-9:
    return _QUARTER[q % 4]
  a = math.radians(psi)
  return math.cos(a), math.sin(a)

def _wrap180(deg: float) -> float:
  d = (deg + 180.0) % 360.0 - 180.0
  return 180.0 if d == -180.0 else d

@dataclass(frozen=True)
class Frame:
  psi: float = 0.0
  box_in: tuple = (0.0, 0.0, 0.0, 0.0)
  turn_deg: int = 0
  skew_deg: float = 0.0
  words: int = 0
  share: float = 0.0
  reason: str = "UPRIGHT"

  @property
  def identity(self) -> bool:
    return self.psi == 0.0

  @property
  def quarter(self) -> bool:
    return not self.identity and abs(self.psi / 90.0 - round(self.psi / 90.0)) < 1e-9

  @cached_property
  def _geo(self) -> tuple:
    l, b, r, t = self.box_in
    cx, cy = (l + r) / 2.0, (b + t) / 2.0
    c, s = _cos_sin(self.psi)
    xs, ys = [], []
    for x, y in ((l, b), (r, b), (r, t), (l, t)):
      xs.append(c * (x - cx) - s * (y - cy) + cx)
      ys.append(s * (x - cx) + c * (y - cy) + cy)
    return cx, cy, c, s, l - min(xs), b - min(ys), max(xs) - min(xs), max(ys) - min(ys)

  @property
  def box_out(self) -> tuple:
    if self.identity:
      return tuple(self.box_in)
    _, _, _, _, _, _, w, h = self._geo
    return (self.box_in[0], self.box_in[1], self.box_in[0] + w, self.box_in[1] + h)

  def forward(self, x: float, y: float) -> tuple:
    if self.identity:
      return x, y
    cx, cy, c, s, sx, sy, _, _ = self._geo
    return c * (x - cx) - s * (y - cy) + cx + sx, s * (x - cx) + c * (y - cy) + cy + sy

  def back(self, x: float, y: float) -> tuple:
    if self.identity:
      return x, y
    cx, cy, c, s, sx, sy, _, _ = self._geo
    dx, dy = x - cx - sx, y - cy - sy
    return c * dx + s * dy + cx, -s * dx + c * dy + cy

  def forward_box(self, b) -> list:
    return _box_through(self.forward, b)

  def back_box(self, b) -> list:
    return _box_through(self.back, b)

  def to_json(self) -> dict:
    return {"turn_deg": int(self.turn_deg), "skew_deg": round(float(self.skew_deg), 2), "psi": round(float(self.psi), 6), "words": int(self.words), "share": round(float(self.share), 3),
      "box_in": [round(float(v), 4) for v in self.box_in], "reason": self.reason}

  @staticmethod
  def from_json(d: dict | None) -> "Frame":
    if not d or not d.get("psi"):
      return Frame()
    return Frame(psi=float(d["psi"]), box_in=tuple(float(v) for v in d["box_in"]), turn_deg=int(d.get("turn_deg") or 0), skew_deg=float(d.get("skew_deg") or 0.0), words=int(d.get("words") or 0),
      share=float(d.get("share") or 0.0), reason=str(d.get("reason") or "TEXT"))

def _box_through(fn, b) -> list:
  pts = [fn(b[0], b[1]), fn(b[2], b[1]), fn(b[2], b[3]), fn(b[0], b[3])]
  xs, ys = [p[0] for p in pts], [p[1] for p in pts]
  return [min(xs), min(ys), max(xs), max(ys)]

def _weighted_median(pairs: list) -> float:
  pairs = sorted(pairs)
  half = sum(w for _, w in pairs) / 2.0
  run = 0.0
  for v, w in pairs:
    run += w
    if run >= half:
      return v
  return pairs[-1][0]

def text_turn(words: list) -> tuple:
  sample = []
  
  by_quarter = [0.0, 0.0, 0.0, 0.0]
  for w in words:
    t = (w.text or "").strip()
    if len(t) < 2 or not any(ch.isalnum() for ch in t):
      continue
  
    weight = float(w.length) if w.length and w.length > 0 else len(t) * float(w.size or 0.0) * 0.5
    if weight <= 0.0:
      continue
    a = float(w.angle) % 360.0
    q = round(a / 90.0)
    sample.append((q % 4, a - q * 90.0, weight))
    by_quarter[q % 4] += weight
    
  if len(sample) < MIN_WORDS:
    return 0, 0.0, len(sample), 0.0, "TOO_LITTLE_TEXT"
  total = sum(by_quarter)
  q = max(range(4), key=lambda i: by_quarter[i])
  share = by_quarter[q] / total
  
  if share < QUARTER_SHARE:
    return 0, 0.0, len(sample), share, "TEXT_RUNS_TWO_WAYS"
  mine = [(r, wt) for qq, r, wt in sample if qq == q]
  med = _weighted_median(mine)
  skew = 0.0
  if abs(med) >= SKEW_MIN_DEG:
    close = sum(wt for r, wt in mine if abs(r - med) <= SKEW_BAND_DEG)
    if close / sum(wt for _, wt in mine) >= SKEW_SHARE:
      skew = med
  return q * 90, skew, len(sample), share, "TEXT"

def line_axes(segs: array, kinds: array) -> tuple:
  n = len(kinds)
  step = max(1, n // MAX_SEGMENTS_SAMPLED)
  
  bins: dict = {}
  total = 0.0
  for i in range(0, n, step):
    if kinds[i]:
      continue
  
    k = i * 5
    dx, dy = segs[k + 2] - segs[k], segs[k + 3] - segs[k + 1]
    ln = math.hypot(dx, dy)
    if ln >= MIN_SEGMENT_PT:
      AX.add(bins, math.degrees(math.atan2(dy, dx)), ln)
      total += ln
  return AX.lead(bins, total)

def detect(words: list, box: tuple, segs: array | None = None, kinds: array | None = None) -> Frame:
  turn, skew, n, share, reason = text_turn(words)
  
  if reason != "TEXT":
    return Frame(box_in=tuple(box), words=n, share=share, reason=reason)
  if turn == 0 and skew == 0.0:
    return Frame(box_in=tuple(box), words=n, share=share, reason="UPRIGHT")
  if skew != 0.0 and segs is not None and kinds is not None:
    axis, lead = line_axes(segs, kinds)
    if lead >= AXES_MIN_SHARE and abs(AX.wrap_axis(axis - skew)) > AXES_AGREE_DEG:
      return Frame(box_in=tuple(box), words=n, share=share, reason="LINES_DISAGREE")
  psi = _wrap180(-(turn + skew))
  return Frame(psi=psi, box_in=tuple(box), turn_deg=turn, skew_deg=skew, words=n, share=share, reason="TEXT")
