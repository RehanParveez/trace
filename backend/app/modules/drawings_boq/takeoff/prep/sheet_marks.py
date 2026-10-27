from __future__ import annotations
from app.modules.drawings_boq.takeoff.prep import region_ocr as RO
from collections import Counter
import dataclasses
from app.modules.drawings_boq.takeoff.prep import title_strip as TS
from app.modules.drawings_boq.takeoff.extract import drawing_list as DL

STRIP_RIGHT_SHARE = 0.22
BLOCK_LEFT_SHARE = 0.40
BLOCK_TOP_SHARE = 0.28
OVERLAP_DUP = 0.5
LIST_DPIS = (450.0, 300.0)
STRIP_PASSES = ((300.0, "6"), (300.0, "11"), (200.0, "11"), (450.0, "6"))
COLUMN_PASSES = ((450.0, "6"), (450.0, "11"), (450.0, "4"), (600.0, "6"))
ROW_VOTE = 0.4
CELL_DPIS = (450.0, 560.0, 650.0)

def _overlap(a, b) -> float:
  ix = max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0))
  iy = max(0.0, min(a.y1, b.y1) - max(a.y0, b.y0))
  area = max(min((a.x1 - a.x0) * (a.y1 - a.y0), (b.x1 - b.x0) * (b.y1 - b.y0)), 1e-6)
  return ix * iy / area

def _merge(existing: list, added: list, region: tuple | None = None) -> list:
  if region is not None:
    x0, y0, x1, y1 = region
    kept = [o for o in existing if not (x0 <= o.cx <= x1 and y0 <= o.cy <= y1)]
    return kept + list(added)
  out = list(existing)
  for w in added:
    if not any(_overlap(w, o) > OVERLAP_DUP for o in existing):
      out.append(w)
  return out

def strip_regions(view_w: float, view_h: float) -> list:
  return [("BOTTOM", (view_w * BLOCK_LEFT_SHARE, view_h * (1.0 - BLOCK_TOP_SHARE), view_w, view_h)), ("RIGHT", (view_w * (1.0 - STRIP_RIGHT_SHARE), 0.0, view_w, view_h))]

def read_strip(page, rotation: int, cropbox: tuple, words: list) -> dict:
  got = TS.read(words, cropbox)
  basis = "TEXT"
  tried: list = []

  if not got["fields"].get("sheet_no") and page is not None:
    merged = list(words)
    Wv, Hv = page.get_size()
    done = False
    for name, box in strip_regions(Wv, Hv):
      for dpi, psm in STRIP_PASSES:
        extra, info = RO.read_region(page, rotation, cropbox, box, dpi=dpi, psm=psm)
        tried.append({"region": name, "dpi": dpi, "psm": psm, "words": len(extra)})
        if not extra:
          continue
        
        merged = _merge(merged, extra, RO.user_box(box, rotation, cropbox))
        again = TS.read(extra, cropbox)
        if not again["fields"].get("sheet_no"):
          again = TS.read(merged, cropbox)
        if again["fields"].get("sheet_no"):
          got, basis, done = again, "REGION_OCR", True
          break
        if len(again["fields"]) > len(got["fields"]):
          got, basis = again, "REGION_OCR"
      if done:
        break
  return {**got["fields"], "basis": basis if got["fields"] else "NONE", "evidence": got["evidence"], "tried": tried}

def _numbers(words: list) -> list:
  out = []
  for w in words:
    t = TS.clean_no(w.text)
    if DL._number_like(t):
      out.append(dataclasses.replace(w, text=t))
  return out

def _shape(text: str) -> str:
  return "".join("9" if c.isdigit() else "A" if c.isalpha() else c for c in text)

def _vote(passes: list) -> list:
  items = [(w, i) for i, ws in enumerate(passes) for w in ws]
  if not items:
    return []
  h = sorted(w.y1 - w.y0 for w, _i in items)[len(items) // 2] if all(abs(((float(w.angle or 0) + 45) % 90) - 45) < 8 for w, _ in items) else 5.0
  cells: list = []

  for w, i in sorted(items, key=lambda t: (-t[0].cy, t[0].cx)):
    for c in cells:
      if abs(c["cy"] - w.cy) <= ROW_VOTE * max(h, 1.0) and abs(c["cx0"] - w.x0) <= 6.0 * max(h, 1.0):
        c["words"].append(w)
        break
    else:
      cells.append({"cy": w.cy, "cx0": w.x0, "words": [w]})
  shapes = Counter(_shape(w.text) for w, _i in items)

  out = []
  for c in cells:
    votes = Counter(TS.clean_no(w.text) for w in c["words"])
    best = max(votes, key=lambda t: (votes[t], shapes[_shape(t)], len(t)))
    rep = next(w for w in c["words"] if TS.clean_no(w.text) == best)
    out.append(dataclasses.replace(rep, text=best))
  return out

def read_list(page, rotation: int, cropbox: tuple, words: list) -> dict | None:
  heading = DL.heading_of(words)
  if heading is None:
    return None

  own = DL.read(words, heading)
  best = {"entries": own["entries"], "basis": "TEXT"}
  if page is not None:
    Wv, Hv = page.get_size()
    vx0, vy0, vx1, vy1 = RO.view_box(heading["bbox"], rotation, cropbox)
    table = (0.0, max(0.0, vy1), Wv, Hv)
    pool: list = []

    for dpi in LIST_DPIS:
      extra, info = RO.read_region(page, rotation, cropbox, table, dpi=dpi)
      if not extra:
        continue
      got = DL.read(extra, None)
      if len(got["entries"]) >= len(best["entries"]) and len(got["entries"]) > 0:
        best = {"entries": got["entries"], "basis": "REGION_OCR", "dpi": info.get("dpi")}
        pool = extra
      if len(got["entries"]) >= 3:
        break

    column = DL.number_column(pool) if pool else None
    if column is not None:
      cx0, _cy0, cx1, _cy1 = RO.view_box(column, rotation, cropbox)
      strip = (max(0.0, cx0), table[1], min(Wv, cx1), Hv)
      loose = [_numbers(pool)]
      info = {}
      for dpi, psm in COLUMN_PASSES:
        extra, info = RO.read_region(page, rotation, cropbox, strip, dpi=dpi, psm=psm)
        loose.append(_numbers(extra))
      cellwise = []

      for dpi in CELL_DPIS:
        cells, _info = RO.read_cells(page, rotation, cropbox, strip, dpi=dpi)
        cellwise.append(_numbers(cells))
      primary = _vote(cellwise)
      voted = primary + [w for w in _vote(loose) if not any(abs(p.cy - w.cy) <= 0.8 * max(p.y1 - p.y0, 1.0) for p in primary)]
      merged = [w for w in pool if not DL._number_like(TS.clean_no(w.text))] + voted
      got = DL.read(merged, None)
      if len(got["entries"]) > len(best["entries"]):
        best = {"entries": got["entries"], "basis": "REGION_OCR", "dpi": info.get("dpi"), "column_reread": True}

  if len(best["entries"]) < DL.MIN_ENTRIES:
    return None
  return {"heading": heading["text"][:80], **best}

def read(page, rotation: int, cropbox: tuple, words: list) -> dict:
  out: dict = {}
  strip = read_strip(page, rotation, cropbox, words)
  if strip.get("basis") != "NONE":
    out["strip"] = strip
  listing = read_list(page, rotation, cropbox, words)
  if listing:
    out["list"] = listing
  return out
