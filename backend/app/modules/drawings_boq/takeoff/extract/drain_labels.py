from __future__ import annotations
import re
from app.engine.measure import rule_registry as RR

RULE = "DRAIN_LABEL_ITEMS"
META_KEY = "drain_label_items"
SOURCE_KEY = "drain_labels"
DISCIPLINES = ("PLUMBING",)
ROLES = ("PLAN",)

LABELS = (
  ("MH", re.compile(r"^M\.?\s?H\.?$", re.I)),
  ("GT", re.compile(r"^G\.?\s?T\.?$", re.I)),
  ("KH", re.compile(r"^K\.?\s?H\.?$", re.I)),
  ("PT", re.compile(r"^P\.?\s?T\.?$", re.I)),
  ("R", re.compile(r"^R$")),
)

SIZE = re.compile(r"^(?P<a>\d{1,3})\s*[\"”″]\s*[xX×]\s*(?P<b>\d{1,3})\s*[\"”″]$")
SIZE_ABOVE_PT = 16.0
SIZE_ALIGN_PT = 10.0

def enabled() -> bool:
  return RR.on(RULE)

def kind_of(text: str) -> str | None:
  t = (text or "").strip()
  for kind, rx in LABELS:
    if rx.match(t):
      return kind
  return None

def _centre(w) -> tuple:
  return ((w.x0 + w.x1) / 2, (w.y0 + w.y1) / 2)

def labels_of(words: list) -> list:
  sizes = []
  for w in words:
    m = SIZE.match((w.text or "").strip())
    if m:
      sizes.append((_centre(w), [int(m.group("a")), int(m.group("b"))]))
  out = []
  
  for w in words:
    kind = kind_of(w.text)
    if kind is None:
      continue
    cx, cy = _centre(w)
    size = None
    
    for (sx, sy), value in sizes:
      if abs(sx - cx) <= SIZE_ALIGN_PT and 0 < abs(sy - cy) <= SIZE_ABOVE_PT:
        size = value
        break
    rec = {"kind": kind, "at": [round(cx, 1), round(cy, 1)]}
    if size:
      rec["size_in"] = size
    out.append(rec)
  return sorted(out, key=lambda r: (r["at"][1], r["at"][0]))

def read(raw) -> dict | None:
  if not enabled() or not raw.words:
    return None
  got = labels_of(raw.words)
  return {"labels": got} if got else None

def apply(rows: list) -> int:
  made = 0
  for row in rows:
    meta = row.get("meta")
    if meta is None:
      continue
    
    meta.pop(META_KEY, None)
    if not enabled():
      continue
    ident = meta.get("identity") or {}
    if ident.get("discipline") not in DISCIPLINES or ident.get("role") not in ROLES:
      continue
    labels = ((meta.get("structure_tables") or {}).get(SOURCE_KEY) or {}).get("labels") or []
    if labels:
      meta[META_KEY] = {"labels": labels}
      made += len(labels)
      
  return made
