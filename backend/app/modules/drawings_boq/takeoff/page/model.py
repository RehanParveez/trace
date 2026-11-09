from __future__ import annotations
from dataclasses import dataclass, field

VIEW, SCHEDULE, LEGEND, NOTES, SECTION_PICTURE, TITLE_BLOCK, CALLOUT = "VIEW", "SCHEDULE", "LEGEND", "NOTES", "SECTION_PICTURE", "TITLE_BLOCK", "CALLOUT"
KINDS = (VIEW, SCHEDULE, LEGEND, NOTES, SECTION_PICTURE, TITLE_BLOCK, CALLOUT)
PRIORITY = (TITLE_BLOCK, SCHEDULE, LEGEND, NOTES, SECTION_PICTURE, CALLOUT, VIEW)
MODEL_VERSION = 1

@dataclass
class Region:
  kind: str
  box: tuple
  title: str = ""
  words: list = field(default_factory=list)
  lines: int = 0
  rings: int = 0
  turn: int = 0
  confidence: float = 1.0
  source: str = ""
  parent: int | None = None
  group: int | None = None
  extra: dict = field(default_factory=dict)

  def to_json(self) -> dict:
    out = {"kind": self.kind, "box": [round(float(v), 2) for v in self.box], "title": self.title, "words": list(self.words), "lines": int(self.lines), "rings": int(self.rings), "turn": int(self.turn),
      "confidence": round(float(self.confidence), 3), "source": self.source, "parent": self.parent}
    if self.group is not None:
      out["group"] = self.group
    if self.extra:
      out["extra"] = self.extra
    return out

  @staticmethod
  def from_json(d: dict) -> "Region":
    return Region(kind=d["kind"], box=tuple(float(v) for v in d["box"]), title=d.get("title") or "", words=list(d.get("words") or []), lines=int(d.get("lines") or 0), rings=int(d.get("rings") or 0),
      turn=int(d.get("turn") or 0), confidence=float(d.get("confidence", 1.0)), source=d.get("source") or "", parent=d.get("parent"), group=d.get("group"), extra=dict(d.get("extra") or {}))

def area(b) -> float:
  return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])

def cut(a, b) -> float:
  return area((max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])))

def share_inside(a, b) -> float:
  return 0.0 if area(a) <= 0 else cut(a, b) / area(a)

def union(boxes: list) -> tuple:
  return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))

def contains_point(b, x: float, y: float) -> bool:
  return b[0] <= x <= b[2] and b[1] <= y <= b[3]

def region_at(regions: list, x: float, y: float, kinds: tuple | None = None):
  held = [r for r in regions if (kinds is None or r.kind in kinds) and contains_point(r.box, x, y)]
  return min(held, key=lambda r: area(r.box)) if held else None
