from __future__ import annotations
import re
import difflib

GAP_SPLIT = 2.2
TALL_WORD = 5.0
SAME_LINE = 0.55
VALUE_RIGHT_MAX = 10.0
VALUE_BELOW_MAX = 3.5
ZONE_RIGHT = 0.70
ZONE_BOTTOM = 0.30
MAX_NO_CHARS = 30

_NO_LABEL = r"(?:DRAWING|DRAWINGS|DRG|DWG|SHEET)\s*(?:NO|NUMBER|NUM|#)\.?"
LABELS = (
  ("sheet_no", re.compile(r"^" + _NO_LABEL + r"\s*:?$", re.I)),
  ("sheet_no_weak", re.compile(r"^(?:NO|NUMBER)\.?\s*:?$", re.I)),
  ("title", re.compile(r"^(?:(?:DRAWING|SHEET)\s*)?TITLE\s*:?$|^DRAWING\s*:$", re.I)),
  ("revision", re.compile(r"^(?:REV|REVISION|ISSUE)\.?(?:\s*NO\.?)?\s*:?$", re.I)),
  ("scale", re.compile(r"^SCALES?\s*:?$", re.I)),
  ("date", re.compile(r"^(?:ISSUE\s+)?DATE\s*:?$", re.I)),
)

INLINE_NO = re.compile(r"^" + _NO_LABEL + r"\s*[:\-]\s*(?P<v>\S.*)$", re.I)
_SCALE_VALUE = re.compile(r"^(?:\d+\s*:\s*\d[\d,.]*|N\.?\s?T\.?\s?S\.?|AS\s+SHOWN|VARIES|NOT\s+TO\s+SCALE|\d+(?:/\d+)?\s*\"\s*=\s*\d+\s*'(?:\s*-\s*\d+\s*\"?)?|\d+(?:/\d+)?\s*\"\s*=\s*\d+\s*'?)$", re.I)
_MONTH = r"JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC"
_DATE_VALUE = re.compile(r"^(?:\d{1,2}\s*[-/.]\s*\d{1,2}\s*[-/.]\s*\d{2,4}|(?:\d{1,2}[ -]*)?(?:" + _MONTH + r")[A-Z]*[ ,.\-]*(?:\d{1,2}[ ,.\-]*)?\d{2,4})$", re.I)
_REV_VALUE = re.compile(r"^[A-Z0-9]{1,3}$|^[A-Z]-?\d{1,2}$", re.I)
_LABEL_WORD = re.compile(r"^(?:DRAWING|DRG|DWG|SHEET|REV|REVISION|DATE|SCALE|TITLE|PROJECT|CLIENT|DRAWN|CHECKED|DESIGNED|APPROVED|NO\.?|NUMBER)\b", re.I)

def _frame(w) -> tuple:
  q = int(round(float(w.angle or 0.0) / 90.0)) % 4
  if q == 0:
    return q, w.x0, w.x1, w.y0, w.y1
  if q == 1:
    return q, w.y0, w.y1, -w.x1, -w.x0
  if q == 2:
    return q, -w.x1, -w.x0, -w.y1, -w.y0
  return q, -w.y1, -w.y0, w.x0, w.x1

