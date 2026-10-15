from __future__ import annotations
import math
from dataclasses import dataclass, field

GRID_MM = 25.0
MIN_SUPPORT = 4
MIN_RATIO = 0.70
MAX_RESIDUAL_MM = 50.0
SIZE_TOL = 0.10
SIZE_ABS_MM = 15.0
ENVELOPE_CONFIDENCE = 0.3
VOTE_CONFIDENCE = 0.8
TOUCH_TOL_MM = 1.0

REFERENCE, COLUMN_MATCH, ENVELOPE, UNALIGNED, MANUAL = "REFERENCE", "COLUMN_MATCH", "ENVELOPE", "UNALIGNED", "MANUAL"
ASSUMED, CONFIRMED = "ASSUMED", "CONFIRMED"

@dataclass(frozen=True)
class FramePoint:
  """A column (or other mark) centre on its view, in millimetres, with its plan size when known (sorted, so 230 x 300 equals 300 x 230)."""
  x: float
  y: float
  size: tuple | None = None
  ref: object = None

@dataclass(frozen=True)
class Alignment:
  """Where one view sits on the frame: the translation that takes its sheet positions to the reference view's, then the origin shift of the frame."""
  view: str
  dx_mm: float
  dy_mm: float
  method: str
  grade: str = ASSUMED
  supporters: int = 0
  compared: int = 0
  residual_mm: float = 0.0
  confidence: float = 0.0

  @property
  def usable(self) -> bool:
    return self.method != UNALIGNED

@dataclass(frozen=True)
class Frame:
  reference: str | None
  origin_mm: tuple
  alignments: dict = field(default_factory=dict)

  def to_frame(self, view: str, x: float, y: float) -> tuple | None:
    a = self.alignments.get(view)
    if a is None or not a.usable:
      return None
    return (x + a.dx_mm, y + a.dy_mm)

def size_class(length: float | None, width: float | None) -> tuple | None:
  if not length or not width:
    return None
  a, b = sorted((float(length), float(width)))
  return (a, b)

def _same_size(p: tuple | None, q: tuple | None) -> bool:
  if p is None or q is None:
    return True
  return all(abs(a - b) <= max(SIZE_ABS_MM, SIZE_TOL * max(a, b)) for a, b in zip(p, q))

def choose_reference(views: dict, preferred: str | None = None) -> str | None:
  """The view with the most points; a tie goes to the smaller key so the choice does not depend on input order. A preferred view wins when it has any."""
  if preferred and views.get(preferred):
    return preferred
  ranked = sorted(((-len(pts), key) for key, pts in views.items() if pts))
  return ranked[0][1] if ranked else None

def _match(ref: list, pts: list, dx: float, dy: float, tol: float) -> list:
  """One-to-one pairs between the reference points and the points moved by (dx, dy), nearest first, within tol."""
  pairs = []
  for i, p in enumerate(pts):
    for j, r in enumerate(ref):
      if not _same_size(r.size, p.size):
        continue
      d = math.hypot(r.x - (p.x + dx), r.y - (p.y + dy))
      if d <= tol:
        pairs.append((d, i, j))
  pairs.sort()
  used_i, used_j, out = set(), set(), []
  for d, i, j in pairs:
    if i in used_i or j in used_j:
      continue
    used_i.add(i)
    used_j.add(j)
    out.append((i, j, d))
  return out

