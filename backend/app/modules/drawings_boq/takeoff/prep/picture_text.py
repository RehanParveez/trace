from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.prep.texts import build_lines, to_visual
from app.modules.drawings_boq.takeoff.prep import beam_details as BD
from app.modules.drawings_boq.takeoff.prep import tank_details as TD

TEXT_VOTES = 3

def region_words(words: list, region: tuple, crop: tuple, rotation: int, page_wh: tuple) -> list:
  """The words whose centre lies in `region` (visual page units), with where each is in those units: [(word, x, y)]."""
  Wv, Hv = page_wh
  out = []
  for w in words:
    u, v = to_visual(w.cx, w.cy, crop, rotation)
    x, y = u * Wv, v * Hv
    if region[0] <= x <= region[2] and region[1] <= y <= region[3]:
      out.append((w, x, y))
  return out

def _pieces(inside: list) -> list:
  """Every word and every line of words in the region as a piece of text with its place and whether it reads upward: [(text, x, y, vertical)]. A note split
  over two words (3-#4 TOP, #3@6"C/C) is found as the line."""
  pieces = [(w.text, x, y, round(w.angle / 90.0) % 2 == 1) for w, x, y in inside]
  ids = {id(w): (x, y) for w, x, y in inside}
  for ln in build_lines([w for w, _, _ in inside]):
    if len(ln.spans) < 2:
      continue
    ws = [w for _, _, w in ln.spans]
    xs = [ids[id(w)][0] for w in ws if id(w) in ids]
    ys = [ids[id(w)][1] for w in ws if id(w) in ids]
    if xs:
      pieces.append((ln.text, sum(xs) / len(xs), sum(ys) / len(ys), ln.angle % 180 == 90))
  return pieces

def beam_picture(inside: list) -> dict:

  bars, stirrups, dims = [], [], []
  for text, x, y, vertical in _pieces(inside):
    b = BD.parse_bars(text)
    if b:
      bars += [{**b, "x": x, "y": y}] * TEXT_VOTES
    s = BD.parse_stirrup(text)
    if s:
      stirrups += [{**s, "x": x, "y": y}] * TEXT_VOTES
    d = BD.parse_dim(text)
    if d:
      dims += [{"v": d, "orient": "V" if vertical else "H", "x": x, "y": y}] * TEXT_VOTES
  return {"bars": bars, "stirrups": stirrups, "dims": dims, "reads": 0, "from_text": bool(bars or stirrups or any(d["orient"] == "V" for d in dims))}

def tank_lengths(inside: list) -> list:
  """The sizes written as text inside a tank drawing: [{"text", "inches", "votes", "source": "TEXT"}] (3'-6" is 42 inches)."""
  
  seen: dict = {}
  for text, _x, _y, _v in _pieces(inside):
    got = TD.parse_length(text)
    if got and got["inches"] not in seen:
      seen[got["inches"]] = {"text": got["text"], "inches": got["inches"], "votes": TEXT_VOTES, "source": "TEXT"}
  return sorted(seen.values(), key=lambda r: r["inches"])
