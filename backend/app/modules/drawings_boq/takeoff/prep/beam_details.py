from __future__ import annotations
import csv
import io
import os
import re
from app.modules.drawings_boq.takeoff.prep.details import norm_mark, ocr_available
import math
import tempfile
from concurrent.futures import ThreadPoolExecutor
from app.modules.drawings_boq.takeoff.prep import picture_cache as PC
from app.modules.drawings_boq.takeoff.prep import picture_text as PT
from app.modules.drawings_boq.takeoff.prep import schedules as S
import subprocess
import time
from app.modules.drawings_boq.takeoff.prep.texts import build_lines, to_visual
from app.engine.measure.steel_grammar import steel_text

BEAM_CAPTION = re.compile(r"\b(?P<mark>(?:PB|RB|GB|LB|TB|CB|B)\s*-?\s*\d{1,2})\b", re.I)
CAPTION_WORD = re.compile(r"\b(?:BEAM|SECTION|DETAIL)\b", re.I)
TIE_CAPTION = re.compile(r"\bTIE\s+BEAM\b|\bLEVEL\s+TIE\s+BAND\b|\bTIE\s+BAND\b", re.I)
MAX_CAPTION_CHARS = 40
UPSTAND_WORD = re.compile(r"\b(?:UP[\s-]?STAND(?:ING)?|INVERTED|UP[\s-]?TURNED?)\b", re.I)
UPSTAND_REACH_PT = 45.0
REGION_HALF_WIDTH_PT = 55.0
REGION_HEIGHT_PT = 100.0
REGION_BELOW_PT = 3.0
NEIGHBOUR_REACH_PT = 60.0
RENDER_SCALE = 8
WHITELIST = "0123456789#@-\"'/Cc.”"
INCH_MIN, INCH_MAX = 3.0, 48.0
BAR_MIN, BAR_MAX = 2, 12
COUNT_MIN, COUNT_MAX = 1, 12
STIRRUP_SPACING_IN = (2.0, 12.0)
OCR_BUDGET_S = float(os.environ.get("TRACE_BEAM_OCR_BUDGET_S", "75"))
MM_INCH = 25.4

KIND_OF = {"PB": "PLINTH", "RB": "ROOF", "GB": "GRADE", "LB": "LINTEL", "TB": "TIE", "CB": "TIE"}

def caption_marks(lines: list) -> list:
  """[{"mark", "text", "kind", "x", "y"}]: the lines that name a beam section ("Plinth Beam PB-1", "BEAM RB-2 SECTION", "B-2 SECTION", "TIE BEAM / LINTEL"), with
  where each one is (page units, as the words are placed)."""
  out = []
  for ln in lines:
    text = (ln.text or "").strip()
    if not text or len(text) > MAX_CAPTION_CHARS or not ln.spans:
      continue
    mark = None
    
    m = BEAM_CAPTION.search(text)
    if m and CAPTION_WORD.search(text):
      mark = norm_mark(m.group("mark"))
    elif TIE_CAPTION.search(text):
      mark = "TIE"
    if mark is None:
      continue
    ws = [w for _, _, w in ln.spans]
    prefix = re.match(r"[A-Z]+", mark).group(0) if mark != "TIE" else "TB"
    out.append({"mark": mark, "text": text, "kind": KIND_OF.get(prefix, "BEAM"), "x": sum(w.cx for w in ws) / len(ws), "y": sum(w.cy for w in ws) / len(ws)})
  merged: list = []
  for c in out:
    twin = next((m for m in merged if m["mark"] == c["mark"] and math.hypot(m["x"] - c["x"], m["y"] - c["y"]) < 30.0), None)
    if twin is None:
      merged.append(c)
  return merged

