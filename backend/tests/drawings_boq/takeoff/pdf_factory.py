from __future__ import annotations
import math
import zlib

def _num(v: float) -> str:
  s = f"{v:.4f}".rstrip("0").rstrip(".")
  return s if s not in ("", "-0") else "0"

def _esc(text: str) -> str:
  return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

class Canvas:

  def __init__(self):
    self.ops: list[str] = []

  def raw(self, op: str):
    self.ops.append(op)
    return self

  def width(self, w: float):
    self.ops.append(f"{_num(w)} w")
    return self

  def gray(self, g: float, stroke: bool = True, fill: bool = False):
    if stroke:
      self.ops.append(f"{_num(g)} G")
    if fill:
      self.ops.append(f"{_num(g)} g")
    return self

  def line(self, x1, y1, x2, y2, w: float | None = None):
    if w is not None:
      self.width(w)
    self.ops.append(f"{_num(x1)} {_num(y1)} m {_num(x2)} {_num(y2)} l S")
    return self

  def polyline(self, pts, close: bool = False, fill: bool = False, stroke: bool = True):
    first, rest = pts[0], pts[1:]
    s = f"{_num(first[0])} {_num(first[1])} m " + " ".join(f"{_num(x)} {_num(y)} l" for x, y in rest)
    if close:
      s += " h"
    s += " " + ("B" if (fill and stroke) else "f" if fill else "S")
    if close and not fill and stroke:
      s = s[:-1] + "s"
    self.ops.append(s)
    return self

  def rect(self, x, y, w, h, fill: bool = False, stroke: bool = True):
    self.ops.append(f"{_num(x)} {_num(y)} {_num(w)} {_num(h)} re " + ("B" if (fill and stroke) else "f" if fill else "S"))
    return self

  def circle(self, cx, cy, r, fill: bool = False, stroke: bool = True):
    k = 0.5522847498 * r
    p = [(cx + r, cy), (cx + r, cy + k, cx + k, cy + r, cx, cy + r), (cx - k, cy + r, cx - r, cy + k, cx - r, cy),
         (cx - r, cy - k, cx - k, cy - r, cx, cy - r), (cx + k, cy - r, cx + r, cy - k, cx + r, cy)]
    s = f"{_num(p[0][0])} {_num(p[0][1])} m " + " ".join(
      " ".join(_num(v) for v in seg) + " c" for seg in p[1:]) + " h " + ("B" if (fill and stroke) else "f" if fill else "S")
    self.ops.append(s)
    return self

  def text(self, x, y, s: str, size: float = 10, angle: float = 0, font: str = "F1"):
    a = math.radians(angle)
    c, sn = math.cos(a), math.sin(a)
    self.ops.append(f"BT /{font} {_num(size)} Tf {c:.6f} {sn:.6f} {-sn:.6f} {c:.6f} {_num(x)} {_num(y)} Tm ({_esc(s)}) Tj ET")
    return self

  def hidden_text(self, x, y, s: str, size: float = 10):
    self.ops.append(f"BT /F1 {_num(size)} Tf 3 Tr 1 0 0 1 {_num(x)} {_num(y)} Tm ({_esc(s)}) Tj ET")
    return self

  def image(self, name: str, x, y, w, h):
    self.ops.append(f"q {_num(w)} 0 0 {_num(h)} {_num(x)} {_num(y)} cm /{name} Do Q")
    return self

  def form(self, name: str, a=1, b=0, c=0, d=1, e=0, f=0):
    self.ops.append(f"q {_num(a)} {_num(b)} {_num(c)} {_num(d)} {_num(e)} {_num(f)} cm /{name} Do Q")
    return self

  def push(self):
    self.ops.append("q")
    return self

  def pop(self):
    self.ops.append("Q")
    return self

  def dimension(self, x1, y1, x2, y2, value: str, offset: float = 14, size: float = 6, tick: float = 3, ext_gap: float = 2,
     split_text: bool = True, terminator: str = "tick"):
   
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length
    nx, ny = -uy, ux
    ax, ay = x1 + nx * offset, y1 + ny * offset
    bx, by = x2 + nx * offset, y2 + ny * offset
    self.line(x1 + nx * ext_gap, y1 + ny * ext_gap, ax + nx * 2, ay + ny * 2)
    self.line(x2 + nx * ext_gap, y2 + ny * ext_gap, bx + nx * 2, by + ny * 2)
    mx, my = (ax + bx) / 2, (ay + by) / 2
    tw = len(value) * size * 0.55
    if split_text and length > tw + 8:
      g = tw / 2 + 2
      self.line(ax, ay, mx - ux * g, my - uy * g)
      self.line(mx + ux * g, my + uy * g, bx, by)
      
    else:
      self.line(ax, ay, bx, by)
    if terminator == "tick":
      for px, py in ((ax, ay), (bx, by)):
        self.line(px - (ux + nx) * tick * 0.7, py - (uy + ny) * tick * 0.7, px + (ux + nx) * tick * 0.7, py + (uy + ny) * tick * 0.7)
    elif terminator == "arrow":
      for px, py, s in ((ax, ay, 1), (bx, by, -1)):
        tipx, tipy = px, py
        b1 = (px + s * ux * tick * 1.6 + nx * tick * 0.5, py + s * uy * tick * 1.6 + ny * tick * 0.5)
        b2 = (px + s * ux * tick * 1.6 - nx * tick * 0.5, py + s * uy * tick * 1.6 - ny * tick * 0.5)
        self.polyline([(tipx, tipy), b1, b2], close=True, fill=True, stroke=False)
    ang = math.degrees(math.atan2(uy, ux))
    if ang > 90 or ang < -90:
      ang += 180
    
    shift = 0 if split_text and length > tw + 8 else size * 0.9
    cx, cy = mx + nx * shift, my + ny * shift
    a = math.radians(ang)
    tx = cx - (math.cos(a) * tw / 2) + (math.sin(a) * size * 0.35)
    ty = cy - (math.sin(a) * tw / 2) - (math.cos(a) * size * 0.35)
    self.text(tx, ty, value, size, ang)
    return self

  def content(self) -> bytes:
    return ("\n".join(self.ops) + "\n").encode("latin-1")

