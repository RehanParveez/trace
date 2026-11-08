from __future__ import annotations
import io
import math
from app.modules.drawings_boq.takeoff.prep.extract import PdfOpenError, open_document
from app.core.exceptions import TraceException
from PIL import Image
from app.modules.drawings_boq.takeoff.crops.render import _RENDER
from app.modules.drawings_boq.takeoff.prep import title_block as TB

ZONE = "TITLE_BLOCK_STRIPS"
PAGE_ZONE = "PAGE"
BOX_ZONE = "BOX"
SHEET_ZONE = "SHEET"
LONG_SIDE_PX = 1500
MAX_SCALE = 2.0
GAP_PX = 12
PAGE_LONG_SIDE_PX = 1568
BOX_LONG_SIDE_PX = 1568
BOX_MAX_SCALE = 4.0
MIN_BOX_SIDE = 2.0

def _open(contents: bytes, page_no: int):
  try:
    doc = open_document(contents)
  except PdfOpenError as exc:
    raise TraceException(exc.message, status_code=422, code=exc.code)
  if page_no < 1 or page_no > len(doc):
    doc.close()
    raise TraceException("That page is not in the drawing.", status_code=404, code="SHEET_PAGE_MISSING")
  return doc

def _png(img: Image.Image) -> bytes:
  out = io.BytesIO()
  img.save(out, "PNG", optimize=True)
  return out.getvalue()

def title_block_region() -> dict:
  return {"zone": ZONE, "right_share": round(1.0 - TB.ZONE_RIGHT, 4), "bottom_share": TB.ZONE_BOTTOM, "long_side_px": LONG_SIDE_PX}

def page_region() -> dict:
  return {"zone": PAGE_ZONE, "long_side_px": PAGE_LONG_SIDE_PX}

def sheet_region() -> dict:
  return {"zone": SHEET_ZONE, "strips": title_block_region(), "page": page_region()}

def box_region(box) -> dict:
  return {"zone": BOX_ZONE, "box": [round(float(v), 1) for v in box], "long_side_px": BOX_LONG_SIDE_PX}

def title_block_picture(contents: bytes, page_no: int) -> tuple[bytes, dict]:
  doc = _open(contents, page_no)
  try:
    page = doc[page_no - 1]
    width, height = (float(v) for v in page.get_size())
    strip_w, strip_h = width * (1.0 - TB.ZONE_RIGHT), height * TB.ZONE_BOTTOM
    scale = min(MAX_SCALE, LONG_SIDE_PX / (max(width, height) * 1.3))

    with _RENDER:
      bottom = page.render(scale=scale, crop=(0, 0, 0, height - strip_h)).to_pil().convert("RGB")
      right = page.render(scale=scale, crop=(width - strip_w, 0, 0, 0)).to_pil().convert("RGB")
    canvas = Image.new("RGB", (bottom.width + GAP_PX + right.width, max(bottom.height, right.height)), (255, 255, 255))
    canvas.paste(bottom, (0, 0))
    canvas.paste(right, (bottom.width + GAP_PX, 0))
    boxes = [[0.0, round(height - strip_h, 2), round(width, 2), round(height, 2)], [round(width - strip_w, 2), 0.0, round(width, 2), round(height, 2)]]
    info = {"zone": ZONE, "scale": round(scale, 3), "width_px": canvas.width, "height_px": canvas.height,
      "bottom_share": TB.ZONE_BOTTOM, "right_share": round(1.0 - TB.ZONE_RIGHT, 2), "page_pt": [round(width, 2), round(height, 2)], "boxes": boxes}
    return _png(canvas), info
  finally:
    doc.close()

def page_picture(contents: bytes, page_no: int, long_side_px: int = PAGE_LONG_SIDE_PX) -> tuple[bytes, dict]:
  doc = _open(contents, page_no)
  try:
    page = doc[page_no - 1]
    width, height = (float(v) for v in page.get_size())
    scale = min(MAX_SCALE, long_side_px / max(width, height))
    with _RENDER:
      img = page.render(scale=scale).to_pil().convert("RGB")
    info = {"zone": PAGE_ZONE, "scale": round(scale, 3), "width_px": img.width, "height_px": img.height, "page_pt": [round(width, 2), round(height, 2)], "box_pt": [0.0, 0.0, round(width, 2), round(height, 2)]}
    return _png(img), info
  finally:
    doc.close()

