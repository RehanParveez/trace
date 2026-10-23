from __future__ import annotations
import re

"""Reads the reinforcement callouts printed on a structural drawing ("4-#6 BOT", "#3 @ 6" C/C", "#4 @ 8" B.W.", "4-16Ø", "Ø8 @ 150 c/c") into plain bar sets
and spaced sets. Pure text in, plain numbers out, no drawing and no database. A bar number is the diameter in eighths of an inch (#4 is 1/2 in); a metric
callout gives the diameter in millimetres. Whatever does not read is returned as unread text and never guessed at (D30)."""

MM_INCH = 25.4
MM_FOOT = 304.8
BAR_NUMBERS = (2, 12)
DIA_MM = (6.0, 40.0)
BAR_COUNT = (1, 30)
SPACING_MM = (50.0, 610.0)
ROLES = ("bottom", "top", "vertical", "extra", "bars")

_FRACTIONS = {"½": " 1/2", "¼": " 1/4", "¾": " 3/4", "⅛": " 1/8", "⅜": " 3/8", "⅝": " 5/8", "⅞": " 7/8"}
_QUOTES = {"’": "'", "′": "'", "“": '"', "”": '"', "″": '"'}
_DIA_SIGNS = "ØøΦφФфϕ⌀"

def normalise(text: str) -> str:
  s = text or ""
  for k, v in _FRACTIONS.items():
    s = s.replace(k, v)
  for k, v in _QUOTES.items():
    s = s.replace(k, v)
  for ch in _DIA_SIGNS:
    s = s.replace(ch, "Ø")
  s = s.replace("×", "X").replace("–", "-").replace("—", "-")
  s = re.sub(r"\bC\s*[/\-.]\s*C\b\.?", "CC", s, flags=re.I)
  s = re.sub(r"\bB\s*\.?\s*W\b\.?", "BW", s, flags=re.I)
  s = re.sub(r"\bE\s*\.?\s*W\b\.?", "EW", s, flags=re.I)
  s = re.sub(r"\bO\s*\.?\s*W\b\.?", "OW", s, flags=re.I)
  s = re.sub(r"\bT\s*&\s*B\b", "TB", s, flags=re.I)
  s = re.sub(r"\bNOS?\b\.?", "NOS", s, flags=re.I)
  return re.sub(r"\s+", " ", s).strip().upper()

_N = r"(?P<n>\d{1,2})"
_SEP = r"\s*(?:-|NOS|X)?\s*"
_BAR_IMP = re.compile(r"(?<![#\d.])" + _N + _SEP + r"#\s*(?P<bar>\d{1,2})(?![\d])")
_BAR_MET = re.compile(r"(?<![#\d.])" + _N + _SEP + r"(?:Ø\s*(?P<d1>\d{1,2})|(?P<d2>\d{1,2})\s*(?:MM\s*Ø?|Ø))(?!\d)")
_SPACED_IMP = re.compile(r"#\s*(?P<bar>\d{1,2})\s*(?P<word>RINGS?|STIRRUPS?|TIES?|LINKS?)?\s*(?P<join>@|AT|-)\s*(?P<s>\d{1,3}(?:\.\d)?(?:\s+\d/\d)?)\s*"
  r"(?P<u>\"|'|IN\b|INCH(?:ES)?|MM|CM)?\s*(?P<cc>CC)?")
_SPACED_MET = re.compile(r"(?:Ø\s*(?P<d1>\d{1,2})|(?P<d2>\d{1,2})\s*MM\s*Ø?)\s*(?P<word>RINGS?|STIRRUPS?|TIES?|LINKS?)?\s*(?P<join>@|AT)\s*"
  r"(?P<s>\d{2,4}(?:\.\d)?)\s*(?P<u>MM|CM|\")?\s*(?P<cc>CC)?")