def _tess_tokens(img, psm: str, whitelist: str | None = None) -> list:
  """[{"text", "x", "y", "w", "h", "conf"}] for the words tesseract finds in a picture, in picture pixels."""
  fd, path = tempfile.mkstemp(suffix=".png")
  try:
    with os.fdopen(fd, "wb") as fh:
      img.save(fh, format="PNG")
    env = dict(os.environ)
    env["OMP_THREAD_LIMIT"] = "1"      
    out = subprocess.run(["tesseract", path, "-", "--psm", psm, "-c", f"tessedit_char_whitelist={whitelist or WHITELIST}", "tsv"], capture_output=True, text=True,
      timeout=25, env=env).stdout
  except Exception:
    return []
  finally:
    try:
      os.remove(path)
    except OSError:
      pass
  
  rows = []
  for r in csv.DictReader(io.StringIO(out), delimiter="\t"):
    t = (r.get("text") or "").strip()
    try:
      conf = float(r.get("conf") or -1)
    except ValueError:
      conf = -1.0
    if t and conf > 0:
      rows.append({"text": t, "x": int(r["left"]) + int(r["width"]) / 2.0, "y": int(r["top"]) + int(r["height"]) / 2.0, "w": int(r["width"]), "h": int(r["height"]), "conf": conf})
  return rows

_BARS = re.compile(r"^(?P<n>\d{1,2})[-–](?P<bar>\d)$")
_BARS_HASH = re.compile(r"^(?P<n>\d{1,2})[-–]#(?P<bar>\d{1,2})$")
_BARS_LOST_HASH = re.compile(r"^(?P<n>\d{1,2})[-–][#4](?P<bar>\d)$")
_STIRRUP = re.compile(r"^#?(?P<bar>\d)[@0](?P<s>[1-9]\d?)[\"”']?(?:C/?C)?$", re.I)
_DIM = re.compile(r"^(?P<v>\d{1,2})[\"”]$")

def parse_bars(text: str) -> dict | None:
  """"3-#4" is three bars of #4. The character reader often drops the # and writes it as a 4 ("3-44", "2-45"), so a note with two digits after the dash is read
  as the # and the bar number; a single digit after the dash is not accepted."""
  t = (text or "").replace(" ", "").replace("—", "-").replace("–", "-")
  for pat in (_BARS_HASH, _BARS_LOST_HASH):
    m = pat.match(t)
    if m:
      n, bar = int(m.group("n")), int(m.group("bar"))
      if COUNT_MIN <= n <= COUNT_MAX and BAR_MIN <= bar <= BAR_MAX:
        return {"n": n, "bar": bar}
  return None

def parse_stirrup(text: str) -> dict | None:
  """"#3@6"C/C" is #3 rings at 6 inch centres. The @ is often read as a 0 ("#306"")."""
  t = (text or "").replace(" ", "").replace("”", '"')
  m = _STIRRUP.match(t)
  if not m:
    return None
  bar, spacing = int(m.group("bar")), float(m.group("s"))
  if BAR_MIN <= bar <= BAR_MAX and STIRRUP_SPACING_IN[0] <= spacing <= STIRRUP_SPACING_IN[1]:
    return {"bar": bar, "spacing_mm": round(spacing * MM_INCH, 1)}
  return None

def parse_dim(text: str, bare_ok: bool = False) -> float | None:
  """"18"" is eighteen inches. The reader writes the inch mark as a quote and sometimes loses it; a bare number is taken only when the caller says the reading
  was a clear one (bare_ok) and the number has two digits, since a bare 8 is too often a 9."""
  t = (text or "").replace(" ", "").replace("'", '"')
  m = _DIM.match(t)
  if m:
    v = float(m.group("v"))
  elif bare_ok and re.fullmatch(r"\d{2}", t):
    v = float(t)
  else:
    return None
  return v if INCH_MIN <= v <= INCH_MAX else None

def _region(cap_v: tuple, others_v: list, Wv: float, Hv: float) -> tuple:
  """The rectangle (visual page units) of the detail drawn above a caption: as wide as a detail, as tall as one, and no taller than the next caption above."""
  vx, vy = cap_v
  top = vy - REGION_HEIGHT_PT
  for ox, oy in others_v:
    if (ox, oy) != cap_v and abs(ox - vx) < NEIGHBOUR_REACH_PT and oy < vy - 12.0:
      top = max(top, oy + 4.0)
  return (max(0.0, vx - REGION_HALF_WIDTH_PT), max(0.0, top), min(Wv, vx + REGION_HALF_WIDTH_PT), max(0.0, vy - REGION_BELOW_PT))