def phrases(words: list) -> list:
  by_q: dict = {}

  usable = [w for w in words if (w.text or "").strip() and abs(((float(w.angle or 0.0) + 45) % 90) - 45) <= 8]
  heights = sorted((_frame(w)[4] - _frame(w)[3]) for w in usable)
  cap = TALL_WORD * heights[len(heights) // 2] if heights else 1e9
  for w in usable:
    q, a0, a1, c0, c1 = _frame(w)
    if c1 - c0 > cap:
      continue
    by_q.setdefault(q, []).append((a0, a1, c0, c1, w.text.strip(), w.x0, w.y0, w.x1, w.y1))

  out: list = []
  for q, items in by_q.items():
    items.sort(key=lambda t: -(t[2] + t[3]) / 2.0)
    lines: list = []
    for it in items:
      mid = (it[2] + it[3]) / 2.0
      h = it[3] - it[2]
      for ln in lines:
        if abs(mid - ln["mid"]) <= SAME_LINE * max(h, ln["h"]):
          ln["items"].append(it)
          n = len(ln["items"])
          ln["mid"] += (mid - ln["mid"]) / n
          ln["h"] = max(ln["h"], h)
          break
      else:
        lines.append({"mid": mid, "h": h, "items": [it]})
        
    for ln in lines:
      its = sorted(ln["items"], key=lambda t: t[0])
      cur = [its[0]]
      for it in its[1:]:
        gap = it[0] - cur[-1][1]
        h = max(it[3] - it[2], cur[-1][3] - cur[-1][2])
        if gap > GAP_SPLIT * h:
          out.append(_phrase(q, cur))
          cur = [it]
        else:
          cur.append(it)
      out.append(_phrase(q, cur))
  return out

def _phrase(q: int, its: list) -> dict:
  c0 = min(t[2] for t in its)
  c1 = max(t[3] for t in its)
  return {"q": q, "text": " ".join(t[4] for t in its), "bbox": (min(t[5] for t in its), min(t[6] for t in its), max(t[7] for t in its), max(t[8] for t in its)), "a0": its[0][0], "a1": max(t[1] for t in its), "c0": c0, "c1": c1, "h": max(t[3] - t[2] for t in its), "mid": (c0 + c1) / 2.0}

def clean_no(text: str) -> str:
  t = re.sub(r"\s*([-/.])\s*", r"\1", (text or "").strip())
  t = re.sub(r"\s+", " ", t).strip(" .:,;|_\u00b7\u2022'\"`")
  t = t.upper()
  m = re.match(r"^([A-Z]{1,3}) (\d{1,4}[A-Z]?)$", t)
  return f"{m.group(1)}-{m.group(2)}" if m else t

def key(text: str) -> str:
  return re.sub(r"[^A-Z0-9]", "", (text or "").upper())

_YEAR = re.compile(r"^(?:19|20)\d\d$")

def _fits(field: str, text: str) -> bool:
  t = (text or "").strip()
  if not t or _LABEL_WORD.match(t) and field != "title":
    return False
  if field in ("sheet_no", "sheet_no_weak"):
    k = key(t)
    return 2 <= len(k) <= MAX_NO_CHARS and any(ch.isdigit() for ch in k) and len(t.split()) <= 4 and not _SCALE_VALUE.match(t) and not _DATE_VALUE.match(t) and not _YEAR.match(t)

  if field == "revision":
    return bool(_REV_VALUE.match(t.strip(" .")))
  if field == "scale":
    return bool(_SCALE_VALUE.match(t))
  if field == "date":
    return bool(_DATE_VALUE.match(t)) and len(t) <= 24
  return len(re.findall(r"[A-Za-z]{3,}", t)) >= 1 and not _LABEL_WORD.match(t)

_FUZZY_NO = re.compile(r"^(\S{3,9})\s*(?:NO|NUMBER|#)\.?\s*:?$", re.I)
FUZZY_MIN = 0.65

def _label_field(text: str):
  t = text.strip()
  for field, rx in LABELS:
    if rx.match(t):
      return field
  m = _FUZZY_NO.match(t)
  if m and not t.upper().startswith(("NO", "NUMBER")):
    first = m.group(1).upper()
    if any(difflib.SequenceMatcher(None, first, word).ratio() >= FUZZY_MIN for word in ("DRAWING", "DRG", "DWG", "SHEET")):
      return "sheet_no"
  return None

def _candidates(label: dict, ph: list, field: str) -> list:
  out = []
  H = label["h"]
  for p in ph:
    if p is label or p["q"] != label["q"] or _label_field(p["text"]):
      continue
    h = max(H, p["h"])
    if abs(p["mid"] - label["mid"]) <= 0.6 * h and -0.5 * h <= p["a0"] - label["a1"] <= VALUE_RIGHT_MAX * h:
      out.append((p["a0"] - label["a1"], "RIGHT", p))
      continue
    
    drop = label["c0"] - p["c1"]
    if -0.3 * h <= drop <= VALUE_BELOW_MAX * h and p["a0"] <= label["a1"] + 6.0 * H and p["a1"] >= label["a0"] - 6.0 * H:
      out.append((drop + 0.2 * abs(p["a0"] - label["a0"]), "BELOW", p))
  out.sort(key=lambda t: t[0])
  return [(how, p) for _d, how, p in out if _fits(field, p["text"])]

def read(words: list, cropbox: tuple) -> dict:
  ph = phrases(words)
  l, b, r, t = cropbox
  w, h = max(r - l, 1.0), max(t - b, 1.0)
  found: dict = {}
  evidence: list = []
  for p in ph:
    if p["q"] != 0:
      continue

    m = INLINE_NO.match(p["text"].strip())
    if m and _fits("sheet_no", m.group("v")):
      found.setdefault("sheet_no", []).append((3.0, clean_no(m.group("v")), p, "INLINE"))
  for lab in ph:
    field = _label_field(lab["text"])
    if not field:
      continue
    zone = 0.0
    if lab["q"] == 0:
      cx = (lab["a0"] + lab["a1"]) / 2.0
      cy = lab["mid"]
      zone = 1.5 if (cx >= l + ZONE_RIGHT * w or cy <= b + ZONE_BOTTOM * h) else 0.0
    if field == "sheet_no_weak" and not zone:
      continue
    cands = _candidates(lab, ph, field)
    if not cands:
      continue

    how, p = cands[0]
    text = p["text"]
    if field == "title":
      follow = [q for q in ph if q["q"] == p["q"] and q is not p and not _label_field(q["text"]) and 0 < p["c0"] - q["c1"] <= 1.6 * max(p["h"], q["h"]) and q["a0"] <= p["a1"] and q["a1"] >= p["a0"] and _fits("title", q["text"])]
      if follow:
        text = text + " " + sorted(follow, key=lambda q: -q["c1"])[0]["text"]
    value = clean_no(text) if field in ("sheet_no", "sheet_no_weak") else re.sub(r"\s+", " ", text).strip(" :")[:80]
    if field == "sheet_no_weak":
      found.setdefault("sheet_no", []).append((zone + 0.5, value, p, how + "_NO_ONLY"))
      continue
    found.setdefault(field, []).append((zone + 2.0, value, p, how))

  fields: dict = {}
  for field, rows in found.items():
    rows.sort(key=lambda x: -x[0])
    score, value, p, how = rows[0]
    fields[field] = value
    evidence.append({"label": field, "value": value[:60], "how": how, "in_strip": score >= 3.5})
  return {"fields": fields, "evidence": evidence}