def raster_image(width: int, height: int, gray: int = 200, noise: bool = True) -> tuple[bytes, dict]:
  rows = bytearray()
  for yy in range(height):
    for xx in range(width):
      rows.append((gray + ((xx * 7 + yy * 13) % 40 if noise else 0)) % 256)
  return zlib.compress(bytes(rows)), {"Width": width, "Height": height}

class PdfBuilder:
  def __init__(self):
    self.pages: list[dict] = []

  def add_page(self, width: float, height: float, canvas: Canvas | bytes | None = None, *, rotate: int = 0,
    origin: tuple[float, float] = (0, 0), crop: tuple[float, float, float, float] | None = None,
    user_unit: float | None = None, images: dict | None = None, forms: dict | None = None):
    content = canvas.content() if isinstance(canvas, Canvas) else (canvas or b"")
    self.pages.append(dict(w=width, h=height, content=content, rotate=rotate, origin=origin, crop=crop, user_unit=user_unit,
      images=images or {}, forms=forms or {}))
    return self

  def build(self) -> bytes:
    objs: dict[int, bytes] = {}
    next_id = [5]

    def new_id() -> int:
      i = next_id[0]
      next_id[0] += 1
      return i

    objs[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    objs[4] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"
    page_ids = []
    for p in self.pages:
      xobj = []
      for name, (data, meta) in p["images"].items():
        i = new_id()
        objs[i] = (f"<< /Type /XObject /Subtype /Image /Width {meta['Width']} /Height {meta['Height']} /ColorSpace /DeviceGray "
          f"/BitsPerComponent 8 /Filter /FlateDecode /Length {len(data)} >>\nstream\n").encode() + data + b"\nendstream"
        xobj.append(f"/{name} {i} 0 R")
      for name, (stream, bbox) in p["forms"].items():
        i = new_id()
        s = stream.content() if isinstance(stream, Canvas) else stream
        objs[i] = (f"<< /Type /XObject /Subtype /Form /BBox [{' '.join(_num(v) for v in bbox)}] /Resources << /Font << /F1 3 0 R >> >> "
          f"/Length {len(s)} >>\nstream\n").encode() + s + b"\nendstream"
        xobj.append(f"/{name} {i} 0 R")
      cid = new_id()
      c = p["content"]
      objs[cid] = f"<< /Length {len(c)} >>\nstream\n".encode() + c + b"\nendstream"
      pid = new_id()
      
      ox, oy = p["origin"]
      media = f"[{_num(ox)} {_num(oy)} {_num(ox + p['w'])} {_num(oy + p['h'])}]"
      extra = ""
      if p["crop"]:
        extra += f" /CropBox [{' '.join(_num(v) for v in p['crop'])}]"
      if p["rotate"]:
        extra += f" /Rotate {p['rotate']}"
      if p["user_unit"]:
        extra += f" /UserUnit {_num(p['user_unit'])}"
      res = "/Font << /F1 3 0 R /F2 4 0 R >>"
      
      if xobj:
        res += " /XObject << " + " ".join(xobj) + " >>"
      objs[pid] = (f"<< /Type /Page /Parent 2 0 R /MediaBox {media}{extra} /Contents {cid} 0 R /Resources << {res} >> >>").encode()
      page_ids.append(pid)
    objs[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objs[2] = (f"<< /Type /Pages /Kids [{' '.join(f'{i} 0 R' for i in page_ids)}] /Count {len(page_ids)} >>").encode()
    out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    
    offsets = {}
    for i in sorted(objs):
      offsets[i] = len(out)
      out += f"{i} 0 obj\n".encode() + objs[i] + b"\nendobj\n"
    xref = len(out)
    n = max(objs) + 1
    out += f"xref\n0 {n}\n".encode() + b"0000000000 65535 f \n"
    for i in range(1, n):
      out += f"{offsets[i]:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {n} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)

PT_MM = 25.4 / 72.0

def _ftin(mm: float) -> str:
  total = round(mm / 25.4)
  return f"{total // 12}'-{total % 12}\""

def make_plan(drawn_ratio: float = 100.0, declared: str | None = "1:100", unit: str = "mm", paper: tuple = (1190.55, 841.89),
  terminator: str = "tick", split_text: bool = True, bad_dims: dict | None = None, units_note: str | None = "ALL DIMENSIONS IN MM",
  title: str | None = "GROUND FLOOR PLAN", sheet_no: str | None = "A-101", dims: bool = True, rotate: int = 0,
  origin: tuple = (0, 0), user_unit: float | None = None) -> bytes:
  
  k = 1.0 / (drawn_ratio * PT_MM)  
  ox, oy = origin[0] + 140.0, origin[1] + 160.0
  xs = [0, 3600, 7800, 10800]
  ys = [0, 4500, 7200]
  def P(x, y):
    return (ox + x * k, oy + y * k)
  c = Canvas()
  c.gray(0.0).width(0.35)
  t = 115  
  
  for off in (-t, t):
    x0, y0 = P(xs[0] - off, ys[0] - off)
    x1, y1 = P(xs[-1] + off, ys[-1] + off)
    c.rect(x0, y0, x1 - x0, y1 - y0)
  for xv in xs[1:-1]:
    for off in (-t, t):
      a = P(xv + off, ys[0] + t)
      b = P(xv + off, ys[-1] - t)
      c.line(a[0], a[1], b[0], b[1])
  for yv in ys[1:-1]:
    for off in (-t, t):
      a = P(xs[0] + t, yv + off)
      b = P(xs[1] - t, yv + off)
      c.line(a[0], a[1], b[0], b[1])
 
  n = 0
  for xv in xs:
    for yv in ys:
      p = P(xv - 115, yv - 115)
      c.rect(p[0], p[1], 230 * k, 230 * k, fill=True, stroke=True)
      n += 1
      tx, ty = P(xv + 160, yv + 160)
      c.text(tx, ty, "C2" if (xv, yv) == (xs[1], ys[1]) else "C1", 5)
  c.text(*P(1500, 2200), "BEDROOM", 6)
  
  if dims:
    top = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
    for i, v in enumerate(top):
      a = P(xs[i], ys[-1] + t + 200)
      b = P(xs[i + 1], ys[-1] + t + 200)
      txt = str(v) if unit == "mm" else (f"{v / 1000:.2f}" if unit == "m" else _ftin(v))
      if bad_dims and ("top", i) in bad_dims:
        txt = bad_dims[("top", i)]
      c.dimension(a[0], a[1], b[0], b[1], txt, offset=16, size=5.5, terminator=terminator, split_text=split_text)
    left = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
    
    for i, v in enumerate(left):
      a = P(xs[0] - t - 200, ys[i])
      b = P(xs[0] - t - 200, ys[i + 1])
      txt = str(v) if unit == "mm" else (f"{v / 1000:.2f}" if unit == "m" else _ftin(v))
      if bad_dims and ("left", i) in bad_dims:
        txt = bad_dims[("left", i)]
      c.dimension(a[0], a[1], b[0], b[1], txt, offset=16, size=5.5, terminator=terminator, split_text=split_text)
      
  w, h = paper
  c.gray(0.0).width(1.0).rect(origin[0] + 20, origin[1] + 20, w - 40, h - 40)
  c.width(0.5).rect(origin[0] + w - 300, origin[1] + 20, 280, 120)
  bx = origin[0] + w - 290
  by = origin[1] + 120
  if title:
    c.text(bx, by, title, 12, font="F2")
  if sheet_no:
    c.text(bx, by - 18, f"DWG NO. {sheet_no}", 7)
  if declared:
    c.text(bx, by - 34, f"SCALE {declared}", 8)
  if units_note:
    c.text(bx, by - 48, units_note, 6)
  return PdfBuilder().add_page(w, h, c, rotate=rotate, origin=origin, user_unit=user_unit).build()