SCALES = (6, 8, 11)
MIN_VOTES_BARS = 2
MIN_VOTES_DIM = 2
CLUSTER_PT = 5.0

WORKERS = max(1, min(4, os.cpu_count() or 1))

def _read_picture(page, region: tuple, Hv: float, Wv: float, deadline: float) -> dict:
  
  from PIL import Image
  renders = []
  for sc in SCALES:
    if time.monotonic() > deadline:
      break
    try:
      renders.append((sc, page.render(scale=sc, crop=(region[0], Hv - region[3], Wv - region[2], region[1])).to_pil().convert("L")))
    except Exception:
      continue
  
  empty = {"bars": [], "stirrups": [], "dims": [], "reads": 0, "complete": False}
  if not renders:
    return empty
  key = PC.key_of("beam", renders[-1][1]) if len(renders) == len(SCALES) else None
  if key:
    hit = PC.get(key)
    if hit and all(k in hit for k in ("bars", "stirrups", "dims")):
      return {**hit, "complete": True, "cached": True}
  jobs = []
  for sc, img in renders:
    wi, hi = img.size
    turned = img.transpose(Image.ROTATE_270)      
    for psm in ("11", "12"):
      jobs.append(("flat", sc, img, psm, hi))
    for psm in ("11", "12"):
      jobs.append(("turned", sc, turned, psm, hi))
  def run(job):
    kind, sc, im, psm, hi = job
    if time.monotonic() > deadline:
      return None
    got = []
    
    for t in _tess_tokens(im, psm):
      if kind == "flat":
        pos = (region[0] + t["x"] / sc, region[1] + t["y"] / sc)
        b = parse_bars(t["text"])
        if b:
          got.append(("bars", {**b, "x": pos[0], "y": pos[1]}))
        s = parse_stirrup(t["text"])
        if s:
          got.append(("stirrups", {**s, "x": pos[0], "y": pos[1]}))
        d = parse_dim(t["text"], bare_ok=t["conf"] >= 85.0)
        if d:
          got.append(("dims", {"v": d, "orient": "H" if t["w"] >= 1.1 * t["h"] else "V", "x": pos[0], "y": pos[1]}))
      else:
        d = parse_dim(t["text"], bare_ok=t["conf"] >= 85.0)
        if d:
          ox, oy = t["y"], hi - t["x"]           
          got.append(("dims", {"v": d, "orient": "V" if t["w"] >= 1.1 * t["h"] else "H", "x": region[0] + ox / sc, "y": region[1] + oy / sc}))
    return got

  out = {"bars": [], "stirrups": [], "dims": []}
  done, complete = 0, len(renders) == len(SCALES)
  with ThreadPoolExecutor(max_workers=WORKERS) as pool:
    for got in pool.map(run, jobs):
      if got is None:
        complete = False
        continue
      done += 1
      for k, item in got:
        out[k].append(item)
  reads = len(renders)
  result = {**out, "reads": reads, "complete": complete}
  if complete and key:
    PC.put(key, out)
  return result

def _cluster(items: list) -> list:
  """Group readings that sit in the same place: [[reading, ...]]."""
  groups: list = []
  for it in items:
    for g in groups:
      if math.hypot(g[0]["x"] - it["x"], g[0]["y"] - it["y"]) <= CLUSTER_PT:
        g.append(it)
        break
    else:
      groups.append([it])
  return groups

def _winner(group: list, keys: tuple, min_votes: int):
  """The value of `keys` most of the readings in a place agree on, with at least `min_votes` and a lead of one over the next value."""
  tally: dict = {}
  for it in group:
    k = tuple(it[x] for x in keys)
    tally[k] = tally.get(k, 0) + 1
  ranked = sorted(tally.items(), key=lambda kv: -kv[1])
  if not ranked or ranked[0][1] < min_votes or (len(ranked) > 1 and ranked[1][1] >= ranked[0][1]):
    return None
  return ranked[0]

