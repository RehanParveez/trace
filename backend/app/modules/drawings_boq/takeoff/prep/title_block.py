from __future__ import annotations
import re

LABELS = (
  ("sheet_no", re.compile(r"^(?:SHEET|DWG|DRG|DRAWING)\s*(?:NO|NUMBER|#)\.?\s*[:\-]?\s*(?P<v>.*)$", re.I)),
  ("title", re.compile(r"^(?:DRAWING\s+)?TITLE\s*[:\-]?\s*(?P<v>.*)$", re.I)),
  ("scale", re.compile(r"^SCALE\s*[:\-]?\s*(?P<v>.*)$", re.I)),
  ("revision", re.compile(r"^(?:REV|REVISION|ISSUE)\.?\s*[:\-]?\s*(?P<v>.*)$", re.I)),
  ("project", re.compile(r"^(?:PROJECT(?:\s+NAME)?|CLIENT|OWNER)\s*[:\-]?\s*(?P<v>.*)$", re.I)),
  ("date", re.compile(r"^DATE\s*[:\-]?\s*(?P<v>.*)$", re.I)),
)

OPTION_RX = re.compile(r"\bOPTION\s*#?\s*(\d+|[A-C])\b|\bALT(?:ERNATIVE)?\s*#?\s*(\d)\b", re.I)
REV_RX = re.compile(r"\bREV(?:ISION)?\.?\s*#?\s*(\d+|[A-Z])\b", re.I)
DATE_RX = re.compile(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b")

def option_of(texts: list) -> dict | None:
  for t in texts:
    m = OPTION_RX.search(t or "")
    if m:
      label = f"OPTION {m.group(1).upper()}" if m.group(1) else f"ALT {m.group(2)}"
      return {"label": label, "text": re.sub(r"\s+", " ", t.strip())[:90]}
  return None

def _iso(m) -> str | None:
  d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
  return f"{y:04d}-{mo:02d}-{d:02d}" if 1 <= mo <= 12 and 1 <= d <= 31 else None

def stamps_of(texts: list) -> list:
  out: list = []
  for t in texts:
    m = REV_RX.search(t or "")
    if m:
      d = DATE_RX.search(t)
      out.append({"rev": m.group(1).upper(), "date": _iso(d) if d else None})
  seen: set = set()
  return [s for s in out if not ((s["rev"], s["date"]) in seen or seen.add((s["rev"], s["date"])))]

ZONE_RIGHT = 0.70
ZONE_BOTTOM = 0.30
MAX_VALUE = 80

def zone_words(words: list, cropbox: tuple) -> list:
  l, b, r, t = cropbox
  w, h = max(r - l, 1.0), max(t - b, 1.0)
  return [x for x in words if x.cx >= l + ZONE_RIGHT * w or x.cy <= b + ZONE_BOTTOM * h]

def read(lines: list) -> dict:
  fields: dict = {}
  evidence: list = []

  texts = [t.strip() for t, _s in lines if t and t.strip()]
  for i, text in enumerate(texts):
    for key, rx in LABELS:
      m = rx.match(text)
      if not m or key in fields:
        continue
      value = (m.group("v") or "").strip()
      if not value and i + 1 < len(texts) and not any(r.match(texts[i + 1]) for _k, r in LABELS):
        value = texts[i + 1]
      if value:
        fields[key] = value[:MAX_VALUE]
        evidence.append({"label": key, "text": text[:MAX_VALUE]})
      break
  return {"fields": fields, "evidence": evidence}
