from __future__ import annotations
import collections
import re
import time
from app.modules.drawings_boq.takeoff.prep.texts import build_lines, to_visual
from app.modules.drawings_boq.takeoff.prep.details import ocr_available
from app.modules.drawings_boq.takeoff.prep import picture_cache as PC
from app.modules.drawings_boq.takeoff.prep import picture_text as PT

CAPTION = re.compile(r"\b(?:SECTION|DETAIL|PLAN)\b.*\b(?:TANKS?|W\.?\s?T)\b", re.I)
BARE_CAPTION = re.compile(r"^(?:O\s*[/.]?\s*H|OVER\s*HEAD|U\s*[/.]?\s*G|UNDER\s*GROUND)\.?\s*WATER\s*TANK$", re.I) 
VIEW_SECTION = re.compile(r"\b(?:SECTION|DETAIL)\b", re.I)
KIND_OHWT = re.compile(r"\bO\s*[/.]?\s*H\b|OVER\s*HEAD|OHWT", re.I)
KIND_UGWT = re.compile(r"\bU\s*[/.]?\s*G\b|UNDER\s*GROUND|UGWT", re.I)
MAX_CAPTION_CHARS = 48
REGION_HALF_WIDTH_PT = 75.0
REGION_HEIGHT_PT = 170.0
NEIGHBOUR_REACH_PT = 90.0
SCALES = (6, 8, 11)
PSMS = ("11", "12")
WORKERS = 4
MIN_VOTES = 2
WHITELIST = "0123456789#@-\"'/Cc.”’"
FEET_INCH = re.compile(r"^(\d{1,2})[’'/]?-(\d{1,2})[\"”]?$")
INCH = re.compile(r"^(\d{1,2})[\"”]$")
BAR_NOTE = re.compile(r"#\s*\d+\s*@|\d+\s*/\s*\d+\s*[\"”]?\s*Ø", re.I)
OCR_BUDGET_S = 60.0

def kind_of(text: str) -> str:
  """OHWT, UGWT, SEPTIC or TANK, from the words of a tank label or caption."""
  t = text or ""
  if re.search(r"SEPTIC", t, re.I):
    return "SEPTIC"
  if KIND_OHWT.search(t):
    return "OHWT"
  if KIND_UGWT.search(t):
    return "UGWT"
  return "TANK"

def parse_length(text: str) -> dict | None:
  """A size as the reader returns it. 3'-6" is 42 inches; 6" is 6. The apostrophe is often read as a slash or lost ("3/-6"") and a bare quote is a
  clear inch value; anything else (a bare number, 14-3) is not taken."""
  t = (text or "").replace(" ", "")
  m = FEET_INCH.match(t)
  if m and ("'" in t or "’" in t or "/" in t):
    feet, inch = int(m.group(1)), int(m.group(2))
    if 1 <= feet <= 30 and inch <= 11:
      return {"inches": feet * 12 + inch, "text": f"{feet}'-{inch}\""}
  m = INCH.match(t)
  if m and 1 <= int(m.group(1)) <= 48:
    return {"inches": int(m.group(1)), "text": f"{int(m.group(1))}\""}
  return None

def captions(lines: list) -> list:
  """[{"text", "kind", "view", "x", "y"}]: the lines that name a tank drawing ("SECTION OF O/H WATER TANK", "Detail of U/G.W.Tank", "PLAN OF OVER HEAD WATER TANK")."""
  out = []
  for ln in lines:
    text = (ln.text or "").strip()
    if not text or len(text) > MAX_CAPTION_CHARS or not ln.spans or not (CAPTION.search(text) or BARE_CAPTION.match(text)):
      continue
    ws = [w for _, _, w in ln.spans]
    out.append({"text": text, "kind": kind_of(text), "view": "SECTION" if VIEW_SECTION.search(text) else "PLAN", "x": sum(w.cx for w in ws) / len(ws), "y": sum(w.cy for w in ws) / len(ws)})
  return out

def _region(cap_v: tuple, others_v: list, Wv: float, Hv: float) -> tuple:
  vx, vy = cap_v
  top = vy - REGION_HEIGHT_PT
  for ox, oy in others_v:
    if (ox, oy) != cap_v and abs(ox - vx) < NEIGHBOUR_REACH_PT and oy < vy - 12.0:
      top = max(top, oy + 4.0)
  return (max(0.0, vx - REGION_HALF_WIDTH_PT), max(0.0, top), min(Wv, vx + REGION_HALF_WIDTH_PT), max(0.0, vy - 3.0))