def _depth(votes: dict) -> float | None:
  """The depth from the vertical labels of a section (value -> readings): the only label, or the biggest when some of the others add up to it (a depth written
  in parts, as slab thickness and web below it). When the labels fit neither way the one read clearly more often than any other is taken; otherwise nothing."""
  vals = sorted(v for v, n in votes.items() if n >= MIN_VOTES_DIM)
  if not vals:
    return None
  biggest, others = vals[-1], vals[:-1]
  if not others:
    return biggest
  for mask in range(1, 1 << len(others)):
    if abs(sum(v for i, v in enumerate(others) if mask >> i & 1) - biggest) < 0.6:
      return biggest
  ranked = sorted(votes.items(), key=lambda kv: -kv[1])
  if ranked[0][1] >= ranked[1][1] + 2:
    return ranked[0][0]
  return None

def interpret(picture: dict, box_ratio: float | None = None) -> dict:
  """Turn the readings of one detail into {"width_in", "depth_in", "steel", "checks"}. Bars are tied to the top or the bottom of the section only when
  two bar notes are agreed on; one alone could be either, so it is reported and not used."""
  out: dict = {"width_in": None, "depth_in": None, "steel": None, "checks": {}}
  notes = []
  for g in _cluster(sorted(picture["bars"], key=lambda b: b["y"])):
    w = _winner(g, ("n", "bar"), MIN_VOTES_BARS)
    
    if w:
      notes.append({"n": w[0][0], "bar": w[0][1], "votes": w[1], "y": sum(i["y"] for i in g) / len(g)})
  notes.sort(key=lambda n: n["y"])
  steel: dict = {}
  if len(notes) >= 2:
    steel["top"] = {"n": notes[0]["n"], "bar": notes[0]["bar"]}
    steel["bottom"] = {"n": notes[-1]["n"], "bar": notes[-1]["bar"]}
  elif len(notes) == 1:
    out["checks"]["single_bar_note"] = {"n": notes[0]["n"], "bar": notes[0]["bar"]}
  rings = _cluster(sorted(picture["stirrups"], key=lambda s: s["y"]))
  best = None
  
  for g in rings:
    w = _winner(g, ("bar", "spacing_mm"), MIN_VOTES_BARS)
    if w and (best is None or w[1] > best[1]):
      best = w
  if best:
    steel["ring"] = {"bar": best[0][0], "spacing_mm": best[0][1]}
  out["steel"] = steel or None
  out["checks"]["dimension_labels_in"] = {}
  tallies: dict = {}
  for orient in ("V", "H"):
    tally: dict = {}
    for d in picture["dims"]:
      if d["orient"] == orient:
        tally[d["v"]] = tally.get(d["v"], 0) + 1
    tallies[orient] = tally
    out["checks"]["dimension_labels_in"][orient] = {str(v): n for v, n in sorted(tally.items())}
  out["depth_in"] = _depth(tallies["V"])
  return out

COLUMN_PAD_PT = (25.0, 28.0, 50.0, 8.0)
COLUMN_MIN_BARS = 4

def column_region(box_v: tuple, Wv: float, Hv: float) -> tuple:
  """The rectangle (visual page units) round the drawn outline of a column detail where its bar notes are written: a little to the left and above, more to the right
  where the arrows end, and just below."""
  left, above, right, below = COLUMN_PAD_PT
  return (max(0.0, box_v[0] - left), max(0.0, box_v[1] - above), min(Wv, box_v[2] + right), min(Hv, box_v[3] + below))

