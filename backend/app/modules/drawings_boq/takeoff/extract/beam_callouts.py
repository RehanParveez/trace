from __future__ import annotations
import re
from app.engine.measure import rule_registry as RR
from app.engine.measure import steel_grammar as SG
from app.modules.drawings_boq.takeoff.extract import structure_tables as ST
from app.modules.drawings_boq.takeoff.page import lines as LN
from app.modules.drawings_boq.takeoff.page import access as AC
from app.modules.drawings_boq.takeoff.page import settings as PS
from app.modules.drawings_boq.takeoff.page.model import SECTION_PICTURE

RULE = "BEAM_CALLOUTS"
CAPTION_MARK = re.compile(r"^[A-Z]{1,2}-?\d{1,2}$")
CAPTION_WORDS = ("BEAM",)
NOTE_WORD = re.compile(r"^[A-Za-z]{2,}")

def enabled() -> bool:
  return RR.on(RULE)

def _level(a, b, h: float) -> bool:
  return abs(a.vc - b.vc) <= PS.get("beam_picture", "level") * h

def captions_of(words: list, h: float) -> list:
  reach = PS.get("beam_picture", "caption_gap") * h
  out = []
  for k in words:
    if k.turn != 0 or k.text.upper().strip(".:") not in CAPTION_WORDS:
      continue
    marks = [w for w in words if w is not k and w.turn == 0 and _level(w, k, h) and 0 <= w.u0 - k.u1 <= reach and CAPTION_MARK.match(w.text.upper())]
    if not marks:
      continue
    m = min(marks, key=lambda w: w.u0)
    out.append({"mark": m.text.upper().replace("-", ""), "u": (k.u0 + m.u1) / 2, "v": (k.vc + m.vc) / 2, "u0": k.u0, "u1": m.u1, "k": k, "word": m, "at": section_at(words, k, m, h)})
  return out

def section_at(words: list, k, m, h: float) -> str | None:
  below, reach = PS.get("beam_picture", "at_below") * h, PS.get("beam_picture", "at_reach") * h
  line = [w for w in words if w.turn == 0 and 0.3 * h <= k.vc - w.vc <= below and k.u0 - reach <= w.u0 <= m.u1 + reach]
  text = " ".join(w.text.upper() for w in sorted(line, key=lambda w: w.u0))
  support, mid = "SUPPORT" in text, "MID" in text or "SPAN" in text
  if support and not mid:
    return "SUPPORT"
  if mid and not support:
    return "MID SPAN"
  return None

def callouts_in(words: list, h: float) -> list:
  out = []
  for run in LN.runs(list(enumerate(words)), h):
    ws = [w for _i, w in run["words"]]
    for k, w in enumerate(ws):
      if w.turn != 0:
        continue
      text = INCH_PAIR.sub('"', w.text)
      got = SG.parse_callout(text)
      if got["bars"] and not got["unread"] and all(b.get("n") and b.get("bar") for b in got["bars"]) and not got["spaced"]:
        b = got["bars"][0]
        note = any(NOTE_WORD.match(o.text) for o in ws[k + 1:])
        out.append({"kind": "BARS", "text": "+".join(f"{g['n']}-#{g['bar']}" for g in got["bars"]), "n": b["n"], "bar": b["bar"], "u": w.uc, "v": w.vc, "note": note, "raw": w.raw})
      elif got["spaced"] and not got["unread"] and not got["bars"]:
        out.append({"kind": "RING", "text": text, "bar": got["spaced"][0]["bar"], "spacing_mm": got["spaced"][0]["spacing_mm"], "u": w.uc, "v": w.vc, "note": False, "raw": w.raw})
  return out

INCH_PAIR = re.compile(r"''|\u2019\u2019|\u201d")
INCHES = re.compile(r"""^(\d{1,3})\s*(?:["\u2033\u201d]|'{2})$""")

def _inches(text: str) -> int | None:
  m = INCHES.match(text.strip())
  return int(m.group(1)) if m else None

def _pitch(caps: list, k: dict, h: float) -> float:
  level = PS.get("beam_picture", "level") * h
  gaps = [abs(o["u"] - k["u"]) for o in caps if o is not k and abs(o["v"] - k["v"]) <= level]
  return min(gaps) if gaps else 2.0 * PS.get("beam_picture", "bind_reach") * h

def _owner(caps: list, u: float, v: float, h: float):
  weight, reach, tall = PS.get("beam_picture", "bind_weight"), PS.get("beam_picture", "bind_reach") * h, PS.get("beam_picture", "bind_height") * h
  left, right = PS.get("beam_picture", "room_left"), PS.get("beam_picture", "room_right")
  near = []
  for n, k in enumerate(caps):
    pitch = _pitch(caps, k, h)
    side = u - k["u"]
    if 0 < v - k["v"] <= tall and abs(side) <= reach and -left * pitch <= side <= right * pitch:
      near.append((v - k["v"] + weight * abs(side), n))
  return min(near)[1] if near else None

def read_picture(words: list, h: float) -> list:
  caps = captions_of(words, h)
  if not caps:
    return []
  
  taken: list = [{"calls": [], "wide": [], "tall": []} for _ in caps]
  for c in callouts_in(words, h):
    if not c["note"]:
      n = _owner(caps, c["u"], c["v"], h)
      if n is not None:
        taken[n]["calls"].append(c)
  for w in words:
    inch = _inches(w.text)
    if inch is None or w.turn not in (0, 1, 3):
      continue
    n = _owner(caps, w.uc, w.vc, h)
    if n is not None:
      taken[n]["wide" if w.turn == 0 else "tall"].append((w, inch))
      
  sections = []
  for cap, mine in zip(caps, taken):
    bars = sorted([c for c in mine["calls"] if c["kind"] == "BARS"], key=lambda c: -c["v"])
    rings = [c for c in mine["calls"] if c["kind"] == "RING"]
    rec = {"mark": cap["mark"], "at": cap["at"], "top": None, "bottom": None, "stirrup": None, "reasons": []}
    if len(bars) >= 2:
      rec["top"], rec["bottom"] = bars[0]["text"], bars[-1]["text"]
    elif len(bars) == 1:
      rec["reasons"].append("JOIN_MISSING")
    if rings and len(bars) >= 2:
      rec["stirrup"] = rings[0]["text"]
    if mine["wide"]:
      rec["width_in"] = max(mine["wide"], key=lambda p: p[0].vc)[1]
    if mine["tall"]:
      rec["vertical_in"] = [i for _w, i in sorted(mine["tall"], key=lambda p: -p[0].vc)]
    if rec["top"]:
      rec["point"] = _point(mine["wide"])
      sections.append(rec)
  return sections

def _point(wide: list) -> list | None:
  if not wide:
    return None
  w = max(wide, key=lambda p: p[0].vc)[0]
  return [round(w.raw.cx, 1), round(w.raw.cy, 1)]

def read_words(words: list, regions: list, h: float) -> dict | None:
  """The sections of a page that shows section pictures. A picture's region can miss its own caption or the strings beside it (a tall picture is cut where its stirrup ends), so every word of the page is looked at; a string is bound only to a caption that stands under it, within reach."""
  sections = read_picture(words, h) if regions else []
  return {"kind": "BEAM_CALLOUTS", "sections": sections} if sections else None

def read(raw, model: dict | None = None) -> dict | None:
  if not enabled() or not raw.words:
    return None
  words, _ = ST.upright_words(raw)
  model = model or AC.model_of(raw)
  return read_words(words, AC.regions_of(model, SECTION_PICTURE), float(model["h"]))

