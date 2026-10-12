from __future__ import annotations
import math
from shapely.geometry import Polygon
from shapely.ops import unary_union
from tests.drawings_boq.takeoff.pdf_factory import Canvas, PdfBuilder, PT_MM

K_ARC = 0.5522847498

def _walls():
  
  return [
    (0, 0, 9000, 0, 230), (9000, 0, 9000, 8000, 230), (9000, 8000, 0, 8000, 230), (0, 8000, 0, 0, 230),
    (4500, 0, 4500, 4000, 115),
    (0, 4000, 9000, 4000, 115),
    (6000, 4000, 6000, 8000, 115),
  ]

def _openings():
  return [
    ("door", 5, 2000, 900),    
    ("door", 5, 6500, 900),    
    ("door", 6, 1500, 900),    
    ("door", 2, 5500, 1000),   
    ("window", 0, 1000, 1200), ("window", 0, 6000, 1200),
    ("window", 3, 5000, 1200),  
    ("window", 1, 5000, 1200),
  ]

def _frame(w):
  x1, y1, x2, y2, t = w
  ang = math.atan2(y2 - y1, x2 - x1)
  return (x1, y1, math.cos(ang), math.sin(ang), math.hypot(x2 - x1, y2 - y1), t)

def _rect_on_wall(w, s0, s1, extra=0.0):
  x1, y1, ux, uy, L, t = _frame(w)
  nx, ny = -uy, ux
  h = t / 2 + extra
  pts = [(x1 + ux * s0 + nx * h, y1 + uy * s0 + ny * h), (x1 + ux * s1 + nx * h, y1 + uy * s1 + ny * h),
    (x1 + ux * s1 - nx * h, y1 + uy * s1 - ny * h), (x1 + ux * s0 - nx * h, y1 + uy * s0 - ny * h)]
  return Polygon(pts)