def interpret_column(picture: dict) -> dict:
  """The bars and rings read round one column detail: {"steel", "bar_notes", "conflict"}. A bar note counts when it is read twice in the same place (as for beams)
  and is four bars or more. Two bar notes in different places that name different bars, one of them read only once, are a conflict: the detail then prints
  two bar counts (the 18x9 detail of Islamabad prints 8-#6 and 6-#6), and no bars are taken from it. The ring is the ring note read most often."""
  confirmed: list = []
  weak: list = []
  for g in _cluster(sorted(picture["bars"], key=lambda b: (b["y"], b["x"]))):
    tally: dict = {}
    for it in g:
      tally[(it["n"], it["bar"])] = tally.get((it["n"], it["bar"]), 0) + 1
    w = _winner(g, ("n", "bar"), MIN_VOTES_BARS)
    if w:
      if w[0][0] >= COLUMN_MIN_BARS and {"n": w[0][0], "bar": w[0][1]} not in confirmed:
        confirmed.append({"n": w[0][0], "bar": w[0][1]})
    else:
      top = max(tally.items(), key=lambda kv: kv[1])
      if top[0][0] >= COLUMN_MIN_BARS and len([v for v in tally.values() if v == top[1]]) == 1:
        weak.append({"n": top[0][0], "bar": top[0][1]})
  others = [w for w in weak if w not in confirmed]
  notes = confirmed + [w for w in others if w not in confirmed]
  conflict = len(confirmed) > 1 or (bool(confirmed) and bool(others)) or len(others) > 1
  ring = None
  best = None
  for g in _cluster(sorted(picture["stirrups"], key=lambda s: (s["y"], s["x"]))):
    w = _winner(g, ("bar", "spacing_mm"), MIN_VOTES_BARS)
    if w and (best is None or w[1] > best[1]):
      best = w
  if best:
    ring = {"bar": best[0][0], "spacing_mm": best[0][1]}
  steel: dict = {}
  if len(confirmed) == 1 and not conflict:
    steel["vertical"] = dict(confirmed[0])
  if ring:
    steel["ring"] = ring
  return {"steel": steel or None, "bar_notes": notes, "conflict": conflict}

def column_bars(words: list, page, box_v: tuple, page_wh: tuple, crop: tuple, rotation: int, use_ocr: bool, deadline: float) -> dict:
  Wv, Hv = page_wh
  region = column_region(box_v, Wv, Hv)
  text_pic = PT.beam_picture(PT.region_words(words, region, crop, rotation, page_wh))
  got = interpret_column(text_pic)
  steel = got["steel"] or {}
  out = {**got, "read": "TEXT" if (steel.get("vertical") and steel.get("ring")) else "NONE", "region": [round(v, 1) for v in region]}
  if out["read"] == "TEXT" or got["conflict"] or not use_ocr:
    return out

  if time.monotonic() >= deadline:
    out["read"] = "TIMEOUT"
    return out
  try:
    picture = _read_picture(page, region, Hv, Wv, deadline)
  except Exception:
    out["read"] = "FAILED"
    return out
  merged = {k: text_pic[k] + picture[k] for k in ("bars", "stirrups", "dims")}
  got = interpret_column(merged)
  steel = got["steel"] or {}
  out.update(got)
  out["read"] = ("TEXT+OCR" if text_pic["from_text"] else "OCR") if (steel or got["bar_notes"]) else "NONE"
  if not picture.get("complete") and not steel.get("vertical"):
    out["read"] = "TIMEOUT"
  return out

def _whole(got: dict) -> bool:
  """A reading that needs nothing more: the depth and the bars at the top and the bottom."""
  steel = got.get("steel") or {}
  return bool(got.get("depth_in") and steel.get("top") and steel.get("bottom"))

def read_beam_details(words: list, index, page, page_wh: tuple, crop: tuple, rotation: int, use_ocr: bool = True, budget_s: float = OCR_BUDGET_S) -> dict:
  """Every beam section on the sheet: its mark, kind and, when the character reader is available, the size and bars written on it."""

