from __future__ import annotations
import math
import os
import re
import yaml
from app.modules.drawings_boq.takeoff.proof.reading.formats import normal_mark

RULES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "match_rules.yaml")
IN_MM = 25.4
MM_PT = 72.0 / IN_MM
SAMPLES = 40
RATIO_TOL_PCT = 2.0
SKIP_KEYS = ("count", "key")
SIZE_MARK_KIND = "SIZE"
SIZE_PREFIX = "size:"
_rules: dict = {}
DIM = re.compile(r"(\d+)\s*['\u2032\u2019]\s*(?:-?\s*(\d+)?\s*(\u00bd|\d+\s*/\s*\d+)?\s*[\"\u2033\u201d])?")
READ_SIZE = re.compile(r"(\d+(?:\.\d+)?)(?:x(\d+(?:\.\d+)?))?(?:s(\d+(?:\.\d+)?))?$")

def rules() -> dict:
  if not _rules:
    with open(RULES_PATH, encoding="utf-8") as fh:
      _rules.update(yaml.safe_load(fh))
  return _rules

def normal_text(value) -> str:
  s = str(value).strip().lower().replace("×", "x")
  s = re.sub(r"-(?=#)", "", s)
  return re.sub(r"[\s\"'″”′’]+", "", s)

def _fraction(text) -> float:
  if not text:
    return 0.0
  if text == "\u00bd":
    return 0.5
  top, bottom = (float(x) for x in text.replace(" ", "").split("/"))
  return top / bottom

def label_size_in(label) -> tuple | None:
  dims = [int(m.group(1)) * 12 + int(m.group(2) or 0) + _fraction(m.group(3)) for m in DIM.finditer(str(label or ""))]
  if len(dims) < 2:
    return None
  return (dims[0], dims[1])

def read_size_in(read) -> tuple | None:
  attrs = getattr(read, "attrs", None) or {}
  if attrs.get("width_in") is not None:
    return (float(attrs["width_in"]), None if attrs.get("height_in") is None else float(attrs["height_in"]))
  m = READ_SIZE.search(str(getattr(read, "mark", None) or ""))
  if not m:
    return None
  return (float(m.group(1)) / IN_MM, None if m.group(2) is None else float(m.group(2)) / IN_MM)

def is_size_row(row) -> bool:
  return getattr(row, "mark_kind", None) == SIZE_MARK_KIND and row.cls.value in rules()["SIZE_AS_MARK"]["classes"]

def truth_size_in(row) -> tuple | None:
  return label_size_in(row.mark)

def row_key(row) -> str | None:
  if is_size_row(row):
    size = truth_size_in(row)
    if size is not None:
      return f"{SIZE_PREFIX}{size[0]:g}x{size[1]:g}"
  return None if row.mark is None else normal_mark(row.mark)

def _dims_equal(a: float, b: float) -> bool:
  r = rules()["fact"]
  return abs(a - b) <= max(max(abs(a), abs(b)) * r["ratio"], r["length_in"])

def size_equal(row, read) -> bool:
  want, got = truth_size_in(row), read_size_in(read)
  if want is None or got is None:
    return False
  if not _dims_equal(want[0], got[0]):
    return False
  return got[1] is None or _dims_equal(want[1], got[1])

def pair_by_size(truth: list, read: list) -> list:
  def dist(t, r) -> float:
    xy = ((getattr(t, "at", None) or {}).get("page_xy"))
    pt = ((getattr(r, "geom", None) or {}).get("point"))
    return _dist(xy, pt) if xy and pt else 0.0
  cost = [[dist(t, r) for r in read] for t in truth]
  return sorted(assign(cost)) if cost and cost[0] else []

BAR_GROUP = re.compile(r"(\d+)\s*-?\s*#\s*(\d+)")
BAR_JOINERS = re.compile(r"[\s+,]|\band\b")

def bar_groups(value) -> list | None:
  text = str(value).strip().lower()
  groups = BAR_GROUP.findall(text)
  if not groups or BAR_JOINERS.sub("", BAR_GROUP.sub("", text)):
    return None
  return sorted((int(n), int(d)) for n, d in groups)