def make_house(drawn_ratio: float = 100.0, window_style: str = "lines", with_schedule: bool = True, with_dims: bool = True,
  wall_height_note: str | None = "WALL HEIGHT 3000 MM", scale_text: str | None = "SCALE 1:100",
  paper: tuple = (1190.55, 841.89), c2_schedule: str = "230 x 300", extra_untagged_column: bool = False) -> bytes:
  k = 1.0 / (drawn_ratio * PT_MM)
  ox, oy = 150.0, 150.0
  def P(x, y): return (ox + x * k, oy + y * k)
  walls, opens = _walls(), _openings()
  polys = []
  for wi, w in enumerate(walls):
    _, _, _, _, L, _ = _frame(w)
    cuts = sorted((s, s + wd) for kind, i, s, wd in opens if i == wi)
    cur = 0.0
    for a, b in cuts:
      if a > cur:
        polys.append(_rect_on_wall(w, cur, a, extra=0.0))
      cur = b
    if cur < L:
      polys.append(_rect_on_wall(w, cur, L))
  
  merged = unary_union([p.buffer(0.01, join_style=2) for p in polys]).buffer(-0.01, join_style=2)
  c = Canvas()
  c.gray(0.0).width(0.35)
  geoms = list(merged.geoms) if hasattr(merged, "geoms") else [merged]
  for g in geoms:
    for ring in [g.exterior, *g.interiors]:
      pts = [P(x, y) for x, y in list(ring.coords)[:-1]]
      c.polyline(pts, close=True)

  for kind, wi, s, wd in opens:
    x1, y1, ux, uy, L, t = _frame(walls[wi])
    nx, ny = -uy, ux
    if kind == "window":
      offs = (t / 2, 0.0, -t / 2) if window_style == "lines" else ()
      for off in offs:
        a = P(x1 + ux * s + nx * off, y1 + uy * s + ny * off)
        b = P(x1 + ux * (s + wd) + nx * off, y1 + uy * (s + wd) + ny * off)
        c.line(*a, *b)
    else:
    
      hx, hy = x1 + ux * s + nx * t / 2, y1 + uy * s + ny * t / 2
      tipx, tipy = hx + nx * wd, hy + ny * wd
      c.line(*P(hx, hy), *P(tipx, tipy))
      ex, ey = hx + ux * wd, hy + uy * wd
      p0, p3 = P(tipx, tipy), P(ex, ey)
      c1 = P(tipx + ux * K_ARC * wd, tipy + uy * K_ARC * wd)
      c2 = P(ex + nx * K_ARC * wd, ey + ny * K_ARC * wd)
      c.raw(f"{p0[0]:.4f} {p0[1]:.4f} m {c1[0]:.4f} {c1[1]:.4f} {c2[0]:.4f} {c2[1]:.4f} {p3[0]:.4f} {p3[1]:.4f} c S")
  
  cols = [(0, 0, "C1"), (9000, 0, "C1"), (0, 8000, "C1"), (9000, 8000, "C1"), (4500, 0, "C2"), (4500, 4000, "C2"),
          (6000, 8000, "C2"), (6000, 4000, "C2")]
  if extra_untagged_column:
    cols.append((0, 4000, ""))
  for x, y, tag in cols:
    p = P(x - 115, y - 115)
    c.rect(p[0], p[1], 230 * k, 230 * k, fill=True, stroke=True)
    if tag:
      tx, ty = P(x + 260, y + 260 if y < 8000 else y - 420)
      c.text(tx, ty, tag, 5)
  
  dpos = [(2450, 4000, "D1"), (6950, 4000, "D1"), (6000, 4950, "D1"), (7500, 8000, "D2")]
  for x, y, tag in dpos:
    tx, ty = P(x - 60, y + 330 if y < 8000 else y - 520)
    c.text(tx, ty, tag, 5)
  for x, y, tag in ((1600, 0, "W1"), (6600, 0, "W1"), (0, 5600, "W1"), (9000, 5600, "W1")):
    tx, ty = P(x - 130 if x else x - 450, y - 330 if y == 0 else y + 120)
    c.text(tx, ty, tag, 5)
  
  rooms = [((600, 1800), "BED ROOM 1", "4270 x 3770"), ((5100, 1800), "BED ROOM 2", "4270 x 3770"),
    ((1900, 5600), "LOUNGE", "5770 x 3770"), ((6500, 5600), "KITCHEN", "2770 x 3770")]
  for (x, y), name, size in rooms:
    px, py = P(x, y)
    c.text(px, py, name, 6)
    c.text(px, py - 9, size, 5)
 
  if with_dims:
    xs = [0, 4500, 6000, 9000]
    for i in range(len(xs) - 1):
      a, b = P(xs[i], 8000 + 600), P(xs[i + 1], 8000 + 600)
      c.dimension(a[0], a[1], b[0], b[1], str(xs[i + 1] - xs[i]), offset=16, size=5.5)
    ys = [0, 4000, 8000]
    for i in range(len(ys) - 1):
      a, b = P(-600, ys[i]), P(-600, ys[i + 1])
      c.dimension(a[0], a[1], b[0], b[1], str(ys[i + 1] - ys[i]), offset=16, size=5.5)
  
  w, h = paper
  sx, sy = ox + 10000 * k + 40, oy + 7600 * k
  if with_schedule:
    c.text(sx, sy + 12, "COLUMN SCHEDULE", 7, font="F2")
    c.text(sx, sy, "MARK", 5.5); c.text(sx + 60, sy, "SIZE", 5.5)
    c.text(sx, sy - 9, "C1", 5.5); c.text(sx + 60, sy - 9, "230 x 230", 5.5)
    c.text(sx, sy - 18, "C2", 5.5); c.text(sx + 60, sy - 18, c2_schedule, 5.5)
    c.text(sx, sy - 27, "D1", 5.5); c.text(sx + 60, sy - 27, "900 x 2100", 5.5)
    c.text(sx, sy - 36, "W1", 5.5); c.text(sx + 60, sy - 36, "1200 x 1200", 5.5)
  notes_y = oy + 6000 * k
  c.text(sx, notes_y, "NOTES", 7, font="F2")
  if wall_height_note:
    c.text(sx, notes_y - 10, wall_height_note, 5.5)
  c.text(sx, notes_y - 20, "ALL DIMENSIONS IN MM", 5.5)
  c.width(1.0).rect(20, 20, w - 40, h - 40)
  c.width(0.5).rect(w - 300, 20, 280, 120)
  c.text(w - 290, 120, "GROUND FLOOR PLAN", 12, font="F2")
  c.text(w - 290, 102, "DWG NO. A-201", 7)
  if scale_text:
    c.text(w - 290, 86, scale_text, 8)
  return PdfBuilder().add_page(w, h, c).build()

EXPECT = {
  "rooms_m2": {"BED ROOM 1": (4500 - 115 - 57.5) * (4000 - 115 - 57.5) / 1e6, },
}