_WAYS_BOTH = re.compile(r"\b(BW|EW|BOTH WAYS|EACH WAY|BOTH DIRECTIONS)\b")
_WAYS_ONE = re.compile(r"\b(OW|ONE WAY|ONE DIRECTION)\b")
_LAYER_BOTH = re.compile(r"\b(TB|TOP (?:AND|&) BOTTOM|TOP/BOTTOM|BOTH FACES|EACH FACE|BOTH LAYERS)\b")
_ROLE_WORDS = (("bottom", re.compile(r"\b(BOT|BOTT|BOTTOM)\b")), ("top", re.compile(r"\bTOP\b")),
  ("vertical", re.compile(r"\b(VERT|VERTICAL|MAIN)\b")), ("extra", re.compile(r"\b(EXTRA|CURTAILED|ADDL|ADDITIONAL)\b")))
_MID = re.compile(r"(?P<s>\d{1,3}(?:\.\d)?)\s*(?P<u>\"|IN\b|MM|CM)?\s*(?:CC)?\s*(?:IN|AT|FOR)\s*(?:THE\s*)?(?:MIDDLE|MID|CENTRE|CENTER|REMAINING|REST)")
_ENDS = re.compile(r"\b(?:AT|NEAR|WITHIN)\s*(?:THE\s*)?(?:ENDS?|SUPPORTS?|JOINTS?)\b")
_ZONE = re.compile(r"(?:FOR|WITHIN|UP\s*TO|UPTO)\s*(?P<z>\d{1,2}(?:\.\d)?)\s*(?P<u>\"|'|MM|M\b)")
_ENDS_WORD = re.compile(r"^(?:AT|ENDS?|SUPPORTS?|MIDDLE|MID|FOR|NEAR|WITHIN|THE|ZONE)$")
_RING_WORD = re.compile(r"\b(RINGS?|STIRRUPS?|TIES?|LINKS?)\b")

def _spacing_mm(raw: str, unit: str | None, imperial: bool) -> float | None:
  parts = raw.split()
  try:
    value = float(parts[0]) + (eval_fraction(parts[1]) if len(parts) > 1 else 0.0)
  except (ValueError, ZeroDivisionError):
    return None
  u = (unit or "").upper()
  if u in ("MM",):
    mm = value
  elif u == "CM":
    mm = value * 10.0
  elif u == "'":
    mm = value * MM_FOOT
  elif u in ('"', "IN", "INCH", "INCHES"):
    mm = value * MM_INCH
  else:
    mm = value * MM_INCH if imperial else value
  return round(mm, 1) if SPACING_MM[0] <= mm <= SPACING_MM[1] else None

def eval_fraction(text: str) -> float:
  a, b = text.split("/")
  return float(a) / float(b)

def _role_after(s: str, start: int, stop: int) -> str | None:
  window = s[start:stop]
  for role, rx in _ROLE_WORDS:
    if rx.search(window):
      return role
  return None

def _bar_matches(s: str) -> list:
  found = []
  for m in _BAR_IMP.finditer(s):
    n, bar = int(m.group("n")), int(m.group("bar"))
    if BAR_COUNT[0] <= n <= BAR_COUNT[1] and BAR_NUMBERS[0] <= bar <= BAR_NUMBERS[1]:
      found.append((m.start(), m.end(), {"n": n, "bar": bar}))
  for m in _BAR_MET.finditer(s):
    n, d = int(m.group("n")), float(m.group("d1") or m.group("d2"))
    if BAR_COUNT[0] <= n <= BAR_COUNT[1] and DIA_MM[0] <= d <= DIA_MM[1]:
      found.append((m.start(), m.end(), {"n": n, "dia_mm": d}))
  found.sort(key=lambda t: t[0])
  return found

def _spaced_matches(s: str) -> list:
  found = []
  for m in _SPACED_IMP.finditer(s):
    bar = int(m.group("bar"))
    if not (BAR_NUMBERS[0] <= bar <= BAR_NUMBERS[1]):
      continue
    if m.group("join") == "-" and not m.group("cc"):
      continue
    sp = _spacing_mm(m.group("s"), m.group("u"), True)
    if sp is not None:
      found.append((m.start(), m.end(), {"bar": bar, "spacing_mm": sp}, m.group("word")))
  for m in _SPACED_MET.finditer(s):
    d = float(m.group("d1") or m.group("d2"))
    if not (DIA_MM[0] <= d <= DIA_MM[1]):
      continue
    sp = _spacing_mm(m.group("s"), m.group("u"), False)
    if sp is not None:
      found.append((m.start(), m.end(), {"dia_mm": d, "spacing_mm": sp}, m.group("word")))
  found.sort(key=lambda t: t[0])
  return found