def values_equal(key: str, a, b) -> bool:
  r = rules()["fact"]
  if isinstance(a, str) and isinstance(b, str) and key.endswith("bars"):
    ga, gb = bar_groups(a), bar_groups(b)
    if ga is not None and gb is not None:
      return ga == gb
  if isinstance(a, bool) or isinstance(b, bool):
    return a == b
  if isinstance(a, (int, float)) and isinstance(b, (int, float)):
    tol = max(abs(a), abs(b)) * r["ratio"]
    if key.endswith("_mm"):
      tol = max(tol, r["length_in"] * IN_MM)
    return abs(a - b) <= tol
  if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
    return len(a) == len(b) and all(values_equal(key, x, y) for x, y in zip(a, b))
  return normal_text(a) == normal_text(b)

def compare_attrs(truth: dict, read: dict) -> tuple:
  wrong, unread = [], []
  for key, want in (truth or {}).items():
    if key in SKIP_KEYS or want == "UNKNOWN":
      continue
    if key not in read:
      unread.append(key)
    elif not values_equal(key, want, read[key]):
      wrong.append(key)
  return wrong, unread

def _dist(a: list, b: list) -> float:
  return math.hypot(a[0] - b[0], a[1] - b[1])

def point_threshold_pt(page) -> float:
  r = rules()["point"]
  share = 0.0
  if page is not None and page.paper_mm and all(page.paper_mm):
    share = r["max_offset_view_share"] * math.hypot(page.paper_mm[0], page.paper_mm[1]) * MM_PT
  inches = r["max_offset_in"] * IN_MM / page.mm_per_pt if page is not None and page.mm_per_pt else 0.0
  return max(share, inches)

def assign(cost: list) -> list:
  if not cost or not cost[0]:
    return []
  feasible = [c for row in cost for c in row if c is not None]
  if not feasible:
    return []
  try:
    import numpy as np
    from scipy.optimize import linear_sum_assignment
    big = max(feasible) * 1000.0 + 1.0
    m = np.array([[big if c is None else c for c in row] for row in cost])
    rows, cols = linear_sum_assignment(m)
    return [(int(i), int(j)) for i, j in zip(rows, cols) if cost[i][j] is not None]

  except ImportError:
    pairs = sorted((c, i, j) for i, row in enumerate(cost) for j, c in enumerate(row) if c is not None)
    used_i, used_j, out = set(), set(), []
    for _c, i, j in pairs:
      if i not in used_i and j not in used_j:
        used_i.add(i)
        used_j.add(j)
        out.append((i, j))
    return out

def _along(poly: list) -> list:
  segs = list(zip(poly, poly[1:]))
  total = sum(_dist(a, b) for a, b in segs)
  if total <= 0:
    return [poly[0]]

  out = []
  for k in range(SAMPLES + 1):
    target = total * k / SAMPLES
    run = 0.0
    for a, b in segs:
      seg = _dist(a, b)
      if run + seg >= target - 1e-9:
        t = 0.0 if seg == 0 else (target - run) / seg
        out.append([a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])])
        break
      run += seg
  return out

def _to_line(p: list, poly: list) -> float:
  best = float("inf")
  for a, b in zip(poly, poly[1:]):
    dx, dy = b[0] - a[0], b[1] - a[1]
    seg2 = dx * dx + dy * dy
    t = 0.0 if seg2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / seg2))
    best = min(best, _dist(p, [a[0] + t * dx, a[1] + t * dy]))
  return best

def line_overlap(truth: list, read: list, offset_pt: float) -> float:
  if len(truth) < 2 or len(read) < 2:
    return 0.0
  a = sum(1 for p in _along(truth) if _to_line(p, read) <= offset_pt) / (SAMPLES + 1)
  b = sum(1 for p in _along(read) if _to_line(p, truth) <= offset_pt) / (SAMPLES + 1)
  return min(a, b)

def line_offset_pt(page, thickness_mm) -> float:
  share = rules()["line"]["max_offset_thickness_share"]
  if page is not None and page.mm_per_pt and thickness_mm:
    return share * float(thickness_mm) / page.mm_per_pt
  return point_threshold_pt(page) * share

def _area(poly: list) -> float:
  return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))) / 2.0

