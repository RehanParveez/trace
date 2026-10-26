from __future__ import annotations
import io
from app.modules.drawings_boq.takeoff.prep.extract import PdfOpenError, open_document
from app.core.exceptions import TraceException
from PIL import Image
from app.modules.drawings_boq.takeoff.crops.render import _RENDER
from app.modules.drawings_boq.takeoff.prep import title_block as TB

ZONE = "TITLE_BLOCK_STRIPS"
LONG_SIDE_PX = 1500
MAX_SCALE = 2.0
GAP_PX = 12

def title_block_picture(contents: bytes, page_no: int) -> tuple[bytes, dict]:
  try:
    doc = open_document(contents)
  except PdfOpenError as exc:
    raise TraceException(exc.message, status_code=422, code=exc.code)
  try:
    if page_no < 1 or page_no > len(doc):
      raise TraceException("That page is not in the drawing.", status_code=404, code="SHEET_PAGE_MISSING")
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
    out = io.BytesIO()
    canvas.save(out, "PNG", optimize=True)
    info = {"zone": ZONE, "scale": round(scale, 3), "width_px": canvas.width, "height_px": canvas.height,
      "bottom_share": TB.ZONE_BOTTOM, "right_share": round(1.0 - TB.ZONE_RIGHT, 2)}
    return out.getvalue(), info
  finally:
    doc.close()
