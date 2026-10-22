from __future__ import annotations
import os
import io
import tempfile
import shutil
import csv
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from app.modules.drawings_boq.takeoff.prep import scan_lookalike as SL

SCAN_OCR_BUDGET_S = float(os.environ.get("TRACE_SCAN_OCR_BUDGET_S", "75"))
MIN_COVER = 0.5
MIN_DPI, MAX_DPI = 300.0, 350.0
MAX_SIDE_PX = 9000
MIN_CONF = 40.0
MIN_CONF_SHORT = 70.0
MAX_WORDS = 20000
PASSES = (0, 90)
TILE_PX = 1500
TILE_OVERLAP_PX = 200
UPSCALE = 2
BLANK_DARK_FRACTION = 0.002
MAX_WORKERS = 4
NATIVE_WORDS_OK = 25
RECHECK_ON = os.environ.get("TRACE_SCAN_RECHECK", "1") != "0"
RECHECK_BUDGET_S = float(os.environ.get("TRACE_SCAN_RECHECK_S", "20"))
REREAD_SCALES = (3, 4, 5)
REREAD_PAD_PX = 6

def available() -> bool:
  if shutil.which("tesseract") is None:
    return False
  try:
    import numpy
    import PIL
  except ImportError:
    return False
  return True

def needs_ocr(words: list, images: list, cropbox: tuple, stats: dict) -> bool:
  if len(words) >= NATIVE_WORDS_OK or stats.get("text_chars", 0) >= 4 * NATIVE_WORDS_OK:
    return False
  l, b, r, t = cropbox
  area = max((r - l) * (t - b), 1.0)
  cover = 0.0
  for im in images:
    x0, y0, x1, y1 = im["bbox"]
    cover += max(0.0, min(x1, r) - max(x0, l)) * max(0.0, min(y1, t) - max(y0, b))
  return cover / area >= MIN_COVER

def pick_dpi(images: list) -> float:
  best = max((im.get("dpi") or 0.0 for im in images), default=0.0)
  if best <= 0:
    return MIN_DPI
  return max(MIN_DPI, min(MAX_DPI, best))

def view_to_user(a: float, b: float, rotation: int, crop: tuple) -> tuple:
  cx0, cy0, cx1, cy1 = crop
  if rotation == 90:
    return cx0 + b, cy0 + a
  if rotation == 180:
    return cx1 - a, cy0 + b
  if rotation == 270:
    return cx1 - b, cy1 - a
  return cx0 + a, cy1 - b

def user_angle(view_angle: float, rotation: int) -> float:
  return (view_angle + rotation) % 360.0

def _tsv(img, timeout: float, psm: str = "11") -> list[dict]:
  from PIL import ImageOps
  img = ImageOps.expand(img, border=20, fill=255)
  fd, path = tempfile.mkstemp(suffix=".png")
  try:
    with os.fdopen(fd, "wb") as fh:
      img.save(fh, format="PNG")
    env = dict(os.environ)
    env["OMP_THREAD_LIMIT"] = "1"
    proc = subprocess.run(["tesseract", path, "-", "--psm", psm, "-l", "eng", "tsv"], capture_output=True, text=True,
      timeout=max(5.0, timeout), env=env)
    text = proc.stdout
  except Exception:
    return []

  finally:
    try:
      os.remove(path)
    except OSError:
      pass
  rows = []
  rd = csv.DictReader(io.StringIO(text), delimiter="\t", quoting=csv.QUOTE_NONE)
  for r in rd:
    try:
      if int(r["level"]) != 5:
        continue
      word = (r["text"] or "").strip()
      conf = float(r["conf"])
      if not word or conf < 0:
        continue
      rows.append({"text": word, "conf": conf, "l": int(r["left"]) - 20, "t": int(r["top"]) - 20, "w": int(r["width"]), "h": int(r["height"])})
    except (KeyError, ValueError, TypeError):
      continue
  return rows

def _keep(row: dict) -> bool:
  text = row["text"]
  if row["conf"] < MIN_CONF:
    return False
  if not any(ch.isalnum() for ch in text):
    return False
  if len(text) <= 2 and row["conf"] < MIN_CONF_SHORT:
    return False
  if row["h"] < 6 or row["w"] < 4:
    return False
  return True