def vote_offset(ref: list, pts: list, *, grid: float = GRID_MM, min_support: int = MIN_SUPPORT, min_ratio: float = MIN_RATIO,
    max_residual: float = MAX_RESIDUAL_MM) -> dict | None:
  """The translation that takes pts onto ref, found by voting. Every (reference, view) pair of the same size class proposes an offset; offsets are
  counted on a grid; the best one is refined to the mean of the points that agree with it. It stands when at least min_support points agree, or min_ratio
  of the smaller set, and none of them is further than max_residual from the mean. Returns {dx, dy, supporters, compared, residual} or None."""
  smaller = min(len(ref), len(pts))
  if smaller < 2:
    return None
  bins: dict = {}
  for i, p in enumerate(pts):
    for j, r in enumerate(ref):
      if not _same_size(r.size, p.size):
        continue
      key = (round((r.x - p.x) / grid), round((r.y - p.y) / grid))
      bins.setdefault(key, []).append((i, j, r.x - p.x, r.y - p.y))
  if not bins:
    return None
  scored = []
  for (kx, ky), items in bins.items():
    near = [it for k2 in ((kx + a, ky + b) for a in (-1, 0, 1) for b in (-1, 0, 1)) for it in bins.get(k2, [])]
    scored.append((len({i for i, _, _, _ in near}), -abs(kx) - abs(ky), kx, ky, near))
  scored.sort(key=lambda s: (-s[0], -s[1], s[2], s[3]))
  best = scored[0]
  dx = sum(it[2] for it in best[4]) / len(best[4])
  dy = sum(it[3] for it in best[4]) / len(best[4])
  
  for _ in range(2):
    pairs = _match(ref, pts, dx, dy, max_residual * 2)
    if not pairs:
      return None
    dx += sum(ref[j].x - (pts[i].x + dx) for i, j, _ in pairs) / len(pairs)
    dy += sum(ref[j].y - (pts[i].y + dy) for i, j, _ in pairs) / len(pairs)
  pairs = _match(ref, pts, dx, dy, max_residual)
  supporters = len(pairs)
  if supporters < 2:
    return None
  residual = max(d for _, _, d in pairs)
  if not (supporters >= min_support or supporters >= min_ratio * smaller):
    return None
  if supporters < min_ratio * smaller and supporters < min_support:
    return None
  if residual > max_residual:
    return None
  return {"dx": dx, "dy": dy, "supporters": supporters, "compared": smaller, "residual": residual}

def envelope(pts: list) -> tuple | None:
  if not pts:
    return None
  xs, ys = [p.x for p in pts], [p.y for p in pts]
  return (min(xs), min(ys), max(xs), max(ys))

def envelope_offset(ref_box: tuple | None, box: tuple | None) -> tuple | None:
  """The translation that puts the lower-left corner of a view's envelope on the reference's. Only a guess: it needs the two envelopes to be the same size
  within the grid, otherwise nothing is returned."""
  if ref_box is None or box is None:
    return None
  rw, rh = ref_box[2] - ref_box[0], ref_box[3] - ref_box[1]
  w, h = box[2] - box[0], box[3] - box[1]
  if min(rw, rh, w, h) <= 0 or abs(rw - w) > max(GRID_MM * 2, 0.05 * rw) or abs(rh - h) > max(GRID_MM * 2, 0.05 * rh):
    return None
  return (ref_box[0] - box[0], ref_box[1] - box[1])

def align_views(views: dict, *, reference: str | None = None, confirmed: dict | None = None, **params) -> Frame:
  """Place every view on one frame. views maps a view key to its points; confirmed maps a view key to (dx, dy) set by a person, which is used as given
  and graded CONFIRMED. The frame origin is the lower-left point of the reference view (lowest y, then lowest x)."""
  confirmed = confirmed or {}
  ref_key = choose_reference({k: v for k, v in views.items()}, reference)
  if ref_key is None:
    return Frame(None, (0.0, 0.0), {k: Alignment(k, 0.0, 0.0, UNALIGNED) for k in views})
  ref_pts = sorted(views[ref_key], key=lambda p: (p.y, p.x))
  origin = (ref_pts[0].x, ref_pts[0].y)
  out: dict = {}
  
  for key in sorted(views):
    pts = views[key]
    if key == ref_key:
      out[key] = Alignment(key, 0.0, 0.0, REFERENCE, ASSUMED, len(pts), len(pts), 0.0, 1.0)
      continue
    if key in confirmed:
      dx, dy = confirmed[key]
      out[key] = Alignment(key, float(dx), float(dy), MANUAL, CONFIRMED, 0, 0, 0.0, 1.0)
      continue
    
    v = vote_offset(ref_pts, sorted(pts, key=lambda p: (p.x, p.y)), **params) if pts else None
    if v is not None:
      out[key] = Alignment(key, round(v["dx"], 2), round(v["dy"], 2), COLUMN_MATCH, ASSUMED, v["supporters"], v["compared"], round(v["residual"], 2),
        round(VOTE_CONFIDENCE * v["supporters"] / max(1, v["compared"]), 3))
      continue
    e = envelope_offset(envelope(ref_pts), envelope(pts))
    if e is not None:
      out[key] = Alignment(key, round(e[0], 2), round(e[1], 2), ENVELOPE, ASSUMED, 0, min(len(ref_pts), len(pts)), 0.0, ENVELOPE_CONFIDENCE)
      continue
    out[key] = Alignment(key, 0.0, 0.0, UNALIGNED)
  if ref_key in confirmed:
    out[ref_key] = Alignment(ref_key, float(confirmed[ref_key][0]), float(confirmed[ref_key][1]), MANUAL, CONFIRMED, 0, 0, 0.0, 1.0)
  return Frame(ref_key, origin, out)