def box_picture(contents: bytes, page_no: int, box, long_side_px: int = BOX_LONG_SIDE_PX) -> tuple[bytes, dict]:
  doc = _open(contents, page_no)
  try:
    page = doc[page_no - 1]
    width, height = (float(v) for v in page.get_size())
    x0, y0, x1, y1 = (float(v) for v in box)
    x0, x1 = max(0.0, min(x0, x1)), min(width, max(x0, x1))
    y0, y1 = max(0.0, min(y0, y1)), min(height, max(y0, y1))
    if not all(math.isfinite(v) for v in (x0, y0, x1, y1)) or x1 - x0 < MIN_BOX_SIDE or y1 - y0 < MIN_BOX_SIDE:
      raise TraceException("That box is not on the page.", status_code=422, code="AI_BOX_OFF_PAGE")
    scale = min(BOX_MAX_SCALE, long_side_px / max(x1 - x0, y1 - y0))
    with _RENDER:
      img = page.render(scale=scale, crop=(x0, height - y1, width - x1, y0)).to_pil().convert("RGB")
    info = {"zone": BOX_ZONE, "scale": round(scale, 3), "width_px": img.width, "height_px": img.height, "page_pt": [round(width, 2), round(height, 2)], "box_pt": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)]}
    return _png(img), info
  finally:
    doc.close()

def zone_picture(contents: bytes, page_no: int, zone) -> tuple[bytes, dict]:
  doc = _open(contents, page_no)
  try:
    width, height = (float(v) for v in doc[page_no - 1].get_size())
  finally:
    doc.close()
  u0, v0, u1, v1 = (float(v) for v in zone)
  return box_picture(contents, page_no, (u0 * width, v0 * height, u1 * width, v1 * height))

def text_in_boxes(contents: bytes, page_no: int, boxes) -> str | None:
  doc = _open(contents, page_no)
  try:
    page = doc[page_no - 1]
    if int(page.get_rotation() or 0) % 360:
      return None
    left, bottom, right, top = (float(v) for v in page.get_cropbox())
    textpage = page.get_textpage()
    try:
      parts = []
      for x0, y0, x1, y1 in boxes:
        parts.append(textpage.get_text_bounded(left=left + x0, bottom=top - y1, right=left + x1, top=top - y0))
      return "\n".join(parts)
    finally:
      textpage.close()
  finally:
    doc.close()

def page_text(contents: bytes, page_no: int, page_pt) -> str | None:
  width, height = (float(v) for v in page_pt)
  return text_in_boxes(contents, page_no, [[0.0, 0.0, width, height]])

NOTE_GRIDS = ((350, 1, 1), (800, 2, 1), (10 ** 9, 2, 2))
NOTE_TILE_OVERLAP = 0.04

def note_grid(words: int) -> tuple:
  return next((cols, rows) for limit, cols, rows in NOTE_GRIDS if words <= limit)

def note_region() -> dict:
  return {"zone": "NOTE_TILES", "grids": [list(g) for g in NOTE_GRIDS], "overlap": NOTE_TILE_OVERLAP, "long_side_px": BOX_LONG_SIDE_PX}

def schedule_region() -> dict:
  return {**note_region(), "zone": "SCHEDULE_TILES"}

def note_tiles(page_pt, words: int) -> list:
  width, height = (float(v) for v in page_pt)
  cols, rows = note_grid(words)
  dx, dy = width * NOTE_TILE_OVERLAP, height * NOTE_TILE_OVERLAP
  return [[max(0.0, c * width / cols - dx), max(0.0, r * height / rows - dy), min(width, (c + 1) * width / cols + dx), min(height, (r + 1) * height / rows + dy)] for r in range(rows) for c in range(cols)]