def _reread(view, row: dict, k: int, deadline: float):
  """One more reading of a single word: its box cut out of the sheet, magnified k times, read as a line. None when it failed or gave more than one word."""
  from PIL import Image
  left = max(0, int(row["l"] - REREAD_PAD_PX))
  top = max(0, int(row["t"] - REREAD_PAD_PX))
  right = min(view.size[0], int(row["l"] + row["w"] + REREAD_PAD_PX + 1))
  bottom = min(view.size[1], int(row["t"] + row["h"] + REREAD_PAD_PX + 1))
  if right - left < 4 or bottom - top < 4:
    return None
  part = view.crop((left, top, right, bottom))
  big = part.resize((part.width * k, part.height * k), Image.LANCZOS)
  rows = _tsv(big, max(2.0, min(10.0, deadline - time.monotonic())), psm="7")
  rows = [r for r in rows if any(ch.isalnum() for ch in r["text"])]
  if len(rows) != 1:
    return None
  return rows[0]["text"]

def _room_names() -> set:
  try:
    from app.modules.drawings_boq.takeoff.extract import config as C
    return set(C.ROOM_NAMES)
  except Exception:
    return set()

def _settle(rows: list, views: dict, partial: bool) -> tuple[list, dict]:
  names = _room_names()
  todo = SL.plan(rows) if rows else []
  verdicts: dict = {}
  if todo and RECHECK_ON and not partial:
    deadline = time.monotonic() + RECHECK_BUDGET_S

    def work(i: int):
      reads = []
      for k in REREAD_SCALES[:SL.REREADS]:
        reads.append(_reread(views[rows[i]["angle"]], rows[i], k, deadline) if time.monotonic() < deadline else None)
      return i, reads
    workers = max(1, min(MAX_WORKERS, os.cpu_count() or 1))
    try:
      with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, reads in pool.map(work, todo):
          verdicts[i] = SL.decide(rows[i]["text"], reads)
    except Exception:
      verdicts = {}
  kept, report = SL.apply(rows, verdicts, names)
  if todo and not verdicts:
    report["unchecked"] = len(todo)
  return kept, report

def _reread(view, row: dict, k: int, deadline: float):
  """One more reading of a single word: its box cut out of the sheet, magnified k times, read as a line. None when it failed or gave more than one word."""
  from PIL import Image
  left = max(0, int(row["l"] - REREAD_PAD_PX))
  top = max(0, int(row["t"] - REREAD_PAD_PX))
  right = min(view.size[0], int(row["l"] + row["w"] + REREAD_PAD_PX + 1))
  bottom = min(view.size[1], int(row["t"] + row["h"] + REREAD_PAD_PX + 1))
  if right - left < 4 or bottom - top < 4:
    return None
  part = view.crop((left, top, right, bottom))
  big = part.resize((part.width * k, part.height * k), Image.LANCZOS)
  rows = _tsv(big, max(2.0, min(10.0, deadline - time.monotonic())), psm="7")
  rows = [r for r in rows if any(ch.isalnum() for ch in r["text"])]
  if len(rows) != 1:
    return None
  return rows[0]["text"]

def _room_names() -> set:
  try:
    from app.modules.drawings_boq.takeoff.extract import config as C
    return set(C.ROOM_NAMES)
  except Exception:
    return set()

def _settle(rows: list, views: dict, partial: bool) -> tuple[list, dict]:
  names = _room_names()
  todo = SL.plan(rows) if rows else []
  verdicts: dict = {}
  if todo and RECHECK_ON and not partial:
    deadline = time.monotonic() + RECHECK_BUDGET_S

    def work(i: int):
      reads = []
      for k in REREAD_SCALES[:SL.REREADS]:
        reads.append(_reread(views[rows[i]["angle"]], rows[i], k, deadline) if time.monotonic() < deadline else None)
      return i, reads
    workers = max(1, min(MAX_WORKERS, os.cpu_count() or 1))
    try:
      with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, reads in pool.map(work, todo):
          verdicts[i] = SL.decide(rows[i]["text"], reads)
    except Exception:
      verdicts = {}
  kept, report = SL.apply(rows, verdicts, names)
  if todo and not verdicts:
    report["unchecked"] = len(todo)
  return kept, report

