from __future__ import annotations
from app.modules.drawings_boq.takeoff.prep import ocr_layer, region_ocr, title_block as TB
from app.modules.drawings_boq.takeoff.extract import pageroles as PR
from app.modules.drawings_boq.takeoff.extract import sheet_identity as SID
import time

DPI = 200.0
BAND_HEIGHTS = 2.0               

def boxes(raw) -> list:
  l, b, r, t = raw.cropbox
  w, h = max(r - l, 1.0), max(t - b, 1.0)
  x_cut, y_cut = l + TB.ZONE_RIGHT * w, b + TB.ZONE_BOTTOM * h
  out = [("TITLE_BLOCK_CORNER", (x_cut, b, r, y_cut))]
  words = [x for x in raw.words if abs(((x.angle + 45) % 90) - 45) <= 6]
  
  if words:
    top = max(x.size for x in words)
    big = [x for x in words if x.size >= 0.9 * top]
    cy = sum(x.cy for x in big) / len(big)
    out.append(("LARGEST_LETTERING", (l, cy - BAND_HEIGHTS * top, r, cy + BAND_HEIGHTS * top)))
  out.append(("RIGHT_STRIP", (x_cut, b, r, t)))
  out.append(("BOTTOM_STRIP", (l, b, r, y_cut)))
  return out

def read_floor(page, raw, identity: dict, views: list | None, budget_s: float = SID.TITLE_OCR_BUDGET_S) -> dict:
  if not ocr_layer.available():
    return {"error": "UNAVAILABLE"}
  started = time.monotonic()
  
  tried = []
  for name, box in boxes(raw):
    left = budget_s - (time.monotonic() - started)
    if left < 0.5:
      break
    view = region_ocr.view_box(box, raw.rotation, raw.cropbox)
    words, info = region_ocr.read_region(page, raw.rotation, raw.cropbox, view, dpi=DPI, budget_s=left)
    tried.append({"where": name, "words": len(words), "error": info.get("error")})
    if not words:
      continue
    lines = PR._title_lines(words)
    key, basis = SID.floor_of(identity, raw.words, views, lines)
    if key:
      text = next((t for t, _s in sorted(lines, key=lambda x: -x[1]) if SID._level_of([t])), None)
      return {"floor": key, "basis": basis, "text": (text or "")[:60], "where": name, "seconds": round(time.monotonic() - started, 2), "tried": tried}
  return {"floor": None, "seconds": round(time.monotonic() - started, 2), "tried": tried}

def apply(page, raw, meta: dict) -> None:
  identity = meta.get("identity")
  if not SID.wants_title_ocr(identity):
    return
  found = read_floor(page, raw, identity, meta.get("views"))
  meta["floor_ocr"] = {k: v for k, v in found.items() if k != "floor" or v}
  if not found.get("floor"):
    return
  identity["floor"], identity["floor_basis"] = found["floor"], found["basis"]
  identity.setdefault("evidence", []).append({"floor": found["floor"], "text": found["text"], "ocr": True, "where": found["where"]})
  title = meta.get("title")
  if isinstance(title, dict) and not title.get("level_hint") and not title.get("composite"):
    title["level_hint"] = found["floor"]
