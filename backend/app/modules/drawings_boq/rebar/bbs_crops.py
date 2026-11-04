from __future__ import annotations
import io

ROW_PITCH_PT = 79.0
BBS_PAD_ABOVE = 0.95
BBS_PAD_BELOW = 0.55
BBS_MAX_ROWS = 4
ANCHOR_BOX_PT = (240.0, 200.0)
ANCHOR_LIFT_PT = 50.0
CELL_PAD = 0.10
MIN_BOX_PT = 40.0
TARGET_WIDTH_PX = 900
MAX_SIDE_PX = 4500
ROTATIONS = (0, 90, 180, 270)

class CropError(Exception):
  def __init__(self, code: str, message: str):
    super().__init__(message)
    self.code = code
    self.message = message

Box = tuple 

def clip_box(box: Box, page_w: float, page_h: float) -> Box:
  x0, y0, x1, y1 = box
  x0, x1 = max(0.0, min(x0, x1)), min(page_w, max(x0, x1))
  y0, y1 = max(0.0, min(y0, y1)), min(page_h, max(y0, y1))
  if x1 - x0 < 1 or y1 - y0 < 1:
    raise CropError("OUTSIDE_PAGE", "The place lies outside the page.")
  return (x0, y0, x1, y1)

def _min_size(box: Box, page_w: float, page_h: float) -> Box:
  x0, y0, x1, y1 = box
  if x1 - x0 < MIN_BOX_PT:
    c = (x0 + x1) / 2
    x0, x1 = c - MIN_BOX_PT / 2, c + MIN_BOX_PT / 2
  if y1 - y0 < MIN_BOX_PT:
    c = (y0 + y1) / 2
    y0, y1 = c - MIN_BOX_PT / 2, c + MIN_BOX_PT / 2
  return clip_box((x0, y0, x1, y1), page_w, page_h)

def bbs_box(page_w: float, page_h: float, ys: list) -> Box:
  if not ys:
    raise CropError("NO_POSITION", "The finding does not say where on the schedule page it is.")
  top = page_h - max(ys) - BBS_PAD_ABOVE * ROW_PITCH_PT
  bottom = page_h - min(ys) + BBS_PAD_BELOW * ROW_PITCH_PT
  return clip_box((0.0, top, page_w, bottom), page_w, page_h)

def bbs_rows_on_page(bbs_ref: dict) -> tuple:
  page = bbs_ref.get("page")
  rows = [r for r in (bbs_ref.get("rows") or []) if r.get("y") is not None]
  if page is None and rows:
    page = rows[0].get("page")
  if page is None:
    raise CropError("NO_POSITION", "The finding does not say which schedule page it is on.")
  ys = [float(r["y"]) for r in rows if r.get("page") == page]
  main = bbs_ref.get("y")
  if main is not None:
    main = float(main)
    ys = [main] + [y for y in ys if y != main]
  return int(page), ys[:BBS_MAX_ROWS]

def to_display(x: float, y: float, rotation: int, width: float, height: float) -> tuple:
  if rotation == 0:
    return (x, height - y)
  if rotation == 90:
    return (y, x)
  if rotation == 180:
    return (width - x, y)
  if rotation == 270:
    return (height - y, width - x)
  raise CropError("BAD_ROTATION", f"Unsupported page rotation {rotation}.")

def turn(x: float, y: float, angle: int) -> tuple:
  return {0: (x, y), 90: (y, -x), 180: (-x, -y), 270: (-y, x)}[angle]

def unturn(u: float, v: float, angle: int) -> tuple:
  return {0: (u, v), 90: (-v, u), 180: (-u, -v), 270: (v, -u)}[angle]

