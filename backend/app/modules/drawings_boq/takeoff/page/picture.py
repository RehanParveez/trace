from __future__ import annotations

COLOURS = {"VIEW": (0, 120, 255), "SCHEDULE": (0, 170, 60), "LEGEND": (170, 0, 200), "NOTES": (230, 140, 0), "SECTION_PICTURE": (220, 0, 0), "TITLE_BLOCK": (110, 110, 110), "CALLOUT": (0, 170, 170)}

def draw(pdf_page, regions: list, truth: list | None = None, scale: float = 1.5):
  from PIL import ImageDraw
  img = pdf_page.render(scale=scale).to_pil().convert("RGB")
  d = ImageDraw.Draw(img)
  W, H = pdf_page.get_size()
  rot = int(pdf_page.get_rotation() or 0) % 360
  x0, y0, x1, y1 = (float(v) for v in pdf_page.get_cropbox())
  
  def to_px(x: float, y: float) -> tuple:
    if rot == 90:
      u, v = y - y0, x - x0
    elif rot == 180:
      u, v = x1 - x, y - y0
    elif rot == 270:
      u, v = y1 - y, x1 - x
    else:
      u, v = x - x0, y1 - y
    return u * scale, v * scale
  
  def rect(box, colour, width=2, dash=False):
    pts = [to_px(box[0], box[1]), to_px(box[2], box[1]), to_px(box[2], box[3]), to_px(box[0], box[3])]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    a, b, c, e = min(xs), min(ys), max(xs), max(ys)
    
    if not dash:
      d.rectangle([a, b, c, e], outline=colour, width=width)
      return
    step = 8
    for t in range(int(a), int(c), step * 2):
      d.line([(t, b), (min(t + step, c), b)], fill=colour, width=width)
      d.line([(t, e), (min(t + step, c), e)], fill=colour, width=width)
    for t in range(int(b), int(e), step * 2):
      d.line([(a, t), (a, min(t + step, e))], fill=colour, width=width)
      d.line([(c, t), (c, min(t + step, e))], fill=colour, width=width)
  for r in regions:
    kind = r["kind"] if isinstance(r, dict) else r.kind
    box = r["box"] if isinstance(r, dict) else r.box
    rect(box, COLOURS.get(kind, (0, 0, 0)))
  for box in truth or []:
    rect(box, (0, 0, 0), 1, True)
  return img
