from __future__ import annotations
import io
import threading
from app.modules.drawings_boq.takeoff.prep.texts import to_visual
from PIL import Image, ImageDraw
from app.modules.drawings_boq.takeoff.prep.extract import PdfOpenError, open_document
from app.core.exceptions import TraceException
from app.modules.drawings_boq.takeoff.crops.box import candidate_box, points_of

MIN_PX = 160
MAX_PX = 1000
MARK = (214, 40, 40)
HALO = (255, 255, 255)
RING_PX = 9
_RENDER = threading.Lock()

def in_view(geometry: dict, crop: tuple, rotation: int, width: float, height: float) -> dict:
  def move(ring):
    return [[u * width, v * height] for u, v in (to_visual(x, y, crop, rotation) for x, y in ring)]
  g = geometry or {}
  if g.get("outer"):
    return {"outer": move(points_of({"outer": g["outer"]}))}
  return {"points": move(points_of({"points": g.get("points")}))}

def _mark(img: Image.Image, box: tuple, kind: str, geometry: dict) -> Image.Image:
  x0, y0, x1, y1 = box
  sx, sy = img.width / (x1 - x0), img.height / (y1 - y0)
  pts = [((x - x0) * sx, (y - y0) * sy) for x, y in points_of(geometry)]
  layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
  dr = ImageDraw.Draw(layer)

  if kind == "AREA" and len(pts) >= 3:
    dr.polygon(pts, fill=MARK + (46,))
    ring = pts + [pts[0]]
    dr.line(ring, fill=HALO + (255,), width=5, joint="curve")
    dr.line(ring, fill=MARK + (255,), width=2, joint="curve")
  elif kind == "LENGTH" and len(pts) >= 2:
    dr.line(pts, fill=HALO + (255,), width=6, joint="curve")
    dr.line(pts, fill=MARK + (255,), width=3, joint="curve")
    for x, y in (pts[0], pts[-1]):
      dr.ellipse((x - 4, y - 4, x + 4, y + 4), fill=MARK + (255,), outline=HALO + (255,))
  else:
    for x, y in pts:
      dr.ellipse((x - RING_PX - 1, y - RING_PX - 1, x + RING_PX + 1, y + RING_PX + 1), outline=HALO + (255,), width=5)
      dr.ellipse((x - RING_PX, y - RING_PX, x + RING_PX, y + RING_PX), outline=MARK + (255,), width=2)
  return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")

def render_crop(contents: bytes, page_no: int, kind: str, geometry: dict, size_px: int) -> bytes:
  size_px = max(MIN_PX, min(MAX_PX, int(size_px)))
  try:
    doc = open_document(contents)
  except PdfOpenError as exc:
    raise TraceException(exc.message, status_code=422, code=exc.code)
  try:
    if page_no < 1 or page_no > len(doc):
      raise TraceException("That page is not in the drawing.", status_code=404, code="SHEET_PAGE_MISSING")
    page = doc[page_no - 1]
    width, height = page.get_size()
    crop = tuple(float(v) for v in page.get_cropbox())
    seen = in_view(geometry, crop, int(page.get_rotation() or 0) % 360, float(width), float(height))
    box = candidate_box(seen, float(width), float(height))
    if box is None:
      raise TraceException("This item has no position on the sheet, so there is nothing to show.", status_code=422, code="CROP_NO_POSITION")

    x0, y0, x1, y1 = box
    scale = size_px / max(x1 - x0, y1 - y0)
    with _RENDER:
      bitmap = page.render(scale=scale, crop=(x0, height - y1, width - x1, y0))
      img = bitmap.to_pil().convert("RGB")
    img = _mark(img, box, kind, seen)
    out = io.BytesIO()
    img.save(out, "PNG")
    return out.getvalue()
  finally:
    doc.close()
