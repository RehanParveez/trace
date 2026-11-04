from __future__ import annotations
import math
import os
import re
from app.engine.measure import readings as RD

WORDS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "words.txt")
TOKEN = re.compile(r"[A-Za-z]{3,}")
OFFSETS = [k for k in range(-64, 65) if k]
SHIFTS = (1, -1, 2, -2, 3, -3)
FONT_DECODED, GLYPH_REPAIRED, STACKED_FRACTION = "FONT_DECODED", "GLYPH_REPAIRED", "STACKED_FRACTION"
SPACE_CODE = "\x03"
FRACTION_DENOMINATORS = (2, 4, 8, 16)
_words: set = set()

def words() -> set:
  if not _words:
    with open(WORDS_PATH, encoding="utf-8") as fh:
      _words.update(w.strip().upper() for w in fh if w.strip())
  return _words

def tokens(text: str) -> list:
  return TOKEN.findall(text)

def word_passes(text: str) -> bool:
  toks = tokens(text)
  if not toks:
    return False
  letters = sum(len(t) for t in toks)
  return all(t.upper() in words() for t in toks) and letters >= 0.6 * len(text.replace(" ", ""))

def pass_rate(texts: list) -> tuple:
  if not texts:
    return None, 0
  ok = sum(1 for s in texts if word_passes(s))
  return round(ok / len(texts), 4), ok

def shift_char(c: str, k: int) -> str:
  if "A" <= c <= "Z":
    return chr((ord(c) - 65 + k) % 26 + 65)
  if "a" <= c <= "z":
    return chr((ord(c) - 97 + k) % 26 + 97)
  return c

def offset_char(c: str, k: int) -> str:
  if c == SPACE_CODE:
    return " "
  o = ord(c) + k
  return chr(o) if ord(c) > 32 and 33 <= o < 127 else c

def apply_decoding(text: str, kind: str, value: int) -> str:
  fn = offset_char if kind == "offset" else shift_char
  return "".join(fn(c, value) for c in text)

def best_decoding(texts: list, base: float) -> dict:
  best = {"kind": None, "value": None, "rate": base, "gain": 0.0}
  for kind, values in (("offset", OFFSETS), ("shift", SHIFTS)):
    for k in values:
      rate, _n = pass_rate([apply_decoding(s, kind, k) for s in texts])
      if rate is not None and rate - base > best["gain"] + 1e-9:
        best = {"kind": kind, "value": k, "rate": rate, "gain": round(rate - base, 4)}
  return best

def decide_fonts(texts: list, fonts: list) -> dict:
  by_font: dict = {}
  for text, font in zip(texts, fonts):
    if font:
      by_font.setdefault(font, []).append(text)
  out: dict = {}
  
  for font, group in by_font.items():
    if len(group) < RD.FONT_DECODE_MIN_WORDS:
      continue
    base, _ok = pass_rate(group)
    if base is None or base >= RD.FONT_DECODE_ONLY_BELOW:
      continue
  
    best = best_decoding(group, base)
    passing = pass_rate([apply_decoding(t, best["kind"], best["value"]) for t in group])[1] if best["kind"] else 0
    if best["kind"] and passing >= RD.FONT_DECODE_MIN_PASSING and best["gain"] >= RD.FONT_DECODE_MIN_GAIN and best["rate"] >= RD.FONT_DECODE_MIN_RATE:
      out[font] = {"kind": best["kind"], "value": best["value"], "words": len(group), "before": base, "after": best["rate"]}
  return out

def decoders_of(decisions: dict) -> dict:
  return {font: (d["kind"], d["value"]) for font, d in decisions.items()}

def decode_char(c: str, decoder: tuple) -> str:
  kind, value = decoder
  return offset_char(c, value) if kind == "offset" else shift_char(c, value)

def _frame(main, other) -> tuple:
  a = math.radians(main.angle)
  dx, dy = other.cx - main.cx, other.cy - main.cy
  return dx * math.cos(a) + dy * math.sin(a), -dx * math.sin(a) + dy * math.cos(a)

