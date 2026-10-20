from __future__ import annotations
import re
from dataclasses import dataclass

DRAWING, MODEL, BOTH = "DRAWING", "MODEL", "BOTH"
PREFERS = (DRAWING, MODEL, BOTH)
ITEM = "ITEM"
MEMBER_KINDS = ("COLUMN", "FOOTING", "BEAM", "SLAB", "STAIR")
KINDS = (*MEMBER_KINDS, ITEM)

def norm(text) -> str:
  return re.sub(r"[^0-9A-Za-z]", "", str(text or "")).upper()

@dataclass(frozen=True)
class Rule:
  kind: str
  mark: str
  levels: frozenset | None
  prefer: str
  note: str = ""

  @property
  def specificity(self) -> int:
    return (2 if self.mark else 0) + (1 if self.levels is not None else 0)

def clean(raw) -> tuple:
  out: list = []
  for item in raw or ():
    if not isinstance(item, dict):
      continue
  
    kind = str(item.get("kind") or "").upper()
    prefer = str(item.get("prefer") or "").upper()
    if kind not in KINDS or prefer not in PREFERS:
      continue
    ids = item.get("level_ids")
    levels = None if ids is None else frozenset(str(i) for i in ids)
    out.append(Rule(kind, norm(item.get("mark")), levels, prefer, str(item.get("note") or "")))
  out.sort(key=lambda r: (r.kind, r.mark, sorted(r.levels) if r.levels is not None else [], r.prefer))
  return tuple(out)

def find(rules, kind: str, mark, level) -> Rule | None:
  key = norm(mark)
  best = None
  
  for r in rules or ():
    if r.kind != kind:
      continue
    if r.mark and r.mark != key:
      continue
    if r.levels is not None and (level is None or str(level) not in r.levels):
      continue
    if best is None or r.specificity > best.specificity:
      best = r
  return best

def detect(model_drawings: int, pdf_drawings: int, stored_one_total: float | None) -> dict:
  both = model_drawings > 0 and pdf_drawings > 0
  if stored_one_total is not None:
    value, source = (1 if float(stored_one_total) >= 0.5 else 0), "user"
  elif both:
    value, source = 1, "detected"
  else:
    value, source = 0, "default"
  return {"model_drawings": int(model_drawings), "pdf_drawings": int(pdf_drawings), "both": both, "one_total": {"value": value, "source": source},
    "needs_attention": bool(both and value == 0)}