def read_beam_details(words: list, index, page, page_wh: tuple, crop: tuple, rotation: int, use_ocr: bool = True, budget_s: float = OCR_BUDGET_S) -> dict:
  """Every beam section on the sheet: its mark, kind and, when the character reader is available, the size and bars written on it."""
  lines = build_lines(words)
  caps = caption_marks(lines)
  for ln in lines:
    t = (ln.text or "").strip()
    if not t or len(t) > MAX_CAPTION_CHARS or not ln.spans or not UPSTAND_WORD.search(t):
      continue
    ws = [w for _, _, w in ln.spans]
    lx, ly = sum(w.cx for w in ws) / len(ws), sum(w.cy for w in ws) / len(ws)
    near = sorted((math.hypot(c["x"] - lx, c["y"] - ly), i) for i, c in enumerate(caps))
    if near and near[0][0] <= UPSTAND_REACH_PT:
      caps[near[0][1]]["upstand"] = True
  for c in caps:
    if UPSTAND_WORD.search(c["text"]):
      c["upstand"] = True
  ocr = bool(use_ocr and ocr_available())
  Wv, Hv = page_wh
  def vis(px, py):
    u, v = to_visual(px, py, crop, rotation)
    return u * Wv, v * Hv
  deadline = time.monotonic() + budget_s
  cap_v = {id(c): vis(c["x"], c["y"]) for c in caps}
  others = [vis(c["x"], c["y"]) for c in caps]
  try:
    from app.modules.drawings_boq.takeoff.prep.details import find_captions
    others += [vis(c["x"], c["y"]) for c in find_captions(words)]
  except Exception:
    pass

  out = []
  for c in caps:
    region = _region(cap_v[id(c)], others, Wv, Hv)
    rec = {"mark": c["mark"], "caption": c["text"], "kind": c["kind"], "upstand": bool(c.get("upstand")), "x": round(c["x"], 1), "y": round(c["y"], 1), "region": [round(v, 1) for v in region],
      "width_in": None, "depth_in": None, "steel": None, "read": "NONE", "checks": {}}
    inside = PT.region_words(words, region, crop, rotation, page_wh)
    text_pic = PT.beam_picture(inside)
    got = interpret(text_pic)
    rec.update(width_in=got["width_in"], depth_in=got["depth_in"], steel=got["steel"], checks=got["checks"])
    sized = region[2] - region[0] > 20 and region[3] - region[1] > 20
    
    if _whole(got):
      rec["read"] = "TEXT"            
    elif ocr and sized and time.monotonic() < deadline:
      try:
        picture = _read_picture(page, region, Hv, Wv, deadline)
        merged = {k: text_pic[k] + picture[k] for k in ("bars", "stirrups", "dims")}
        got = interpret(merged)
        rec.update(width_in=got["width_in"], depth_in=got["depth_in"], steel=got["steel"], checks=got["checks"])
        rec["read"] = ("TEXT+OCR" if text_pic["from_text"] else "OCR") if rec["depth_in"] else "PARTIAL" if (rec["width_in"] or rec["steel"]) else "NONE"
        
        if not picture.get("complete") and not rec["depth_in"]:
          rec["read"] = "TIMEOUT"
      except Exception:
        rec["read"] = "FAILED"
    elif ocr and sized:
      rec["read"] = "TIMEOUT"
    else:
      rec["read"] = "TEXT" if rec["depth_in"] else "PARTIAL" if (rec["width_in"] or rec["steel"]) else "NONE"
    rec["from_text"] = bool(text_pic["from_text"])
    out.append(rec)
  return {"ocr": "OK" if ocr else "UNAVAILABLE", "details": out}

def gather(sheets: list) -> list:
  """The beam sections of a whole drawing, from the details read on each sheet (prep meta "beam_details"): [{"mark", "kind", "depth_mm", "steel", "pages", "disagree"}].
  sheets: [{"page_no", "details": [...]}]. The same mark read twice with different depths is reported as disagreeing and carries no depth."""
  by: dict = {}
  
  for sh in sheets:
    for d in sh.get("details") or []:
      if not (d.get("depth_in") or d.get("steel")):
        continue
      by.setdefault(d["mark"], []).append({**d, "page_no": sh.get("page_no")})
  out = []
  for mark, reads in sorted(by.items()):
    depths = sorted({r["depth_in"] for r in reads if r.get("depth_in")})
    steels = []
    
    for r in reads:
      if r.get("steel") and r["steel"] not in steels:
        steels.append(r["steel"])
    rec = {"mark": mark, "kind": reads[0].get("kind"), "pages": sorted({r["page_no"] for r in reads if r.get("page_no")}),
      "depth_mm": round(depths[0] * MM_INCH, 1) if len(depths) == 1 else None, "disagree": len(depths) > 1 or len(steels) > 1,
      "steel": steels[0] if len(steels) == 1 else None, "steel_text": steel_text(steels[0]) if len(steels) == 1 else None,
      "upstand": any(r.get("upstand") for r in reads)}
    out.append(rec)
  return out