def _is_digit(w) -> bool:
  return len(w.text) == 1 and w.text.isdigit()

def _stacked_candidates(words: list) -> list:
  digits = [w for w in words if _is_digit(w)]
  if len(digits) < 2:
    return []
  taken: set = set()
  
  found = []
  for main in words:
    if not re.search(r"\d$", main.text) or len(main.text) > 12 or main.text.endswith('"') or id(main) in taken:
      continue
    half = main.length / 2.0
    near = []
    
    for w in digits:
      if id(w) in taken or w is main or abs(w.angle - main.angle) > 8 and abs(abs(w.angle - main.angle) - 360) > 8:
        continue
      u, v = _frame(main, w)
      if half - 0.2 * main.size <= u <= half + 2.5 * main.size and 0.2 * main.size <= abs(v) <= 1.1 * main.size and 0.4 <= w.size / max(main.size, 1e-9) <= 1.3:
        near.append((u, v, w))
    ups = [t for t in near if t[1] > 0]
    downs = [t for t in near if t[1] < 0]
    if len(ups) != 1 or len(downs) != 1 or abs(ups[0][0] - downs[0][0]) > 0.9 * main.size:
      continue
    num, den = ups[0][2], downs[0][2]
    n, d = int(num.text), int(den.text)
    if not (0 < n < d and d in FRACTION_DENOMINATORS):
      continue
  
    quote = None
    for w in words:
      if w.text in ('"', "\u201d", "\u2033"):
        u, v = _frame(main, w)
        if half < u <= half + 4.5 * main.size and abs(v) <= 0.9 * main.size:
          quote = w
          break
    taken.update((id(num), id(den)))
    found.append((main, num, den, quote, n / d))
  return found

def _inches_of(text: str):
  from app.modules.drawings_boq.takeoff.prep import texts as T
  r = T.parse_dimension(text)
  return r[0].value_mm / 25.4 if r else None

def _coords(w) -> tuple:
  a = math.radians(w.angle)
  return w.cx * math.cos(a) + w.cy * math.sin(a), -w.cx * math.sin(a) + w.cy * math.cos(a)

def _confirmed(candidates: list, words: list) -> set:
  fraction = {id(c[0]): c[4] for c in candidates}
  dims = []
  
  for w in words:
    if ("'" in w.text or id(w) in fraction) and len(w.text) <= 14:
      v = _inches_of(w.text + '"' if id(w) in fraction and not w.text.endswith('"') else w.text)
      if v is not None:
        alo, across = _coords(w)
        dims.append({"w": w, "v": v, "along": alo, "across": across, "q": int(round(w.angle / 90.0)) % 4, "size": w.size})
        
  rows: list = []
  for d in sorted(dims, key=lambda d: (d["q"], d["across"])):
    for r in rows:
      if r["q"] == d["q"] and abs(r["across"] - d["across"]) <= 0.6 * max(r["size"], d["size"]):
        r["items"].append(d)
        break
    else:
      rows.append({"q": d["q"], "across": d["across"], "size": d["size"], "items": [d]})
      
  ok: set = set()
  for row in rows:
    chain = row["items"]
    if len(chain) < 2:
      continue
    lo, hi = min(d["along"] for d in chain), max(d["along"] for d in chain)
    for t in dims:
      if t["q"] != row["q"] or any(t is d for d in chain):
        continue
      off = abs(t["across"] - row["across"])
      if not (0.5 * row["size"] <= off <= 6.0 * row["size"]) or not (lo - 0.5 * row["size"] <= t["along"] <= hi + 0.5 * row["size"]):
        continue
      with_f = sum(d["v"] + fraction.get(id(d["w"]), 0.0) for d in chain)
      without = sum(d["v"] for d in chain)
      want = t["v"] + fraction.get(id(t["w"]), 0.0)
      if abs(with_f - want) < 0.01 and abs(without - want) > 0.4:
        ok.update(id(d["w"]) for d in chain if id(d["w"]) in fraction)
        if id(t["w"]) in fraction:
          ok.add(id(t["w"]))
  return ok