def _build_word(text: str, a0: float, b0: float, a1: float, b1: float, view_angle: float, rotation: int, crop: tuple):
  from app.modules.drawings_boq.takeoff.prep.extract import Word
  corners = [view_to_user(a, b, rotation, crop) for a, b in ((a0, b0), (a1, b0), (a1, b1), (a0, b1))]
  xs = [c[0] for c in corners]
  ys = [c[1] for c in corners]
  x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
  vertical = view_angle % 180 == 90
  length = (b1 - b0) if vertical else (a1 - a0)
  height = (a1 - a0) if vertical else (b1 - b0)
  return Word(text=text, x0=x0, y0=y0, x1=x1, y1=y1, angle=user_angle(view_angle, rotation), size=height / 0.75,
    cx=(x0 + x1) / 2, cy=(y0 + y1) / 2, length=length, height=height)

def _overlap(a: tuple, b: tuple) -> float:
  ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
  iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
  inter = ix * iy
  if inter <= 0:
    return 0.0
  small = max(min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])), 1e-9)
  return inter / small

def _starts(total: int) -> list[int]:
  if total <= TILE_PX:
    return [0]
  step = TILE_PX - TILE_OVERLAP_PX
  out = list(range(0, total - TILE_PX, step))
  out.append(total - TILE_PX)
  return out

def _tiles(width: int, height: int) -> list[tuple]:
  """(crop box, core box) pairs: a word belongs to the tile whose core holds its centre, so overlapping tiles never read a word twice."""
  xs, ys = _starts(width), _starts(height)
  half = TILE_OVERLAP_PX // 2
  out = []
  for yi, y in enumerate(ys):
    for xi, x in enumerate(xs):
      crop = (x, y, min(x + TILE_PX, width), min(y + TILE_PX, height))
      core = (0 if xi == 0 else x + half, 0 if yi == 0 else y + half,
        width if xi == len(xs) - 1 else crop[2] - half, height if yi == len(ys) - 1 else crop[3] - half)
      out.append((crop, core))
  return out

def _blank(img) -> bool:
  import numpy as np
  arr = np.asarray(img)
  return float((arr < 160).mean()) < BLANK_DARK_FRACTION

def _read_tile(img, crop: tuple, core: tuple, deadline: float) -> list[dict]:
  from PIL import Image
  if time.monotonic() > deadline:
    return [{"skipped": True}]
  part = img.crop(crop)
  if _blank(part):
    return []
  big = part.resize((part.width * UPSCALE, part.height * UPSCALE), Image.LANCZOS)
  rows = _tsv(big, max(5.0, deadline - time.monotonic()))
  out = []
  for r in rows:
    l, t = crop[0] + r["l"] / UPSCALE, crop[1] + r["t"] / UPSCALE
    w, h = r["w"] / UPSCALE, r["h"] / UPSCALE
    cx, cy = l + w / 2, t + h / 2
    if not (core[0] <= cx < core[2] and core[1] <= cy < core[3]):
      continue
    out.append({"text": r["text"], "conf": r["conf"], "l": l, "t": t, "w": w, "h": h})
  return out

def _record(info: dict, report: dict, rows: list, rotation: int, cropbox: tuple) -> None:
  repaired = report["repaired"]
  split = report["split"]
  info["ocr_checked"] = report["checked"]
  info["ocr_repaired"] = len(repaired) + report["figure_repaired"] + report["label_repaired"]
  info["ocr_split"] = len(split)
  info["ocr_unchecked"] = report["unchecked"]
  if repaired:
    info["ocr_repairs"] = [{"from": r["from"], "to": r["to"]} for r in repaired[:SL.MAX_LISTED]]
  if split:
    at = []
    for sp in split[:SL.MAX_LISTED]:
      row = rows[sp["row"]]
      a0, b0, a1, b1 = row["box"]
      w = _build_word(row["text"], a0, b0, a1, b1, row["va"], rotation, cropbox)
      at.append({"x": round(w.cx, 1), "y": round(w.cy, 1), "reads": sp["reads"]})
    info["ocr_split_at"] = at

