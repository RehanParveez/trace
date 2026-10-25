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