def nudge(a: Alignment, dx: float, dy: float) -> Alignment:
  """A person moves a view by (dx, dy) on the overlay. The result is a manual placement and counts as confirmed once they confirm it."""
  return Alignment(a.view, round(a.dx_mm + dx, 2), round(a.dy_mm + dy, 2), MANUAL, ASSUMED, a.supporters, a.compared, a.residual_mm, a.confidence)

def confirm(a: Alignment) -> Alignment:
  return Alignment(a.view, a.dx_mm, a.dy_mm, a.method, CONFIRMED, a.supporters, a.compared, a.residual_mm, 1.0 if a.usable else 0.0)

def frame_xy(frame: Frame, view: str, x: float, y: float) -> tuple | None:
  """A sheet position in frame coordinates (origin at the reference view's lower-left column), or None for a view that is not placed."""
  p = frame.to_frame(view, x, y)
  if p is None:
    return None
  return (round(p[0] - frame.origin_mm[0], 2), round(p[1] - frame.origin_mm[1], 2))

@dataclass(frozen=True)
class Box:
  """An axis-aligned block of concrete in the frame: plan rectangle and a z range (all mm)."""
  x0: float
  y0: float
  x1: float
  y1: float
  z0: float
  z1: float

def box_around(cx: float, cy: float, length: float, width: float, z0: float, z1: float) -> Box:
  return Box(cx - length / 2.0, cy - width / 2.0, cx + length / 2.0, cy + width / 2.0, z0, z1)

def _covers(c: float, lo: float, hi: float, outward: int, tol: float) -> bool:
  """Does the neighbour's extent [lo, hi] meet a face at coordinate c whose outside is in direction outward: through it, or starting at it and running out."""
  if lo + tol < c < hi - tol:
    return True
  if outward > 0 and abs(c - lo) <= tol and hi > c + tol:
    return True
  if outward < 0 and abs(c - hi) <= tol and lo < c - tol:
    return True
  return False

def shared_side_faces(box: Box, neighbours: list, tol: float = TOUCH_TOL_MM) -> list:
  """The side faces of a box that other concrete covers: [{face, area_mm2, by}] with one entry per face and neighbour, the covered parts of a face never
  counted twice. A face is covered by a neighbour when the neighbour passes through it or starts on it and runs outward; a neighbour that only ends on
  the face from the inside leaves it open (the outer face of an edge column). neighbours is a list of (label, Box)."""
  from shapely.geometry import box as sbox
  from shapely.ops import unary_union
  faces = (("-x", 0, box.x0, -1, (box.y0, box.y1)), ("+x", 0, box.x1, 1, (box.y0, box.y1)),
    ("-y", 1, box.y0, -1, (box.x0, box.x1)), ("+y", 1, box.y1, 1, (box.x0, box.x1)))
  out = []
  for name, axis, c, sign, (a0, a1) in faces:
    taken = []
    for label, n in neighbours:
      lo, hi = (n.x0, n.x1) if axis == 0 else (n.y0, n.y1)
      if not _covers(c, lo, hi, sign, tol):
        continue
      na0, na1 = (n.y0, n.y1) if axis == 0 else (n.x0, n.x1)
      u0, u1, z0, z1 = max(a0, na0), min(a1, na1), max(box.z0, n.z0), min(box.z1, n.z1)
      if u1 - u0 > tol and z1 - z0 > tol:
        taken.append((label, sbox(u0, z0, u1, z1)))
    seen = None
    for label, rect in taken:
      fresh = rect if seen is None else rect.difference(seen)
      area = fresh.area
      if area > 1e-6:
        out.append({"face": name, "area_mm2": area, "by": label})
      seen = rect if seen is None else unary_union([seen, rect])
  return out
