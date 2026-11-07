from __future__ import annotations
import re
from app.engine.measure import rule_registry as RR
from app.modules.drawings_boq.takeoff.prep import page_unit as PU

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
SIZE_ABOVE_A3 = 16.0
SIZE_ALIGN_A3 = 10.0

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

def labels_of(words: list, unit: float = 1.0) -> list:
  """The drainage point labels a sheet prints: a manhole, a gully trap, a kitchen hole, a P-trap and a rain pipe are each one short word. The place is the middle of the word. A size printed as 18"x18" just above the word (or just below, when the text is turned) is the size of the point."""
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
      if abs(sx - cx) <= SIZE_ALIGN_A3 * unit and 0 < abs(sy - cy) <= SIZE_ABOVE_A3 * unit:
        size = value
        break
    rec = {"kind": kind, "at": [round(cx, 1), round(cy, 1)]}
    if size:
      rec["size_in"] = size
    out.append(rec)
  return sorted(out, key=lambda r: (r["at"][1], r["at"][0]))

def read(raw) -> dict | None:
  """Reads the labels of a sheet's text layer. Runs in structure_tables.read_all, inside the rule context at read time."""
  if not enabled() or not raw.words:
    return None
  wh = (getattr(raw, "width_pt", None), getattr(raw, "height_pt", None))
  got = labels_of(raw.words, PU.unit(wh) if all(wh) else 1.0)
  return {"labels": got} if got else None

def apply(rows: list) -> int:
  """Puts the drainage labels of each plumbing plan sheet in the sheet's meta, when the rule is on; takes them out when it is off. A label is kept only on a sheet whose title block says plumbing and whose role is a plan: the legend of the same set prints the same letters, a section or a detail prints a manhole that is not a point on the plan, and a single letter or a pair of letters means a drain point only there. Returns the labels made."""
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