def parse_callout(text: str) -> dict:
  """One printed note as {"text", "bars": [{role, n, bar|dia_mm}], "spaced": [{kind, bar|dia_mm, spacing_mm, ways, layers}], "unread": [...], "grade"}.
  A spaced set is a RING when the note calls it a ring, stirrup, tie or link, a MESH when it says both ways, each way or one way, and None when the
  note does not say, so the member it belongs to decides. grade is PRINTED when anything read and MISSING when nothing did."""
  s = normalise(text)
  out: dict = {"text": (text or "").strip(), "bars": [], "spaced": [], "unread": [], "grade": "MISSING"}
  if not s:
    return out
  spaced = _spaced_matches(s)
  taken = [(a, b) for a, b, *_ in spaced]
  bars = [t for t in _bar_matches(s) if not any(a <= t[0] < b for a, b in taken)]
  for i, (a, b, item, word) in enumerate(spaced):
    nxt = spaced[i + 1][0] if i + 1 < len(spaced) else len(s)
    prev_end = spaced[i - 1][1] if i else 0
    around = s[max(prev_end, a - 14):min(nxt, b + 24)]
    kind = "RING" if word or _RING_WORD.search(around) else None
    ways = 2 if _WAYS_BOTH.search(around) else 1 if _WAYS_ONE.search(around) else None
    
    if kind is None and ways is not None:
      kind = "MESH"
    layers = 2 if _LAYER_BOTH.search(around) else 1
    entry = {"kind": kind, **item, "ways": ways, "layers": layers}
    layer_words = [role for role in ("top", "bottom") if re.search(r"\b" + role.upper() + r"\b", around) or (role == "bottom" and re.search(r"\bBOT\b", around))]
    if len(layer_words) == 1 and layers == 1:
      entry["layer"] = layer_words[0]
    out["spaced"].append(entry)
  for i, (a, b, item) in enumerate(bars):
    nxt = bars[i + 1][0] if i + 1 < len(bars) else len(s)
    role = _role_after(s, b, nxt)
    if role is None and i:
      role = None
      
    out["bars"].append({"role": role or "bars", **item})
  if len(out["bars"]) == 2 and all(b["role"] == "bars" for b in out["bars"]):
   
    out["bars"][0]["role"], out["bars"][1]["role"] = "bottom", "top"
    out["order_assumed"] = True
  mid = _MID.search(s)
  if mid and out["spaced"] and _ENDS.search(s):
    general = _spacing_mm(mid.group("s"), mid.group("u"), True)
    first = out["spaced"][0]
    if general is not None and general > first["spacing_mm"]:
      first["dense_spacing_mm"], first["spacing_mm"] = first["spacing_mm"], general
      zone = _ZONE.search(s)
      if zone:
        unit = zone.group("u")
        zv = float(zone.group("z"))
        first["dense_zone_mm"] = round(zv * (MM_FOOT if unit == "'" else MM_INCH if unit == '"' else 1000.0 if unit == "M" else 1.0), 1)
      taken.append((mid.start(), mid.end()))
  covered = sorted([(a, b) for a, b, *_ in spaced] + [(a, b) for a, b, _ in bars] + ([(mid.start(), mid.end())] if mid and "dense_spacing_mm" in (out["spaced"][0] if out["spaced"] else {}) else []))
  
  rest, pos = [], 0
  for a, b in covered:
    rest.append(s[pos:a])
    pos = max(pos, b)
  rest.append(s[pos:])
  left = [re.sub(r"[^A-Z0-9#@\"'/.&-]+", " ", r).strip() for r in rest]
  noise = re.compile(r"^(?:|AND|&|WITH|WITH THE|IN|THE|AS|OF|REINF\.?|REINFORCEMENT|STEEL|BARS?|MAIN|ALL|NOS|TOTAL|GRADE|C|CC|BW|EW|OW|TB|BOT|BOTT|BOTTOM|TOP|VERT|VERTICAL|EXTRA|RINGS?|TIES?|STIRRUPS?|LINKS?|AT|[-@./,&]+)$")
  words = [w for r in left for w in (x.strip(".,") for x in r.split()) if not noise.match(w) and not _ENDS_WORD.match(w)]
  out["unread"] = words
  out["grade"] = "PRINTED" if (out["bars"] or out["spaced"]) else "MISSING"
  return out

