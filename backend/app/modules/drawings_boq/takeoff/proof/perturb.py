from __future__ import annotations
import io
import math
from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.generic import RectangleObject, ContentStream

def _rewrite(pdf: bytes, fn) -> bytes:
  reader = PdfReader(io.BytesIO(pdf))
  writer = PdfWriter()
  
  for i, page in enumerate(reader.pages):
    fn(i, page, reader)
    writer.add_page(page)
  out = io.BytesIO()
  writer.write(out)
  return out.getvalue()

def rotate_view(pdf: bytes, degrees: int) -> bytes:
  if degrees % 90:
    raise ValueError("A page turns by quarter turns.")
  return _rewrite(pdf, lambda i, p, r: p.rotate(degrees))

def turn_content(pdf: bytes, degrees: int) -> bytes:
  if degrees not in (90, 180, 270):
    raise ValueError("The drawing turns by 90, 180 or 270 degrees.")

  def fn(i, page, reader):
    box = page.mediabox
    w, h = float(box.width), float(box.height)
    if degrees == 90:
      t, size = Transformation().rotate(90).translate(tx=h, ty=0), (h, w)
    elif degrees == 180:
      t, size = Transformation().rotate(180).translate(tx=w, ty=h), (w, h)
    else:
      t, size = Transformation().rotate(270).translate(tx=0, ty=w), (h, w)
    page.add_transformation(t)
    page.mediabox = RectangleObject([0, 0, size[0], size[1]])
    page.cropbox = RectangleObject([0, 0, size[0], size[1]])
  return _rewrite(pdf, fn)

def rescale(pdf: bytes, factor: float) -> bytes:
  """The whole page, drawing and paper, is made `factor` times as large (0.5 is an A1 sheet plotted on A2, which turns a printed 1:100 into 1:200)."""
  if factor <= 0:
    raise ValueError("The factor must be above zero.")
  return _rewrite(pdf, lambda i, p, r: p.scale_by(factor))

def crop(pdf: bytes, left: float, bottom: float, right: float, top: float) -> bytes:
  if not (0 <= left < right <= 1 and 0 <= bottom < top <= 1):
    raise ValueError("The box is fractions of the page: left < right and bottom < top, all between 0 and 1.")

  def fn(i, page, reader):
    b = page.mediabox
    x0, y0, w, h = float(b.left), float(b.bottom), float(b.width), float(b.height)
    box = RectangleObject([x0 + left * w, y0 + bottom * h, x0 + right * w, y0 + top * h])
    page.cropbox = box
  return _rewrite(pdf, fn)

def _mul(a, b):
  """Matrix a then b (PDF row-vector convention): both (a, b, c, d, e, f)."""
  return (a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3], a[2] * b[0] + a[3] * b[2], a[2] * b[1] + a[3] * b[3],
    a[4] * b[0] + a[5] * b[2] + b[4], a[4] * b[1] + a[5] * b[3] + b[5])

def _strip_text(page, reader, keep) -> int:
  stream = ContentStream(page.get_contents(), reader)
  ctm, stack, out, block, removed, pos = (1, 0, 0, 1, 0, 0), [], [], None, 0, None
  
  for operands, op in stream.operations:
    if op == b"q":
      stack.append(ctm)
    elif op == b"Q":
      ctm = stack.pop() if stack else (1, 0, 0, 1, 0, 0)
    elif op == b"cm":
      ctm = _mul(tuple(float(v) for v in operands), ctm)
    if op == b"BT":
      block, pos = [], None
      continue
  
    if block is not None:
      block.append((operands, op))
      if pos is None and op in (b"Tm", b"Td", b"TD"):
        e, f = (float(operands[4]), float(operands[5])) if op == b"Tm" else (float(operands[0]), float(operands[1]))
        pos = (e * ctm[0] + f * ctm[2] + ctm[4], e * ctm[1] + f * ctm[3] + ctm[5])
      if op == b"ET":
        if keep is not None and pos is not None and keep(*pos):
          out.append(([], b"BT"))
          out.extend(block)
          
        else:
          removed += 1
        block = None
      continue
    out.append((operands, op))
  stream.operations = out
  page.replace_contents(stream)
  return removed

def strip_text(pdf: bytes) -> bytes:
  """Every text block of the page content is removed: the drawing is only lines. Text inside form objects (a title block placed as a form, say) is not touched."""
  return _rewrite(pdf, lambda i, p, r: _strip_text(p, r, None))

def drop_title_block(pdf: bytes, left: float = 0.72, bottom: float = 0.0, right: float = 1.0, top: float = 0.22) -> bytes:
  """The text in the box (fractions of the page: by default the lower right corner, where a title block usually is) is removed; the lines stay."""
  def fn(i, page, reader):
    b = page.mediabox
    x0, y0, w, h = float(b.left), float(b.bottom), float(b.width), float(b.height)
    lo_x, hi_x, lo_y, hi_y = x0 + left * w, x0 + right * w, y0 + bottom * h, y0 + top * h
    _strip_text(page, reader, lambda x, y: not (lo_x <= x <= hi_x and lo_y <= y <= hi_y))
  return _rewrite(pdf, fn)

def turn_by_map(w: float, h: float, degrees: float) -> tuple:
  a = math.radians(degrees)
  c, s = math.cos(a), math.sin(a)
  corners = ((0, 0), (w, 0), (w, h), (0, h))
  mx = min(c * x - s * y for x, y in corners)
  my = min(s * x + c * y for x, y in corners)
  return (lambda x, y: (c * x - s * y - mx, s * x + c * y - my)), (lambda x, y: (c * (x + mx) + s * (y + my), -s * (x + mx) + c * (y + my)))

def turn_by(pdf: bytes, degrees: float) -> bytes:
  
  def fn(i, page, reader):
    box = page.mediabox
    w, h = float(box.width), float(box.height)
    fwd, _ = turn_by_map(w, h, degrees)
    ends = [fwd(x, y) for x, y in ((0, 0), (w, 0), (w, h), (0, h))]
    nw, nh = max(p[0] for p in ends), max(p[1] for p in ends)
    shift = fwd(0.0, 0.0)
    page.add_transformation(Transformation().rotate(degrees).translate(tx=shift[0], ty=shift[1]))
    page.mediabox = RectangleObject([0, 0, nw, nh])
    page.cropbox = RectangleObject([0, 0, nw, nh])
  return _rewrite(pdf, fn)

SUITE = (
  ("rotate view 90", lambda p: rotate_view(p, 90)),
  ("rotate view 180", lambda p: rotate_view(p, 180)),
  ("rotate view 270", lambda p: rotate_view(p, 270)),
  ("turn drawing 90", lambda p: turn_content(p, 90)),
  ("turn drawing 270", lambda p: turn_content(p, 270)),
  ("shrink to half size", lambda p: rescale(p, 0.5)),
  ("enlarge to double size", lambda p: rescale(p, 2.0)),
  ("drop the title block", drop_title_block),
  ("strip all text", strip_text),
)

SUITE_ANGLED = tuple((f"turn drawing {d:+g}", (lambda p, d=d: turn_by(p, d))) for d in (3, 12, 30, -20, 77))