def _clip(subject: list, clip: list) -> list:
  def inside(p, a, b):
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= 0
  def cut(p, q, a, b):
    x1, y1, x2, y2, x3, y3, x4, y4 = p[0], p[1], q[0], q[1], a[0], a[1], b[0], b[1]
    d = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if d == 0:
      return q
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / d
    return [x1 + t * (x2 - x1), y1 + t * (y2 - y1)]

  sign = 1 if sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(clip, clip[1:] + clip[:1])) > 0 else -1
  if sign < 0:
    clip = clip[::-1]
  out = subject
  for a, b in zip(clip, clip[1:] + clip[:1]):
    src, out = out, []
    if not src:
      break
    prev = src[-1]
    for cur in src:
      if inside(cur, a, b):
        if not inside(prev, a, b):
          out.append(cut(prev, cur, a, b))
        out.append(cur)
      elif inside(prev, a, b):
        out.append(cut(prev, cur, a, b))
      prev = cur
  return out

def area_iou(a: list, b: list, use_shapely: bool = True) -> float:
  if len(a) < 3 or len(b) < 3:
    return 0.0
  if use_shapely:
    try:
      from shapely.geometry import Polygon
      pa, pb = Polygon(a).buffer(0), Polygon(b).buffer(0)
      union = pa.union(pb).area
      return 0.0 if union <= 0 else pa.intersection(pb).area / union
    except ImportError:
      pass
  
  inter = _area(_clip(a, b)) if len(_clip(a, b)) >= 3 else 0.0
  union = _area(a) + _area(b) - inter
  return 0.0 if union <= 0 else inter / union

def _shape(geom: dict | None) -> tuple:
  if not geom:
    return None, None
  kind, value = next(iter(geom.items()))
  return kind, ([value] if kind == "point" else value)

def geometry_cost(truth_geom: dict | None, read_geom: dict | None, page, thickness_mm=None) -> float | None:
  tk, tv = _shape(truth_geom)
  rk, rv = _shape(read_geom)
  
  if tk is None or rk is None or tk != rk:
    return None
  if tk == "point":
    d = _dist(tv[0], rv[0])
    return d if d <= point_threshold_pt(page) else None
  if tk == "polyline":
    ov = line_overlap(tv, rv, line_offset_pt(page, thickness_mm))
    return 1.0 - ov if ov >= rules()["line"]["min_overlap"] else None
  iou = area_iou(tv, rv)
  return 1.0 - iou if iou >= rules()["area"]["min_iou"] else None

def pair_group(truth: list, read: list, page) -> tuple:
  cost = [[geometry_cost(t.geom, r.geom, page, (t.attrs or {}).get("thickness_mm")) for r in read] for t in truth]
  pairs = assign(cost)
  used_t, used_r = {i for i, _ in pairs}, {j for _, j in pairs}
  left_r = [j for j in range(len(read)) if j not in used_r]
  for i in [i for i in range(len(truth)) if i not in used_t]:
    for j in left_r:
      if not truth[i].geom or not read[j].geom:
        pairs.append((i, j))
        left_r.remove(j)
        break
  used_t, used_r = {i for i, _ in pairs}, {j for _, j in pairs}
  return pairs, [i for i in range(len(truth)) if i not in used_t], [j for j in range(len(read)) if j not in used_r]

def group_key(mark) -> str | None:
  return None if mark is None else normal_mark(mark)

def counts_equal(want, read_total: int) -> bool:
  return isinstance(want, int) and not isinstance(want, bool) and want == read_total

def ratio_equal(a, b) -> bool:
  if a in (None, "UNKNOWN") or b in (None, "UNKNOWN"):
    return a == b
  return abs(float(a) - float(b)) <= max(abs(float(a)), abs(float(b))) * RATIO_TOL_PCT / 100.0

def title_words(value) -> set:
  return set(re.findall(r"[A-Z0-9]+", str(value or "").upper()))

def title_equal(truth_value, read_value) -> bool:
  a, b = title_words(truth_value), title_words(read_value)
  return bool(a) and bool(b) and (a <= b or b <= a)

def field_equal(name: str, truth_value, read_value) -> bool:
  if name == "scale_ratio":
    return ratio_equal(truth_value, read_value)
  if name == "title":
    return title_equal(truth_value, read_value)
  if truth_value in (None, "UNKNOWN"):
    return True
  return normal_text(truth_value) == normal_text(read_value if read_value is not None else "")