def _group(b: dict) -> dict:
  g = {"n": b["n"]}
  g["bar" if "bar" in b else "dia_mm"] = b.get("bar", b.get("dia_mm"))
  return g

def to_steel(callouts: list, family: str) -> tuple:
  """The bar and ring sets of one member from the notes printed for it, as (steel dict or None, problems). family is COLUMN, BEAM, LINTEL, FOOTING, SLAB or
  RCC_WALL. A beam or column takes bar sets and rings; a footing, slab or wall takes a mesh. A problem is a plain code saying what could not be settled."""
  steel: dict = {}
  problems: list = []
  ringed = family in ("COLUMN", "BEAM", "LINTEL")
  meshed = family in ("FOOTING", "SLAB", "RCC_WALL")
  
  for c in callouts:
    for b in c.get("bars") or []:
      role = b["role"]
      if family == "COLUMN" and role in ("bars", "bottom", "top"):
        role = "vertical"
      if not ringed and not meshed:
        continue
      if meshed:
        problems.append("BAR_SET_ON_MESH_MEMBER")
        continue
      if role in steel:
        if steel[role] != _group(b):
          problems.append("BAR_SETS_DISAGREE")
        continue
      
      steel[role] = _group(b)
    for sp in c.get("spaced") or []:
      kind = sp["kind"] or ("RING" if ringed else "MESH")
      if kind == "RING" and ringed:
        ring = {k: sp[k] for k in ("bar", "dia_mm", "spacing_mm", "dense_spacing_mm", "dense_zone_mm") if k in sp}
        if "ring" in steel and steel["ring"] != ring:
          if steel["ring"].get("spacing_mm", 0) > ring["spacing_mm"] and "dense_spacing_mm" not in steel["ring"]:
            steel["ring"]["dense_spacing_mm"] = ring["spacing_mm"]
          elif steel["ring"].get("spacing_mm", 0) < ring["spacing_mm"]:
            problems.append("RING_SETS_DISAGREE")
          else:
            problems.append("RING_SETS_DISAGREE")
        else:
          steel["ring"] = ring
      elif kind == "MESH" and meshed:
        ways = sp["ways"] or (2 if family in ("FOOTING", "SLAB") else 2)
        mesh = {k: sp[k] for k in ("bar", "dia_mm", "spacing_mm") if k in sp}
        mesh["ways"] = ways
        mesh["layers"] = sp["layers"]
        if sp.get("layer"):
          mesh["layer"] = sp["layer"]
        if "mesh" in steel and steel["mesh"] != mesh:
          problems.append("MESH_SETS_DISAGREE")
        else:
          steel["mesh"] = mesh
      else:
        problems.append("SPACED_SET_DOES_NOT_FIT_MEMBER")
  return (steel or None), sorted(set(problems))

def steel_text(steel: dict | None) -> str:
  """The reinforcement of a member as a short readable line, for a candidate's facts and the BOQ."""
  if not steel:
    return ""
  parts = []
  for role in ROLES:
    g = steel.get(role)
    if g:
      parts.append(f"{g['n']} {_dia_label(g)} {role if role != 'bars' else 'bars'}")
  r = steel.get("ring")
  if r:
    extra = f", {r['dense_spacing_mm'] / MM_INCH:g} in at the ends" if r.get("dense_spacing_mm") else ""
    parts.append(f"rings {_dia_label(r)} at {r['spacing_mm'] / MM_INCH:g} in{extra}")
  pn = steel.get("panels")
  if pn:
    parts.append(f"bars of {len(pn)} slab panels")
  m = steel.get("mesh")
  if m:
    parts.append(f"mesh {_dia_label(m)} at {m['spacing_mm'] / MM_INCH:g} in {'both ways' if m.get('ways', 2) == 2 else 'one way'}"
      + (f", {m['layers']} layers" if m.get("layers", 1) > 1 else ""))
  return ", ".join(parts)

def _dia_label(g: dict) -> str:
  return f"#{g['bar']}" if "bar" in g else f"{g['dia_mm']:g} mm"