def caption_angle(uv: list, anchor: list | None, page_rotation: int) -> int:
  if anchor and len(anchor) == 2:
    order = [page_rotation] + [a for a in ROTATIONS if a != page_rotation]
    u0, v0, u1, v1 = uv
    lo_u, hi_u, lo_v, hi_v = min(u0, u1), max(u0, u1), min(v0, v1), max(v0, v1)
    for a in order:
      u, v = turn(float(anchor[0]), float(anchor[1]), a)
      if lo_u - 2 <= u <= hi_u + 2 and lo_v - 2 <= v <= hi_v + 2:
        return a
  return page_rotation

def drawing_box(ref: dict | None, rotation: int, width: float, height: float, page_w: float, page_h: float) -> Box:
  if not ref:
    raise CropError("NO_DRAWING_REF", "There is no drawing reference for this finding.")
  uv, anchor = ref.get("uv"), ref.get("anchor_native")
  if uv and len(uv) == 4:
    angle = caption_angle(uv, anchor, rotation)
    (nx0, ny0), (nx1, ny1) = unturn(float(uv[0]), float(uv[1]), angle), unturn(float(uv[2]), float(uv[3]), angle)
    (ax, ay), (bx, by) = to_display(nx0, ny0, rotation, width, height), to_display(nx1, ny1, rotation, width, height)
    x0, x1, y0, y1 = min(ax, bx), max(ax, bx), min(ay, by), max(ay, by)
    pad_x, pad_y = (x1 - x0) * CELL_PAD, (y1 - y0) * CELL_PAD
    return _min_size((x0 - pad_x, y0 - pad_y, x1 + pad_x, y1 + pad_y), page_w, page_h)
  if anchor and len(anchor) == 2:
    cx, cy = to_display(float(anchor[0]), float(anchor[1]), rotation, width, height)
    w, h = ANCHOR_BOX_PT
    cy -= ANCHOR_LIFT_PT 
    return clip_box((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), page_w, page_h)
  raise CropError("NO_GEOMETRY", "The drawing reference names the page but not the place on it.")

def render_crop(pdf_bytes: bytes, page_no: int, make_box) -> bytes:
  import pypdfium2 as pdfium
  try:
    pdf = pdfium.PdfDocument(pdf_bytes)
  except Exception as exc:
    raise CropError("UNREADABLE", "The PDF could not be opened.") from exc
  
  try:
    if page_no < 1 or page_no > len(pdf):
      raise CropError("NO_PAGE", f"Page {page_no} is not in the file.")
    page = pdf[page_no - 1]
    try:
      left, bottom, right, top = page.get_mediabox()
      page_w, page_h = page.get_size()
      info = {"rotation": int(page.get_rotation()) % 360, "width": float(right - left), "height": float(top - bottom), "page_w": float(page_w), "page_h": float(page_h)}
      x0, y0, x1, y1 = make_box(info)
      scale = min(max(1.0, TARGET_WIDTH_PX / (x1 - x0)), 4.0, MAX_SIDE_PX / max(page_w, page_h))
      image = page.render(scale=scale).to_pil().convert("RGB")
      box = tuple(int(round(v * scale)) for v in (x0, y0, x1, y1))
      box = (max(0, box[0]), max(0, box[1]), min(image.width, box[2]), min(image.height, box[3]))
      out = io.BytesIO()
      image.crop(box).save(out, format="PNG", optimize=True)
      return out.getvalue()
    finally:
      page.close()
  finally:
    pdf.close()

def bbs_crop(pdf_bytes: bytes, bbs_ref: dict) -> bytes:
  page_no, ys = bbs_rows_on_page(bbs_ref)
  return render_crop(pdf_bytes, page_no, lambda i: bbs_box(i["page_w"], i["page_h"], ys))

def drawing_crop(pdf_bytes: bytes, ref: dict | None) -> bytes:
  if not ref:
    raise CropError("NO_DRAWING_REF", "There is no drawing reference for this finding.")
  if not ref.get("page"):
    raise CropError("NO_PAGE", "The drawing reference does not name a page.")
  return render_crop(pdf_bytes, int(ref["page"]), lambda i: drawing_box(ref, i["rotation"], i["width"], i["height"], i["page_w"], i["page_h"]))