def read_lengths(page, region: tuple, Wv: float, Hv: float, deadline: float, status: dict | None = None) -> list:
  """[{"text", "inches", "votes", "source": "PICTURE"}]: the sizes written in the picture, most often read first. A reading is one size at one rendering size and
  one turn of the picture, so the same label found by both of the reading modes at one size counts once. The readings run side by side (the reader is a
  separate program). A picture read before (same pixels) comes from the cache. `status["complete"]` says whether every reading ran before the deadline; a cut-off
  reading is not cached."""
  from concurrent.futures import ThreadPoolExecutor
  from PIL import Image
  jobs = []
  imgs = []
  for sc in SCALES:
    try:
      img = page.render(scale=sc, crop=(region[0], Hv - region[3], Wv - region[2], region[1])).to_pil().convert("L")
    except Exception:
      continue
  
    imgs.append(img)
    for turn, label in ((None, 0), (Image.ROTATE_270, 270), (Image.ROTATE_90, 90)):
      im = img if turn is None else img.transpose(turn)
      for psm in PSMS:
        jobs.append((sc, label, im, psm))
  key = PC.key_of("tank", imgs[-1]) if imgs and len(imgs) == len(SCALES) else None
  
  if key:
    hit = PC.get(key)
    if isinstance(hit, list):
      if status is not None:
        status["complete"] = True
        status["cached"] = True
      return [{**r, "source": "PICTURE"} for r in hit]
  skipped = [False]
  
  def run(job):
    from app.modules.drawings_boq.takeoff.prep.beam_details import _tess_tokens
    sc, label, im, psm = job
    if time.monotonic() > deadline:
      skipped[0] = True
      return []
    return [(sc, label, got) for got in (parse_length(t["text"]) for t in _tess_tokens(im, psm, WHITELIST)) if got]
  seen: dict = collections.defaultdict(set)
  texts: dict = {}
  with ThreadPoolExecutor(max_workers=WORKERS) as pool:
    for found in pool.map(run, jobs):
      for sc, label, got in found:
        seen[got["inches"]].add((sc, label))
        texts[got["inches"]] = got["text"]
  out = [{"text": texts[v], "inches": v, "votes": len(s)} for v, s in seen.items() if len(s) >= MIN_VOTES]
  out.sort(key=lambda r: (-r["votes"], r["inches"]))
  complete = not skipped[0] and len(imgs) == len(SCALES)
  if status is not None:
    status["complete"] = complete
  if complete and key:
    PC.put(key, out)
  return [{**r, "source": "PICTURE"} for r in out]

def merge_lengths(text_lengths: list, picture_lengths: list) -> list:
  """The sizes from the PDF's own text and from the picture as one list. A size in the text keeps its text reading (and gains the votes of the picture when it
  read the same size); a size only the picture gave stays a picture reading."""
  by = {r["inches"]: dict(r) for r in picture_lengths}
  for r in text_lengths:
    got = by.get(r["inches"])
    by[r["inches"]] = {**r, "votes": r["votes"] + (got["votes"] if got else 0)}
  out = list(by.values())
  out.sort(key=lambda r: (-r["votes"], r["inches"]))
  return out

def bar_notes(lines: list, vis, region: tuple) -> list:
  """The reinforcement notes (real text, so read without the picture) that sit inside the region: ['#3@ 8"C/C HORIZANTAL', ...]."""
  out = []
  for ln in lines:
    text = (ln.text or "").strip()
    if not text or not BAR_NOTE.search(text):
      continue
    x, y = ln.locate(0, len(ln.text))
    vx, vy = vis(x, y)
    if region[0] <= vx <= region[2] and region[1] <= vy <= region[3] and text not in out:
      out.append(text)
  return out

def read_tank_details(words: list, page, page_wh: tuple, crop: tuple, rotation: int, use_ocr: bool = True, budget_s: float = OCR_BUDGET_S) -> dict:
  """Every tank drawing on the sheet: {"ocr", "details": [{"kind", "view", "caption", "x", "y", "region", "lengths", "bar_notes", "read"}]}."""
  lines = build_lines(words)
  caps = captions(lines)
  if not caps:
    return {"ocr": "NONE", "details": []}
  ocr = bool(use_ocr and ocr_available())
  Wv, Hv = page_wh
  def vis(px, py):
    u, v = to_visual(px, py, crop, rotation)
    return u * Wv, v * Hv

  each = budget_s / len(caps)
  cap_v = {id(c): vis(c["x"], c["y"]) for c in caps}
  others = list(cap_v.values())
  try:
    from app.modules.drawings_boq.takeoff.prep.beam_details import caption_marks
    others += [vis(c["x"], c["y"]) for c in caption_marks(lines)]
  except Exception:
    pass

  out = []
  for c in caps:
    region = _region(cap_v[id(c)], others, Wv, Hv)
    rec = {"kind": c["kind"], "view": c["view"], "caption": c["text"], "x": round(c["x"], 1), "y": round(c["y"], 1), "region": [round(v, 1) for v in region],
      "lengths": [], "bar_notes": bar_notes(lines, vis, region), "read": "NONE"}
    text_lengths = PT.tank_lengths(PT.region_words(words, region, crop, rotation, page_wh))
    rec["lengths"] = text_lengths
    rec["read"] = "TEXT" if text_lengths else "NONE"
    if ocr and region[2] - region[0] > 20 and region[3] - region[1] > 20:
      try:
        status: dict = {}
        
        picture = read_lengths(page, region, Wv, Hv, time.monotonic() + each, status)
        rec["lengths"] = merge_lengths(text_lengths, picture)
        if picture:
          rec["read"] = "TEXT+OCR" if text_lengths else "OCR"
        elif not status.get("complete") and not text_lengths:
          rec["read"] = "TIMEOUT"
      except Exception:
        rec["read"] = "FAILED"
    rec["from_text"] = bool(text_lengths or rec["bar_notes"])
    out.append(rec)
  return {"ocr": "OK" if ocr else "UNAVAILABLE", "details": out}

def gather(sheets: list) -> list:
  """The tank drawings of a whole drawing: [{"kind", "view", "caption", "pages", "lengths", "bar_notes"}]. sheets: [{"page_no", "details"}]. The same kind and view
  read on two sheets is kept once per sheet."""
  out = []
  for sh in sheets:
    for d in sh.get("details") or []:
      if d.get("lengths") or d.get("bar_notes"):
        out.append({"kind": d["kind"], "view": d["view"], "caption": d["caption"], "page_no": sh.get("page_no"), "lengths": list(d.get("lengths") or []),
          "bar_notes": list(d.get("bar_notes") or [])})
  return out