def merge_stacked_fractions(words: list) -> list:
  candidates = _stacked_candidates(words)
  if not candidates:
    return []
  ok = _confirmed(candidates, words)
  merges, drop = [], set()
  for main, num, den, quote, frac in candidates:
    if id(main) not in ok:
      continue
  
    n, d = int(num.text), int(den.text)
    before = main.text
    main.text = f'{main.text} {n}/{d}"'
    main.repair = STACKED_FRACTION
    drop.update((id(num), id(den)) + ((id(quote),) if quote else ()))
    merges.append({"was": before, "now": main.text, "kind": STACKED_FRACTION, "status": "READ"})
  if drop:
    words[:] = [w for w in words if id(w) not in drop]
  return merges

STEEL_BARS = re.compile(r"^(\d{1,2})-(\d)$")
SLAB_CALLOUT = re.compile(r'^(#?)(\d)@(\d{1,3})"?(C/?C)$')
CONTEXT_WORDS = re.compile(r"^(thr|ext)\.?$", re.I)
CONTEXT_RADIUS = 6.0

def _near(w, words: list, radius_sizes: float) -> list:
  r = radius_sizes * max(w.size, 1.0)
  return [o for o in words if o is not w and math.hypot(o.cx - w.cx, o.cy - w.cy) <= r]

def _row_label(w, words: list, label: str) -> bool:
  for o in words:
    if o is w or o.text.strip().upper() != label:
      continue
    u, v = _frame(o, w)
    if abs(v) <= 0.8 * max(o.size, w.size) and u > 0:
      return True
  return False

def _fix_callout(t: str, limit: int):
  m = SLAB_CALLOUT.match(t)
  if not m:
    return None
  hashed, d, digits, cc = m.groups()
  if not cc:
    return None
  spacing_text = f'{digits}"'
  if int(digits) > limit and len(digits) == 2:
    a, b = int(digits[0]), int(digits[1:])
    if a < b <= 12:
      spacing_text = f'{a}"/{b}"'
  new = f"#{d}@{spacing_text}C/C"
  return new if new != t.strip() else None

NUMBER_LABELS = ("DRAWING", "DWG", "SHEET", "PROJECT", "JOB", "FILE")

def repair_labels(words: list) -> list:
  hits = []
  for lab in words:
    if lab.text.strip().upper() not in NUMBER_LABELS:
      continue
    half = lab.length / 2.0
    for o in words:
      if o is lab or len(o.text) != 1 or o.text.isalnum() or o.text in "#.:":
        continue
      u, v = _frame(lab, o)
      if half - 0.2 * lab.size <= u <= half + 3.0 * lab.size and abs(v) <= 0.6 * lab.size and ord(o.text) < 32:
        hits.append(o)
        break
    
  out = []
  glyphs = [o.text for o in hits]
  for o in hits:
    same = glyphs.count(o.text)
    was = o.text
    o.text = "#"
    o.repair = GLYPH_REPAIRED
    out.append({"was": repr(was), "now": "#", "kind": GLYPH_REPAIRED, "status": "READ" if same >= 2 else "UNSURE"})
  return out

def repair_grammar(words: list) -> list:
  out = []
  for w in words:
    t = w.text.strip()
    new = None
    
    if "@" in t:
      beam = any(CONTEXT_WORDS.match(o.text.strip()) for o in _near(w, words, CONTEXT_RADIUS * 3))
      new = _fix_callout(t, RD.MAX_TIE_SPACING_IN if beam else RD.MAX_SLAB_SPACING_IN)
    else:
      m = STEEL_BARS.match(t)
      if m and (any(CONTEXT_WORDS.match(o.text.strip()) for o in _near(w, words, CONTEXT_RADIUS)) or _row_label(w, words, "STEEL")):
        new = f"{m.group(1)}-#{m.group(2)}"
    if new and new != t:
      out.append({"was": t, "now": new, "kind": GLYPH_REPAIRED, "status": "UNSURE"})
      w.text = new
      w.repair = GLYPH_REPAIRED
  return out