def _record(info: dict, report: dict, rows: list, rotation: int, cropbox: tuple) -> None:
  repaired = report["repaired"]
  split = report["split"]
  info["ocr_checked"] = report["checked"]
  info["ocr_repaired"] = len(repaired) + report["figure_repaired"] + report["label_repaired"]
  info["ocr_split"] = len(split)
  info["ocr_unchecked"] = report["unchecked"]
  
  if repaired:
    info["ocr_repairs"] = [{"from": r["from"], "to": r["to"]} for r in repaired[:SL.MAX_LISTED]]
  if split:
    at = []
    for sp in split[:SL.MAX_LISTED]:
      row = rows[sp["row"]]
      a0, b0, a1, b1 = row["box"]
      w = _build_word(row["text"], a0, b0, a1, b1, row["va"], rotation, cropbox)
      at.append({"x": round(w.cx, 1), "y": round(w.cy, 1), "reads": sp["reads"]})
    info["ocr_split_at"] = at

def read_page(page, rotation: int, cropbox: tuple, images: list, budget_s: float = SCAN_OCR_BUDGET_S) -> tuple[list, dict]:
  """Words recovered from a scanned sheet, placed in the same unrotated page space as the words of a text layer."""
  info: dict = {"text_source": "OCR"}
  if not available():
    info["ocr_error"] = "UNAVAILABLE"
    return [], info
  started = time.monotonic()
  deadline = started + budget_s
  dpi = pick_dpi(images)
  scale = dpi / 72.0
  try:
    w_pt, h_pt = page.get_size()
    longest = max(w_pt, h_pt) * scale
    if longest > MAX_SIDE_PX:
      scale *= MAX_SIDE_PX / longest
    img = page.render(scale=scale).to_pil().convert("L")
  except Exception:
    info["ocr_error"] = "RENDER"
    return [], info
  info["ocr_dpi"] = round(scale * 72.0, 1)
  H = img.size[1]
  views = {0: img}
  
  if 90 in PASSES:
    views[90] = img.rotate(-90, expand=True)
  jobs = []
  for angle, view in views.items():
    for crop, core in _tiles(view.size[0], view.size[1]):
      jobs.append((angle, view, crop, core))
  workers = max(1, min(MAX_WORKERS, os.cpu_count() or 1))
  try:
    with ThreadPoolExecutor(max_workers=workers) as pool:
      futures = [(angle, pool.submit(_read_tile, view, crop, core, deadline)) for angle, view, crop, core in jobs]
      results = [(angle, fut.result()) for angle, fut in futures]
      
  except Exception:
    info["ocr_error"] = "ENGINE"
    return [], info
  rows_kept: list = []
  boxes: list = []
  partial = False
  for angle in PASSES:
    for a_, rows in results:
      if a_ != angle:
        continue
      for row in rows:
        if row.get("skipped"):
          partial = True
          continue
        if not _keep(row):
          continue
      
        if angle == 0:
          a0, b0 = row["l"] / scale, row["t"] / scale
          a1, b1 = (row["l"] + row["w"]) / scale, (row["t"] + row["h"]) / scale
          va = 0.0
        else:
          u0, v0, u1, v1 = row["l"], row["t"], row["l"] + row["w"], row["t"] + row["h"]
          a0, a1 = v0 / scale, v1 / scale
          b0, b1 = (H - u1) / scale, (H - u0) / scale
          va = 90.0
        box = (a0, b0, a1, b1)
        if any(_overlap(box, other) > 0.5 for other in boxes):
          continue
        boxes.append(box)
        rows_kept.append({**row, "angle": angle, "box": box, "va": va})
        if len(rows_kept) >= MAX_WORDS:
          break
      
  settled, report = _settle(rows_kept, views, partial)
  words: list = []
  confs: list = []
  for row in settled:
    a0, b0, a1, b1 = row["box"]
    words.append(_build_word(row["text"], a0, b0, a1, b1, row["va"], rotation, cropbox))
    confs.append(row["conf"])
  _record(info, report, rows_kept, rotation, cropbox)
  info["ocr_words"] = len(words)
  info["ocr_mean_conf"] = round(sum(confs) / len(confs), 1) if confs else 0.0
  info["ocr_elapsed_s"] = round(time.monotonic() - started, 2)
  if partial:
    info["ocr_partial"] = True
  return words, info
